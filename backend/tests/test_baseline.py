from evaluation.baseline import cases, evaluate


def test_baseline_corpus_matches_the_contract_and_is_release_ready() -> None:
    report = evaluate()

    assert len(cases()) == 72
    assert report["total_cases"] == 72
    assert report["safe_task_success"] == 72
    assert report["hard_gate_failures"] == []
    assert report["release_ready"] is True
