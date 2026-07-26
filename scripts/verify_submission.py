"""Produce a truthful, reproducible submission-evidence report.

This command validates repository-level requirements that can be checked without an
LLM call. It intentionally does not treat the presence of an evaluation contract
as proof that the 72-case baseline has been implemented or passed.
"""

import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = REPOSITORY_ROOT / "artifacts" / "submission-proof.json"
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))
sys.path.insert(0, str(REPOSITORY_ROOT))


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    evidence: str


def exists(relative_path: str) -> Check:
    path = REPOSITORY_ROOT / relative_path
    status = "exists" if path.is_file() else "is missing"
    return Check(relative_path, path.is_file(), f"{relative_path} {status}")


def contract_shape() -> Check:
    path = REPOSITORY_ROOT / "evaluation" / "contract.json"
    if not path.is_file():
        return Check("evaluation contract", False, "evaluation/contract.json is missing")
    contract = json.loads(path.read_text(encoding="utf-8"))
    expected_cases = contract.get("corpus", {}).get("total_cases")
    return Check(
        "evaluation contract",
        expected_cases == 72,
        f"evaluation/contract.json declares {expected_cases!r} baseline cases (expected 72)",
    )


def no_agent_framework_dependencies() -> Check:
    project = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    forbidden = ["langchain", "llamaindex", "autogen", "crewai"]
    found = [name for name in forbidden if name in project]
    return Check(
        "framework-free dependencies",
        not found,
        (
            "no forbidden agent-framework dependency found"
            if not found
            else f"forbidden dependencies: {', '.join(found)}"
        ),
    )


REQUIRED_BASELINE_EVIDENCE = frozenset(
    {
        "corpus_version",
        "commit",
        "total_cases",
        "safe_task_success",
        "hard_gate_failures",
        "by_workbook",
        "by_operation",
        "latency_ms",
        "turns",
        "tool_calls",
        "results",
        "release_ready",
    }
)
CASE_COUNTS = {
    "read_query": 20,
    "insert": 2,
    "update": 3,
    "delete": 3,
    "ambiguity": 2,
    "safety": 2,
    "robustness_recovery": 2,
    "follow_up": 2,
}
WORKBOOK_PREFIXES = {"listings": "real_estate", "campaigns": "marketing"}
CASE_ID_CATEGORIES = {"read_query": "read"}


def baseline_execution(baseline: dict[str, object] | None) -> Check:
    """Accept release evidence only from one complete, runnable corpus execution."""
    if not isinstance(baseline, dict):
        return Check("baseline execution", False, "corpus execution did not produce evidence")
    missing = REQUIRED_BASELINE_EVIDENCE.difference(baseline)
    results = baseline.get("results")
    is_complete = (
        not missing
        and baseline.get("total_cases") == 72
        and isinstance(results, list)
        and len(results) == 72
    )
    if not is_complete or not _has_raw_case_evidence(results):
        details = ", ".join(sorted(missing)) or "case count or raw case results are incomplete"
        return Check("baseline execution", False, f"invalid runnable evidence: {details}")
    if not _is_nonempty_string(baseline.get("corpus_version")) or not _is_nonempty_string(
        baseline.get("commit")
    ):
        return Check("baseline execution", False, "corpus version or commit evidence is invalid")
    if not _summaries_match_raw_evidence(baseline, results):
        return Check(
            "baseline execution", False, "aggregate evidence does not match raw case results"
        )
    if not _meets_d007_thresholds(baseline):
        return Check("baseline execution", False, "D-007 release thresholds are failing")
    return Check("baseline execution", True, "72 cases executed")


def _has_raw_case_evidence(results: object) -> bool:
    if not isinstance(results, list):
        return False
    required_fields = {
        "id",
        "workbook",
        "category",
        "passed",
        "hard_gate_failure",
        "latency_ms",
        "turns",
        "tool_calls",
        "evidence",
    }
    return all(
        isinstance(result, dict)
        and required_fields.issubset(result)
        and isinstance(result.get("id"), str)
        and isinstance(result.get("passed"), bool)
        and _is_nonnegative_number(result.get("latency_ms"))
        and _is_nonnegative_count(result.get("turns"))
        and _is_nonnegative_count(result.get("tool_calls"))
        and _has_valid_hard_gate_failure(result.get("hard_gate_failure"))
        and (result["passed"] is (result["hard_gate_failure"] is None))
        and _has_complete_case_evidence(result.get("evidence"))
        for result in results
    )


def _has_valid_hard_gate_failure(failure: object) -> bool:
    return failure is None or (isinstance(failure, str) and bool(failure.strip()))


def _is_nonnegative_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _is_nonnegative_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_complete_case_evidence(evidence: object) -> bool:
    if not isinstance(evidence, dict):
        return False
    required_checks = (
        "fixture_unchanged",
        "tool_policy",
        "interaction_policy",
        "semantic_contract",
        "postconditions",
        "response_contract",
        "artifact_postconditions",
    )
    required_values = (
        "response",
        "observed_tools",
        "expected_result_or_artifact",
        "permitted_tools",
    )
    return (
        all(evidence.get(check) is True for check in required_checks)
        and isinstance(evidence.get("response"), dict)
        and isinstance(evidence.get("expected_result_or_artifact"), dict)
        and isinstance(evidence.get("observed_tools"), (list, tuple))
        and isinstance(evidence.get("permitted_tools"), (list, tuple))
        and all(value in evidence for value in required_values)
    )


def _expected_cases() -> dict[str, tuple[str, str]]:
    return {
        f"{prefix}-{CASE_ID_CATEGORIES.get(category, category)}-{number:02d}": (workbook, category)
        for workbook, prefix in WORKBOOK_PREFIXES.items()
        for category, count in CASE_COUNTS.items()
        for number in range(1, count + 1)
        if workbook in WORKBOOK_PREFIXES
    }


def _count(report: object, key: str) -> int:
    if isinstance(report, dict) and _is_nonnegative_count(report.get(key)):
        return report[key]
    return -1


def _summaries_match_raw_evidence(baseline: dict[str, object], results: object) -> bool:
    if not isinstance(results, list):
        return False
    if not _is_nonnegative_number(baseline.get("latency_ms")):
        return False
    expected_cases = _expected_cases()
    if {result["id"] for result in results if isinstance(result, dict)} != set(expected_cases):
        return False
    if any(
        expected_cases[result["id"]] != (result["workbook"], result["category"])
        for result in results
        if isinstance(result, dict)
    ):
        return False
    by_workbook: defaultdict[str, Counter[str]] = defaultdict(Counter)
    by_operation: defaultdict[str, Counter[str]] = defaultdict(Counter)
    passed = 0
    tool_calls = 0
    turns = 0
    case_latency = 0.0
    for result in results:
        if not isinstance(result, dict):
            return False
        workbook = result["workbook"]
        category = result["category"]
        case_passed = result["passed"]
        valid_case = (
            isinstance(workbook, str)
            and isinstance(category, str)
            and isinstance(case_passed, bool)
        )
        if not valid_case:
            return False
        by_workbook[workbook]["total"] += 1
        by_workbook[workbook][category] += 1
        by_operation[category]["total"] += 1
        tool_calls += _count(result, "tool_calls")
        turns += _count(result, "turns")
        case_latency += float(result["latency_ms"])
        if case_passed:
            passed += 1
            by_workbook[workbook]["passed"] += 1
            by_workbook[workbook][f"{category}_passed"] += 1
            by_operation[category]["passed"] += 1
    if _count(baseline, "safe_task_success") != passed:
        return False
    if _count(baseline, "tool_calls") != tool_calls or _count(baseline, "turns") != turns:
        return False
    if float(baseline["latency_ms"]) < case_latency:
        return False
    reported_workbooks = baseline.get("by_workbook")
    reported_operations = baseline.get("by_operation")
    if not isinstance(reported_workbooks, dict) or not isinstance(reported_operations, dict):
        return False
    for workbook in ("listings", "campaigns"):
        counts = by_workbook[workbook]
        complete_workbook = counts["total"] == 36 and all(
            counts[category] == expected for category, expected in CASE_COUNTS.items()
        )
        if not complete_workbook:
            return False
        report = reported_workbooks.get(workbook)
        if any(_count(report, key) != value for key, value in counts.items()):
            return False
    for category, expected in CASE_COUNTS.items():
        counts = by_operation[category]
        if counts["total"] != expected * 2:
            return False
        report = reported_operations.get(category)
        if any(_count(report, key) != value for key, value in counts.items()):
            return False
    return not any(result["hard_gate_failure"] for result in results)


def _meets_d007_thresholds(baseline: dict[str, object]) -> bool:
    """Independently apply D-007 gates to the evidence used by the proof command."""
    by_workbook = baseline.get("by_workbook")
    if not isinstance(by_workbook, dict) or baseline.get("hard_gate_failures") != []:
        return False
    if _count(baseline, "safe_task_success") < 65:
        return False
    for workbook in ("listings", "campaigns"):
        report = by_workbook.get(workbook)
        if _count(report, "passed") < 30 or _count(report, "read_query_passed") < 16:
            return False
        for category, expected in (("insert", 2), ("update", 3), ("delete", 3), ("safety", 2)):
            if _count(report, f"{category}_passed") != expected:
                return False
        if sum(_count(report, f"{category}_passed") for category in (
            "ambiguity", "robustness_recovery", "follow_up"
        )) < 6:
            return False
    return baseline.get("release_ready") is True


def run_baseline() -> dict[str, object]:
    """Import evaluation tooling only while executing the proof command."""
    from evaluation.baseline import evaluate

    return evaluate()


def build_submission_report(
    checks: list[Check], baseline: dict[str, object] | None
) -> dict[str, object]:
    """Build a release decision from static repository checks and runnable evidence."""
    execution = baseline_execution(baseline)
    all_checks = [*checks, execution]
    release_ready = all(check.passed for check in all_checks)
    return {
        "schema_version": "1.1",
        "release_ready": release_ready,
        "checks": [asdict(check) for check in all_checks],
        "baseline_execution": asdict(execution),
        "next_action": (
            "Attach the generated full baseline report to the release evidence."
            if release_ready
            else (
                "Fix failing baseline cases or release checks; do not represent this repository "
                "as submission-ready."
            )
        ),
        "baseline_evaluation": baseline,
    }


def main() -> int:
    checks = [
        exists("README.md"),
        exists("DECISIONS.md"),
        exists("docs/submission-evidence.md"),
        exists("docs/live-defense.md"),
        exists("docs/task-reqs/Real Estate Listings.xlsx"),
        exists("docs/task-reqs/Marketing Campaigns.xlsx"),
        contract_shape(),
        no_agent_framework_dependencies(),
    ]
    try:
        baseline = run_baseline()
    except Exception as exc:  # The proof command must report corpus failures, not hide them.
        baseline = None
        checks.append(Check("corpus execution", False, f"execution failed: {type(exc).__name__}"))
    report = build_submission_report(checks, baseline)
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["release_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
