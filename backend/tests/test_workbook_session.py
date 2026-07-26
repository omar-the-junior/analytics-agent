from pathlib import Path

from app.agent_loop import ToolCall
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


def test_ambiguous_city_and_unknown_field_fail_safely(tmp_path: Path) -> None:
    session = WorkbookSession("listings", tmp_path)

    ambiguous = session.query_workbook({"filters": {"City": "Aurora"}})
    unknown = session.query_workbook({"filters": {"drop table": "x"}})

    assert ambiguous.status == "needs_clarification"
    assert ambiguous.payload["error_code"] == "ambiguous_city_scope"
    assert unknown.status == "rejected"


def test_stage_requires_exact_commit_and_verifies_artifact(tmp_path: Path) -> None:
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
    assert SOURCES["listings"].read_bytes() == SOURCES["listings"].read_bytes()


def test_tool_executor_only_exposes_the_session_contract(tmp_path: Path) -> None:
    executor = WorkbookToolExecutor(WorkbookSession("campaigns", tmp_path))

    result = executor.execute(ToolCall(name="query_workbook", arguments={"aggregate": "count"}))
    rejected = executor.execute(ToolCall(name="shell", arguments={}))

    assert result.status == "ok"
    assert rejected.status == "rejected"
