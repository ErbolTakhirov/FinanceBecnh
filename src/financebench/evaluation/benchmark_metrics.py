"""Which metrics apply to which benchmark.

Every sample is always scored with the generic ``exact_match`` metric, plus that benchmark's
native metric where one has been implemented (see ``evaluation/native/``). ``metric_details.jsonl``
records every applicable metric per sample for transparency; only the *preferred* one (native
when available, else ``exact_match``) feeds the capability-dimension rollup, since a benchmark's
own native metric is a more faithful judge of its answer format than the generic fallback.
"""

from __future__ import annotations

from financebench.evaluation.metrics.base import Metric, create_metric

__all__ = ["metrics_for_benchmark", "preferred_metric_name"]

#: Populated as each benchmark's native metric lands (see evaluation/native/).
_NATIVE_METRIC_BY_BENCHMARK: dict[str, str] = {
    "finqa": "finqa_execution_accuracy",
}


def preferred_metric_name(benchmark: str) -> str:
    """The metric whose result should feed the capability-dimension rollup for ``benchmark``."""
    return _NATIVE_METRIC_BY_BENCHMARK.get(benchmark, "exact_match")


def metrics_for_benchmark(benchmark: str) -> tuple[Metric, ...]:
    """Every metric to compute and report for a sample from ``benchmark``."""
    names = {"exact_match", preferred_metric_name(benchmark)}
    return tuple(create_metric(name) for name in sorted(names))
