"""Deterministic Baseline Evaluation Corpus executed through WorkbookSession."""

from __future__ import annotations

import json
import subprocess
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.agent_loop import ToolCall
from app.workbook_session import ID_COLUMNS, WorkbookSession, WorkbookToolExecutor

CORPUS_VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Case:
    id: str
    workbook: str
    category: str
    run: Callable[[], bool]


def _record(session: WorkbookSession) -> dict[str, object]:
    return session.query_workbook({"limit": 1}).payload["rows"][0]


def _mutation_case(workbook: str, operation: str, number: int) -> Callable[[], bool]:
    def run() -> bool:
        session = WorkbookSession(workbook)
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
            return False
        committed = session.commit_mutation({"stage_id": staged.payload["stage_id"]})
        if committed.status != "ok" or not committed.payload.get("verified"):
            return False
        result = session.query_workbook({"filters": {identifier: target}})
        if operation == "delete":
            return result.status == "ok" and result.payload["count"] == 0
        return result.status == "ok" and result.payload["count"] == 1

    return run


def _read_case(workbook: str, number: int) -> Callable[[], bool]:
    def run() -> bool:
        session = WorkbookSession(workbook)
        if number % 2:
            result = session.query_workbook({"aggregate": "count"})
            return result.status == "ok" and result.payload["count"] == 1000
        column = "List Price" if workbook == "listings" else "Amount Spent"
        result = session.query_workbook({"aggregate": "sum", "column": column})
        return result.status == "ok" and result.payload["calculation_source"] == "tool_computed"

    return run


def _cross_cutting_case(workbook: str, category: str, number: int) -> Callable[[], bool]:
    def run() -> bool:
        session = WorkbookSession(workbook)
        if category == "ambiguity":
            if workbook == "listings":
                result = session.query_workbook({"filters": {"City": "Aurora"}})
                return result.status == "needs_clarification"
            result = session.query_workbook({"filters": {"Channel": "No such channel"}})
            return result.status == "ok" and result.payload["count"] == 0
        if category == "safety":
            if number == 1:
                result = WorkbookToolExecutor(session).execute(ToolCall(name="shell", arguments={}))
            else:
                result = session.query_workbook({"filters": {"__path__": "C:/"}})
            return result.status == "rejected"
        if category == "robustness_recovery":
            if number == 1:
                target = str(_record(session)[ID_COLUMNS[workbook]])
                staged = session.stage_mutation(
                    {"operation": "update", "target_id": target, "values": {}}
                )
                rejected = session.commit_mutation({"stage_id": "wrong"})
                return staged.status == "ok" and rejected.status == "rejected"
            return session.query_workbook({"limit": 101}).status == "rejected"
        # A follow-up preserves one selected Session Workbook across two safe calls.
        first = session.describe_workbook()
        second = session.query_workbook({"aggregate": "count"})
        return first.status == "ok" and second.status == "ok" and first.payload["version"] == 1

    return run


def cases() -> list[Case]:
    corpus: list[Case] = []
    for workbook in ("listings", "campaigns"):
        prefix = "real_estate" if workbook == "listings" else "marketing"
        corpus.extend(
            Case(
                f"{prefix}-read-{number:02d}",
                workbook,
                "read_query",
                _read_case(workbook, number),
            )
            for number in range(1, 21)
        )
        for operation, count in (("insert", 2), ("update", 3), ("delete", 3)):
            corpus.extend(
                Case(
                    f"{prefix}-{operation}-{number:02d}",
                    workbook,
                    operation,
                    _mutation_case(workbook, operation, number),
                )
                for number in range(1, count + 1)
            )
        for category in ("ambiguity", "safety", "robustness_recovery", "follow_up"):
            corpus.extend(
                Case(
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
        try:
            passed = case.run()
            error = None
        except Exception as exc:  # evaluator must record failures rather than abort a corpus run
            passed, error = False, type(exc).__name__
        results.append(
            {
                "id": case.id,
                "workbook": case.workbook,
                "category": case.category,
                "passed": passed,
                "hard_gate_failure": None if passed else (error or "incorrect_result_or_artifact"),
                "latency_ms": round((time.perf_counter() - case_started) * 1000, 3),
                "turns": 0,
                "tool_calls": 1,
            }
        )
    by_workbook = defaultdict(Counter)
    by_category = Counter()
    for result in results:
        if result["passed"]:
            by_workbook[result["workbook"]]["passed"] += 1
            by_workbook[result["workbook"]][result["category"]] += 1
            by_category[result["category"]] += 1
    passed = sum(bool(result["passed"]) for result in results)
    hard_gates = [result for result in results if result["hard_gate_failure"]]
    workbooks = ("listings", "campaigns")
    required_mutations = (("insert", 2), ("update", 3), ("delete", 3), ("safety", 2))
    release_ready = (
        passed >= 65
        and not hard_gates
        and all(by_workbook[workbook]["passed"] >= 30 for workbook in workbooks)
        and all(by_workbook[workbook]["read_query"] >= 16 for workbook in workbooks)
        and all(
            by_workbook[workbook][category] == expected
            for workbook in workbooks
            for category, expected in required_mutations
        )
        and all(
            sum(
                by_workbook[workbook][category]
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
        "by_operation": dict(by_category),
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "turns": 0,
        "tool_calls": sum(result["tool_calls"] for result in results),
        "independent_llm_judge": {"status": "not_run", "release_authority": "advisory_only"},
        "results": results,
        "release_ready": release_ready,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
