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


def test_marketing_cases_declare_campaign_metric_contracts_and_emit_evidence() -> None:
    marketing_cases = [case for case in cases() if case.workbook == "campaigns"]

    assert len(marketing_cases) == 36
    metric_cases = [case for case in marketing_cases if case.category == "read_query"]
    declared_columns = {
        case.expected_result_or_artifact["column"]
        for case in metric_cases
        if "column" in case.expected_result_or_artifact
    }
    assert declared_columns == {
        "Amount Spent",
        "Clicks",
        "Conversions",
        "Impressions",
        "Revenue Generated",
    }
    assert all(
        "tool_computed_campaign_metric" in case.semantic_trace_assertions
        for case in metric_cases[:19]
    )

    report = evaluate()
    result = next(item for item in report["results"] if item["id"] == "marketing-read-02")
    assert result["evidence"]["response_contract"] is True
    assert result["evidence"]["artifact_postconditions"] is True
    assert result["evidence"]["semantic_contract"] is True
    unavailable = next(item for item in report["results"] if item["id"] == "marketing-read-20")
    assert unavailable["evidence"]["response"]["status"] == "unavailable"
    ambiguity = next(item for item in report["results"] if item["id"] == "marketing-ambiguity-01")
    assert ambiguity["evidence"]["response"]["status"] == "needs_clarification"


def test_baseline_corpus_matches_the_contract_and_is_release_ready() -> None:
    report = evaluate()

    assert len(cases()) == 72
    assert report["total_cases"] == 72
    assert report["safe_task_success"] == 72
    assert report["hard_gate_failures"] == []
    assert report["release_ready"] is True
