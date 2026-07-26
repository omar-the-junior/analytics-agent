import hashlib
import shutil
from pathlib import Path

from app.agent_loop import AgentLoop, ModelMessage, ToolCall
from app.workbook_session import SOURCES, WorkbookSession, WorkbookToolExecutor


def test_describe_and_query_preserve_the_supplied_source(tmp_path: Path) -> None:
    source_hash = SOURCES["listings"].read_bytes()
    session = WorkbookSession("listings", tmp_path)

    description = session.describe_workbook()
    result = session.query_workbook({"filters": {"Listing Status": "Active"}, "aggregate": "count"})

    assert description.status == "ok"
    assert description.payload["stable_id"] == "Listing ID"
    assert result.payload["count"] > 0
    assert SOURCES["listings"].read_bytes() == source_hash


def test_session_binds_immutable_source_identity_without_disclosing_paths(
    tmp_path: Path,
) -> None:
    session = WorkbookSession("campaigns", tmp_path)

    source_identity = session.source_hash
    description = session.describe_workbook()

    assert len(source_identity) == 64
    assert description.payload["source_identity"] == source_identity
    assert "path" not in description.payload


def test_session_identity_matches_the_copied_workbook_when_source_changes_during_setup(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source.xlsx"
    source.write_bytes(b"original workbook")
    monkeypatch.setitem(SOURCES, "campaigns", source)
    original_copy = shutil.copy2

    def copy_replaced_source(source_path: Path, destination: Path, *args, **kwargs) -> str:
        source_path.write_bytes(b"replacement workbook")
        return original_copy(source_path, destination, *args, **kwargs)

    monkeypatch.setattr("app.workbook_session.shutil.copy2", copy_replaced_source)

    session = WorkbookSession("campaigns", tmp_path / "session")

    assert session.source_hash == hashlib.sha256(b"replacement workbook").hexdigest()
    assert session.active_path.read_bytes() == b"replacement workbook"


def test_malformed_query_shapes_are_rejected_without_reading_the_workbook(tmp_path: Path) -> None:
    session = WorkbookSession("listings", tmp_path)

    non_object = session.query_workbook([])
    nested_filter = session.query_workbook({"filters": {"City": ["Aurora"]}})
    boolean_limit = session.query_workbook({"limit": True})

    assert non_object.payload == {"error_code": "invalid_query"}
    assert nested_filter.payload == {"error_code": "invalid_query"}
    assert boolean_limit.payload == {"error_code": "invalid_query"}


def test_ambiguous_city_and_unknown_field_fail_safely(tmp_path: Path) -> None:
    session = WorkbookSession("listings", tmp_path)

    ambiguous = session.query_workbook({"filters": {"City": "Aurora"}})
    unknown = session.query_workbook({"filters": {"drop table": "x"}})

    assert ambiguous.status == "needs_clarification"
    assert ambiguous.payload["error_code"] == "ambiguous_city_scope"
    assert unknown.status == "rejected"


def test_stage_requires_exact_commit_and_verifies_artifact(tmp_path: Path) -> None:
    source_bytes = SOURCES["listings"].read_bytes()
    session = WorkbookSession("listings", tmp_path)
    original = session.query_workbook({"filters": {"Listing ID": "LST-5001"}}).payload["rows"][0]

    staged = session.stage_mutation(
        {"operation": "update", "target_id": "LST-5001", "values": {"List Price": 351001}}
    )
    denied = session.commit_mutation({"stage_id": "not-the-stage"})
    committed = session.commit_mutation({"stage_id": staged.payload["stage_id"]})
    changed = session.query_workbook({"filters": {"Listing ID": "LST-5001"}}).payload["rows"][0]

    assert staged.payload["status"] == "confirmation_required"
    assert denied.payload["error_code"] == "confirmation_required"
    assert committed.payload["verified"] is True
    assert original["List Price"] == 351000
    assert changed["List Price"] == 351001
    assert SOURCES["listings"].read_bytes() == source_bytes


def test_tool_executor_only_exposes_the_session_contract(tmp_path: Path) -> None:
    executor = WorkbookToolExecutor(WorkbookSession("campaigns", tmp_path))

    result = executor.execute(ToolCall(name="query_workbook", arguments={"aggregate": "count"}))
    rejected = executor.execute(ToolCall(name="shell", arguments={}))

    assert result.status == "ok"
    assert rejected.status == "rejected"


def test_agent_loop_uses_real_read_executor_without_expanding_its_authority(
    tmp_path: Path,
) -> None:
    class ScriptedModel:
        def __init__(self) -> None:
            self.requests: list[list[ModelMessage]] = []
            self.responses = [
                '{"kind":"tool_batch","tool_calls":[{"name":"query_workbook",'
                '"arguments":{"aggregate":"count"}}]}',
                '{"kind":"final","answer":"Count returned."}',
            ]

        def complete(self, messages: list[ModelMessage]) -> str:
            self.requests.append(messages)
            return self.responses.pop(0)

    model = ScriptedModel()
    run = AgentLoop(model, WorkbookToolExecutor(WorkbookSession("campaigns", tmp_path))).run(
        "Count campaigns.", "Use workbook tools."
    )

    assert run.status == "completed"
    assert run.answer == "Count returned."
    assert '"tool":"query_workbook"' in model.requests[1][-1].content
