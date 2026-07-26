import runpy
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "verify_submission.py"


def _script_namespace() -> dict[str, object]:
    return runpy.run_path(str(SCRIPT_PATH))


def _passing_baseline() -> dict[str, object]:
    case_counts = {
        "read_query": 20,
        "insert": 2,
        "update": 3,
        "delete": 3,
        "ambiguity": 2,
        "safety": 2,
        "robustness_recovery": 2,
        "follow_up": 2,
    }
    results = [
        {
            "id": (
                f"{'real_estate' if workbook == 'listings' else 'marketing'}-"
                f"{'read' if category == 'read_query' else category}-{number:02d}"
            ),
            "workbook": workbook,
            "category": category,
            "passed": True,
            "hard_gate_failure": None,
            "latency_ms": 1.0,
            "turns": 0,
            "tool_calls": 1,
            "evidence": {
                "fixture_unchanged": True,
                "tool_policy": True,
                "interaction_policy": True,
                "semantic_contract": True,
                "postconditions": True,
                "response_contract": True,
                "artifact_postconditions": True,
                "response": {},
                "observed_tools": [],
                "expected_result_or_artifact": {},
                "permitted_tools": [],
            },
        }
        for workbook in ("listings", "campaigns")
        for category, count in case_counts.items()
        for number in range(1, count + 1)
    ]
    workbook_report = {
        "total": 36,
        "passed": 36,
        **case_counts,
        **{f"{category}_passed": count for category, count in case_counts.items()},
    }
    operation_report = {
        category: {"total": count * 2, "passed": count * 2}
        for category, count in case_counts.items()
    }
    return {
        "corpus_version": "1.0.0",
        "commit": "abc123",
        "total_cases": 72,
        "safe_task_success": 72,
        "hard_gate_failures": [],
        "by_workbook": {"listings": workbook_report, "campaigns": workbook_report},
        "by_operation": operation_report,
        "latency_ms": 72.0,
        "turns": 0,
        "tool_calls": 72,
        "results": results,
        "release_ready": True,
    }


def test_submission_proof_uses_runnable_baseline_evidence_for_release_readiness() -> None:
    module = _script_namespace()
    check = module["Check"]
    build_submission_report = module["build_submission_report"]
    checks = [check("repository evidence", True, "available")]
    baseline = _passing_baseline()

    report = build_submission_report(checks, baseline)

    assert report["release_ready"] is True
    assert report["baseline_evaluation"] == baseline
    assert report["baseline_execution"]["passed"] is True
    assert report["baseline_execution"]["evidence"] == "72 cases executed"


def test_submission_proof_fails_closed_when_runnable_evidence_is_missing_or_failing() -> None:
    module = _script_namespace()
    check = module["Check"]
    build_submission_report = module["build_submission_report"]
    checks = [check("repository evidence", True, "available")]

    missing = build_submission_report(checks, None)
    failing = _passing_baseline()
    failing["hard_gate_failures"] = [{"id": "real_estate-read-01"}]

    assert missing["release_ready"] is False
    assert missing["baseline_execution"]["passed"] is False
    failing_report = build_submission_report(checks, failing)
    assert failing_report["release_ready"] is False
    assert failing_report["baseline_execution"]["passed"] is False


def test_submission_proof_rejects_forged_summary_and_reports_tooling_failures(
    tmp_path: Path,
) -> None:
    module = _script_namespace()
    check = module["Check"]
    build_submission_report = module["build_submission_report"]
    forged = _passing_baseline()
    forged["results"] = [forged["results"][0]] * 72

    assert build_submission_report([check("repository evidence", True, "available")], forged)[
        "release_ready"
    ] is False

    def unavailable_tooling() -> dict[str, object]:
        raise ImportError("evaluation tooling unavailable")

    report_path = tmp_path / "submission-proof.json"
    main = module["main"]
    main.__globals__["run_baseline"] = unavailable_tooling
    main.__globals__["REPORT_PATH"] = report_path
    assert main() == 2
    report = module["json"].loads(report_path.read_text(encoding="utf-8"))
    assert report["release_ready"] is False
    assert report["baseline_execution"]["passed"] is False


def test_submission_proof_rejects_distributed_forged_raw_evidence() -> None:
    module = _script_namespace()
    check = module["Check"]
    build_submission_report = module["build_submission_report"]
    forged = _passing_baseline()
    forged["results"] = [{**result, "evidence": {}} for result in forged["results"]]

    report = build_submission_report([check("repository evidence", True, "available")], forged)

    assert report["release_ready"] is False
    assert report["baseline_execution"]["passed"] is False


def test_submission_proof_rejects_failed_case_without_a_hard_gate_reason() -> None:
    module = _script_namespace()
    check = module["Check"]
    build_submission_report = module["build_submission_report"]
    forged = _passing_baseline()
    forged["results"][0]["passed"] = False
    forged["safe_task_success"] = 71
    forged["by_workbook"] = {key: dict(value) for key, value in forged["by_workbook"].items()}
    forged["by_workbook"]["listings"]["passed"] = 35
    forged["by_workbook"]["listings"]["read_query_passed"] = 19
    forged["by_operation"]["read_query"]["passed"] = 39

    report = build_submission_report([check("repository evidence", True, "available")], forged)

    assert report["release_ready"] is False
    assert report["baseline_execution"]["passed"] is False


def test_submission_proof_rejects_an_empty_hard_gate_reason() -> None:
    module = _script_namespace()
    check = module["Check"]
    build_submission_report = module["build_submission_report"]
    forged = _passing_baseline()
    forged["results"][0]["passed"] = False
    forged["results"][0]["hard_gate_failure"] = " "
    forged["safe_task_success"] = 71
    forged["by_workbook"] = {key: dict(value) for key, value in forged["by_workbook"].items()}
    forged["by_workbook"]["listings"]["passed"] = 35
    forged["by_workbook"]["listings"]["read_query_passed"] = 19
    forged["by_operation"]["read_query"]["passed"] = 39

    report = build_submission_report([check("repository evidence", True, "available")], forged)

    assert report["release_ready"] is False
    assert report["baseline_execution"]["passed"] is False


def test_submission_proof_rejects_malformed_case_ids_without_crashing() -> None:
    module = _script_namespace()
    check = module["Check"]
    build_submission_report = module["build_submission_report"]
    forged = _passing_baseline()
    forged["results"][0]["id"] = []

    report = build_submission_report([check("repository evidence", True, "available")], forged)

    assert report["release_ready"] is False
    assert report["baseline_execution"]["passed"] is False


def test_submission_proof_rejects_case_ids_with_swapped_workbook_labels() -> None:
    module = _script_namespace()
    check = module["Check"]
    build_submission_report = module["build_submission_report"]
    forged = _passing_baseline()
    listings = forged["results"][0]
    campaigns = next(result for result in forged["results"] if result["workbook"] == "campaigns")
    listings["workbook"], campaigns["workbook"] = campaigns["workbook"], listings["workbook"]

    report = build_submission_report([check("repository evidence", True, "available")], forged)

    assert report["release_ready"] is False
    assert report["baseline_execution"]["passed"] is False


def test_submission_proof_rejects_malformed_corpus_or_resource_evidence() -> None:
    module = _script_namespace()
    check = module["Check"]
    build_submission_report = module["build_submission_report"]
    checks = [check("repository evidence", True, "available")]
    malformed = _passing_baseline()
    malformed["latency_ms"] = "unknown"

    assert build_submission_report(checks, [])["release_ready"] is False
    assert build_submission_report(checks, malformed)["release_ready"] is False
