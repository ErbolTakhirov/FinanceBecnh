"""The ``Metric`` contract, a small metric registry, and a generic aggregator.

Every metric — native (FinQA execution accuracy, TAT-QA numeracy F1, ...) or unified
(exact match, numeric tolerance, ...) — implements one method, ``score``, scoring a single
sample/prediction pair. Metrics are registered by name with :func:`register_metric`, the same
seam ``datasets/base.py`` and ``models/base.py`` use for adapters and providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import ClassVar, TypeVar

from financebench.schemas.metric import MetricAggregate, MetricResult
from financebench.schemas.prediction import Prediction
from financebench.schemas.sample import CanonicalSample
from financebench.utils.errors import ConfigError

__all__ = [
    "Metric",
    "aggregate_metric",
    "available_metrics",
    "create_metric",
    "get_metric_class",
    "register_metric",
]


class Metric(ABC):
    """Abstract base for all metrics, native or unified."""

    name: ClassVar[str] = ""

    @abstractmethod
    def score(self, sample: CanonicalSample, prediction: Prediction) -> MetricResult:
        """Score a single ``(sample, prediction)`` pair.

        Must always return a :class:`MetricResult`, even for a missing/unparsed prediction —
        record it as a failing result (``passed=False``) with a reason in ``details``, never
        raise or silently skip.
        """
        raise NotImplementedError


_REGISTRY: dict[str, type[Metric]] = {}

_MetricT = TypeVar("_MetricT", bound=type[Metric])


def register_metric(name: str) -> Callable[[_MetricT], _MetricT]:
    """Class decorator registering a metric under ``name``."""

    def decorate(cls: _MetricT) -> _MetricT:
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return decorate


def available_metrics() -> list[str]:
    """Sorted list of registered metric names."""
    return sorted(_REGISTRY)


def get_metric_class(name: str) -> type[Metric]:
    """Look up a registered metric class, or raise :class:`ConfigError`."""
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ConfigError(
            f"unknown metric {name!r}; available metrics: {available_metrics()}"
        ) from exc


def create_metric(name: str) -> Metric:
    """Instantiate the metric registered under ``name``."""
    return get_metric_class(name)()


def aggregate_metric(metric_name: str, results: Sequence[MetricResult]) -> MetricAggregate:
    """Roll up a set of :class:`MetricResult` into a :class:`MetricAggregate`.

    Boolean values count as 0/1; non-numeric (string) values are excluded from the mean (a
    metric that legitimately returns strings should report its own aggregate separately) rather
    than raising — an aggregate over zero numeric values is still a valid ``MetricAggregate``
    with ``mean=None``, not an error.

    ``n`` is the number of samples this metric **actually graded**, not the number it was offered.
    Those are different numbers whenever a metric returns not-applicable, and reporting the larger
    one overstates the evidence a mean rests on: SECQUE's ``numeric_agreement`` was published as
    ``n: 80`` when 18 of those samples contain no figures for it to agree with and the mean is over
    62. The repo's own release schema already says ``n`` is "samples actually graded — excluding
    not-applicable ones"; this makes the code obey it, and reports the excluded count rather than
    hiding it.
    """
    numeric_values: list[float] = [
        (1.0 if result.value else 0.0) if isinstance(result.value, bool) else float(result.value)
        for result in results
        if isinstance(result.value, bool | int | float)
    ]
    not_applicable = len(results) - len(numeric_values)
    if not numeric_values:
        return MetricAggregate(metric_name=metric_name, n=0, n_not_applicable=not_applicable)
    return MetricAggregate(
        metric_name=metric_name,
        n=len(numeric_values),
        n_not_applicable=not_applicable,
        mean=sum(numeric_values) / len(numeric_values),
    )
