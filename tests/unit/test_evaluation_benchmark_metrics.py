from __future__ import annotations

from financebench.evaluation.benchmark_metrics import metrics_for_benchmark, preferred_metric_name


def test_finqa_prefers_its_native_metric() -> None:
    assert preferred_metric_name("finqa") == "finqa_execution_accuracy"


def test_unknown_benchmark_falls_back_to_exact_match() -> None:
    assert preferred_metric_name("smoke") == "exact_match"
    assert preferred_metric_name("some-future-benchmark") == "exact_match"


def test_metrics_for_finqa_includes_both_generic_and_native() -> None:
    names = {metric.name for metric in metrics_for_benchmark("finqa")}
    assert names == {"exact_match", "finqa_execution_accuracy"}


def test_metrics_for_smoke_does_not_duplicate_exact_match() -> None:
    metrics = metrics_for_benchmark("smoke")
    names = [metric.name for metric in metrics]
    assert names == ["exact_match"]
