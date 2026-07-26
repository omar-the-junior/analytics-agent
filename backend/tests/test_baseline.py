from evaluation.baseline import cases, evaluate


def test_real_estate_cases_declare_the_contract_and_emit_case_evidence() -> None:
    real_estate_cases = [case for case in cases() if case.workbook == "listings"]

    assert len(real_estate_cases) == 36
    assert all(case.fixture_hash and case.messages for case in real_estate_cases)
    assert all(case.permitted_tools for case in real_estate_cases)
    assert all(case.expected_result_or_artifact for case in real_estate_cases)

    report = evaluate()
    result = next(item for item in report["results"] if item["id"] == "real_estate-read-01")
    assert result["evidence"]["fixture_unchanged"] is True
    assert result["evidence"]["tool_policy"] is True
    assert result["evidence"]["postconditions"] is True


def test_baseline_corpus_matches_the_contract_and_is_release_ready() -> None:
    report = evaluate()

    assert len(cases()) == 72
    assert report["total_cases"] == 72
    assert report["safe_task_success"] == 72
    assert report["hard_gate_failures"] == []
    assert report["release_ready"] is True
