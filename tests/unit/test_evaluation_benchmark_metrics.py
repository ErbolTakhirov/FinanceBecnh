from __future__ import annotations

from financebench.evaluation.benchmark_metrics import metrics_for_run, preferred_metric_name


def test_a_direct_answer_run_gets_our_metric_not_the_official_one() -> None:
    """FinQA's official metrics grade a *program*. A run that asked for a number has none, so it
    is scored by finqa_answer_accuracy — which is ours, and is named so it cannot be mistaken for
    the official metric."""
    assert preferred_metric_name("finqa", "structured_financial_v1") == "finqa_answer_accuracy"

    names = {metric.name for metric in metrics_for_run("finqa", "structured_financial_v1")}
    assert names == {"exact_match", "finqa_answer_accuracy"}
    assert "finqa_program_accuracy" not in names, (
        "program accuracy must not be reported for a run that never asked for a program"
    )


def test_a_program_run_gets_both_official_metrics() -> None:
    assert preferred_metric_name("finqa", "program_v1") == "finqa_execution_accuracy"

    names = {metric.name for metric in metrics_for_run("finqa", "program_v1")}
    assert names == {"exact_match", "finqa_execution_accuracy", "finqa_program_accuracy"}


def test_unknown_benchmark_falls_back_to_exact_match() -> None:
    assert preferred_metric_name("smoke") == "exact_match"
    assert preferred_metric_name("some-future-benchmark") == "exact_match"


def test_metrics_for_smoke_does_not_duplicate_exact_match() -> None:
    names = [metric.name for metric in metrics_for_run("smoke")]
    assert names == ["exact_match"]
