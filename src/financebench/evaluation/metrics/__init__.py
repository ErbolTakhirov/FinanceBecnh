"""Metrics: the ``Metric`` contract, registry, aggregator, and the built-in ``exact_match``
metric.

Importing this package registers every built-in metric — CLI/evaluator code should ``import
financebench.evaluation.metrics`` (not a specific metric module) so the registry is always fully
populated.
"""

from __future__ import annotations

from financebench.evaluation.metrics import exact_match as _exact_match  # noqa: F401
from financebench.evaluation.metrics.base import (
    Metric,
    aggregate_metric,
    available_metrics,
    create_metric,
    get_metric_class,
    register_metric,
)
from financebench.evaluation.metrics.exact_match import ExactMatchMetric

__all__ = [
    "ExactMatchMetric",
    "Metric",
    "aggregate_metric",
    "available_metrics",
    "create_metric",
    "get_metric_class",
    "register_metric",
]
