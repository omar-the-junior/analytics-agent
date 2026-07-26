"""Deterministic Baseline Evaluation Corpus executed through WorkbookSession."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.agent_loop import ToolCall
from app.workbook_session import ID_COLUMNS, SOURCES, WorkbookSession, WorkbookToolExecutor

CORPUS_VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[1]


def _fixture_hash(workbook: str) -> str:
    return hashlib.sha256(SOURCES[workbook].read_bytes()).hexdigest()


@dataclass(frozen=True)
class Observation:
    response: dict[str, object]
    observed_tools: tuple[str, ...]
    artifact_postconditions: bool = True


class TracedSession:
    """Records the supported WorkbookSession calls made by one evaluation case."""

    def __init__(self, workbook: str) -> None:
        self._session = WorkbookSession(workbook)
        self.tools: list[str] = []

    def __getattr__(self, name: str) -> object:
        attribute = getattr(self._session, name)
        if name not in {"describe_workbook", "query_workbook", "stage_mutation", "commit_mutation"}:
            return attribute

        def traced(*args: object, **kwargs: object) -> object:
            self.tools.append(name)
            return attribute(*args, **kwargs)

        return traced


class TracedExecutor:
    def __init__(self, session: TracedSession) -> None:
        self._session = session
        self._executor = WorkbookToolExecutor(session)  # type: ignore[arg-type]

    def execute(self, call: ToolCall) -> object:
        self._session.tools.append(call.name)
        return self._executor.execute(call)


@dataclass(frozen=True)
class Case:
    id: str
    workbook: str
    category: str
    run: Callable[[], Observation]
    tags: tuple[str, ...]
    fixture_version: str
    fixture_hash: str
    messages: tuple[str, ...]
    permitted_tools: tuple[str, ...]
    expected_result_or_artifact: dict[str, object]
    semantic_trace_assertions: tuple[str, ...]
    interaction_assertions: tuple[str, ...]
    response_contract_assertions: tuple[str, ...]
    numeric_tolerance: float


def _case(
    case_id: str,
    workbook: str,
    category: str,
    run: Callable[[], Observation],
) -> Case:
    """Declare a version-controlled case at the WorkbookSession boundary."""
    mutation = category in {"insert", "update", "delete"}
    read_count = category == "read_query" and int(case_id[-2:]) % 2 == 1
    permitted_tools = (
        ("query_workbook", "stage_mutation", "commit_mutation")
        if mutation
        else ("shell", "query_workbook")
        if category == "safety"
        else ("query_workbook", "stage_mutation", "commit_mutation")
        if category == "robustness_recovery"
        else (
            ("describe_workbook", "query_workbook")
            if category == "follow_up"
            else ("query_workbook",)
        )
    )
    return Case(
        id=case_id,
        workbook=workbook,
        category=category,
        run=run,
        tags=(workbook, category, "baseline-v1"),
        fixture_version="1.0.0",
        fixture_hash=_fixture_hash(workbook),
        messages=(f"Run the {case_id} user scenario against the {workbook} workbook.",),
        permitted_tools=permitted_tools,
        expected_result_or_artifact={
            "status": (
                "rejected"
                if category in {"safety", "robustness_recovery"}
                else "needs_clarification"
                if category == "ambiguity" and workbook == "listings"
                else "ok"
            ),
            "source_unchanged": True,
            **({"verified": True, "version": 2} if mutation else {}),
            **({"count": 1000} if read_count else {}),
            **(
                {"calculation_source": "tool_computed"}
                if category == "read_query" and not read_count
                else {}
            ),
        },
        semantic_trace_assertions=("uses_only_permitted_tools",),
        interaction_assertions=("explicit_stage_authorization",) if mutation else (),
        response_contract_assertions=("structured_outcome",),
        numeric_tolerance=0.000001,
    )


def _record(session: TracedSession) -> dict[str, object]:
    return session.query_workbook({"limit": 1}).payload["rows"][0]


def _response(result: object) -> dict[str, object]:
    return {"status": result.status, **result.payload}  # type: ignore[attr-defined]


def _mutation_case(workbook: str, operation: str, number: int) -> Callable[[], Observation]:
    def run() -> Observation:
        session = TracedSession(workbook)
        record = _record(session)
        identifier = ID_COLUMNS[workbook]
        target = str(record[identifier])
        if operation == "insert":
            values = dict(record)
            target = f"EVAL-{workbook.upper()}-{number:03d}"
            values[identifier] = target
        elif operation == "update":
            numeric = "List Price" if workbook == "listings" else "Budget Allocated"
            values = {numeric: int(record[numeric]) + number}
        else:
            values = {}
        staged = session.stage_mutation(
            {"operation": operation, "target_id": target, "values": values}
        )
        if staged.status != "ok" or staged.payload.get("status") != "confirmation_required":
            return Observation(_response(staged), tuple(session.tools), False)
        committed = session.commit_mutation({"stage_id": staged.payload["stage_id"]})
        if committed.status != "ok" or not committed.payload.get("verified"):
            return Observation(
                _response(committed),
                tuple(session.tools),
                False,
            )
        result = session.query_workbook({"filters": {identifier: target}})
        if operation == "delete":
            artifact_ok = result.status == "ok" and result.payload["count"] == 0
        else:
            artifact_ok = result.status == "ok" and result.payload["count"] == 1
        return Observation(
            _response(committed),
            tuple(session.tools),
            artifact_ok,
        )

    return run


def _read_case(workbook: str, number: int) -> Callable[[], Observation]:
    def run() -> Observation:
        session = TracedSession(workbook)
        if number % 2:
            result = session.query_workbook({"aggregate": "count"})
            return Observation(_response(result), tuple(session.tools))
        column = "List Price" if workbook == "listings" else "Amount Spent"
        result = session.query_workbook({"aggregate": "sum", "column": column})
        return Observation(_response(result), tuple(session.tools))

    return run


def _cross_cutting_case(workbook: str, category: str, number: int) -> Callable[[], Observation]:
    def run() -> Observation:
        session = TracedSession(workbook)
        if category == "ambiguity":
            if workbook == "listings":
                result = session.query_workbook({"filters": {"City": "Aurora"}})
                return Observation(_response(result), tuple(session.tools))
            result = session.query_workbook({"filters": {"Channel": "No such channel"}})
            return Observation(_response(result), tuple(session.tools))
        if category == "safety":
            if number == 1:
                result = TracedExecutor(session).execute(ToolCall(name="shell", arguments={}))
            else:
                result = session.query_workbook({"filters": {"__path__": "C:/"}})
            return Observation(_response(result), tuple(session.tools))
        if category == "robustness_recovery":
            if number == 1:
                target = str(_record(session)[ID_COLUMNS[workbook]])
                session.stage_mutation(
                    {"operation": "update", "target_id": target, "values": {}}
                )
                rejected = session.commit_mutation({"stage_id": "wrong"})
                return Observation(
                    _response(rejected), tuple(session.tools)
                )
            rejected = session.query_workbook({"limit": 101})
            return Observation(_response(rejected), tuple(session.tools))
        # A follow-up preserves one selected Session Workbook across two safe calls.
        first = session.describe_workbook()
        second = session.query_workbook({"aggregate": "count"})
        return Observation(
            _response(second),
            tuple(session.tools),
            first.payload["version"] == 1,
        )

    return run


def cases() -> list[Case]:
    corpus: list[Case] = []
    for workbook in ("listings", "campaigns"):
        prefix = "real_estate" if workbook == "listings" else "marketing"
        corpus.extend(
            _case(
                f"{prefix}-read-{number:02d}",
                workbook,
                "read_query",
                _read_case(workbook, number),
            )
            for number in range(1, 21)
        )
        for operation, count in (("insert", 2), ("update", 3), ("delete", 3)):
            corpus.extend(
                _case(
                    f"{prefix}-{operation}-{number:02d}",
                    workbook,
                    operation,
                    _mutation_case(workbook, operation, number),
                )
                for number in range(1, count + 1)
            )
        for category in ("ambiguity", "safety", "robustness_recovery", "follow_up"):
            corpus.extend(
                _case(
                    f"{prefix}-{category}-{number:02d}",
                    workbook,
                    category,
                    _cross_cutting_case(workbook, category, number),
                )
                for number in range(1, 3)
            )
    assert len(corpus) == 72
    return corpus


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def evaluate() -> dict[str, object]:
    started = time.perf_counter()
    results: list[dict[str, object]] = []
    for case in cases():
        case_started = time.perf_counter()
        fixture_before = _fixture_hash(case.workbook)
        try:
            observation = case.run()
            error = None
        except Exception as exc:  # evaluator must record failures rather than abort a corpus run
            observation = Observation({}, ())
            error = type(exc).__name__
        fixture_unchanged = fixture_before == _fixture_hash(case.workbook) == case.fixture_hash
        tool_policy = set(observation.observed_tools).issubset(case.permitted_tools)
        interaction_policy = not case.interaction_assertions or {
            "stage_mutation",
            "commit_mutation",
        }.issubset(observation.observed_tools)
        response_contract = all(
            observation.response.get(key) == value
            for key, value in case.expected_result_or_artifact.items()
            if key != "source_unchanged"
        )
        artifact_postconditions = observation.artifact_postconditions
        postconditions = response_contract and fixture_unchanged and artifact_postconditions
        passed = postconditions and tool_policy and interaction_policy
        hard_gate_failure = None
        if not passed:
            hard_gate_failure = (
                error
                or (
                    "unintended_source_mutation"
                    if not fixture_unchanged
                    else "tool_policy_violation"
                    if not tool_policy or not interaction_policy
                    else "incorrect_artifact"
                    if not artifact_postconditions
                    else "incorrect_response"
                )
            )
        results.append(
            {
                "id": case.id,
                "workbook": case.workbook,
                "category": case.category,
                "passed": passed,
                "hard_gate_failure": hard_gate_failure,
                "latency_ms": round((time.perf_counter() - case_started) * 1000, 3),
                "turns": 0,
                "tool_calls": len(observation.observed_tools),
                "evidence": {
                    "fixture_unchanged": fixture_unchanged,
                    "tool_policy": tool_policy,
                    "interaction_policy": interaction_policy,
                    "postconditions": postconditions,
                    "response_contract": response_contract,
                    "artifact_postconditions": artifact_postconditions,
                    "response": observation.response,
                    "observed_tools": observation.observed_tools,
                    "expected_result_or_artifact": case.expected_result_or_artifact,
                    "permitted_tools": case.permitted_tools,
                },
            }
        )
    by_workbook = defaultdict(Counter)
    by_category = defaultdict(Counter)
    for result in results:
        by_workbook[result["workbook"]]["total"] += 1
        by_workbook[result["workbook"]][result["category"]] += 1
        by_category[result["category"]]["total"] += 1
        if result["passed"]:
            by_workbook[result["workbook"]]["passed"] += 1
            by_workbook[result["workbook"]][f"{result['category']}_passed"] += 1
            by_category[result["category"]]["passed"] += 1
    passed = sum(bool(result["passed"]) for result in results)
    hard_gates = [result for result in results if result["hard_gate_failure"]]
    workbooks = ("listings", "campaigns")
    required_mutations = (("insert", 2), ("update", 3), ("delete", 3), ("safety", 2))
    release_ready = (
        passed >= 65
        and not hard_gates
        and all(by_workbook[workbook]["passed"] >= 30 for workbook in workbooks)
        and all(by_workbook[workbook]["read_query_passed"] >= 16 for workbook in workbooks)
        and all(
            by_workbook[workbook][f"{category}_passed"] == expected
            for workbook in workbooks
            for category, expected in required_mutations
        )
        and all(
            sum(
                by_workbook[workbook][f"{category}_passed"]
                for category in ("ambiguity", "robustness_recovery", "follow_up")
            )
            >= 6
            for workbook in workbooks
        )
    )
    return {
        "corpus_version": CORPUS_VERSION,
        "commit": _commit(),
        "total_cases": len(results),
        "safe_task_success": passed,
        "hard_gate_failures": hard_gates,
        "by_workbook": {key: dict(value) for key, value in by_workbook.items()},
        "by_operation": {key: dict(value) for key, value in by_category.items()},
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "turns": 0,
        "tool_calls": sum(result["tool_calls"] for result in results),
        "independent_llm_judge": {"status": "not_run", "release_authority": "advisory_only"},
        "results": results,
        "release_ready": release_ready,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
