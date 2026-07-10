from __future__ import annotations

import pytest

import financebench.evaluation.metrics as metrics_pkg
from financebench.evaluation.metrics.base import (
    Metric,
    available_metrics,
    create_metric,
    get_metric_class,
    register_metric,
)
from financebench.evaluation.metrics.exact_match import ExactMatchMetric
from financebench.schemas.metric import MetricResult
from financebench.schemas.prediction import Prediction
from financebench.schemas.sample import CanonicalSample
from financebench.utils.errors import ConfigError


def test_exact_match_is_registered_on_package_import() -> None:
    assert "exact_match" in available_metrics()


def test_get_metric_class_returns_exact_match() -> None:
    assert get_metric_class("exact_match") is ExactMatchMetric


def test_get_metric_class_unknown_raises_config_error() -> None:
    with pytest.raises(ConfigError, match="unknown metric"):
        get_metric_class("does-not-exist")


def test_create_metric_builds_an_instance() -> None:
    assert isinstance(create_metric("exact_match"), ExactMatchMetric)


def test_register_metric_sets_name_classvar() -> None:
    @register_metric("throwaway-test-metric")
    class _Throwaway(Metric):
        def score(self, sample: CanonicalSample, prediction: Prediction) -> MetricResult:
            raise NotImplementedError  # pragma: no cover

    assert _Throwaway.name == "throwaway-test-metric"
    assert get_metric_class("throwaway-test-metric") is _Throwaway


def test_package_all_exports_are_importable() -> None:
    for name in metrics_pkg.__all__:
        assert hasattr(metrics_pkg, name)
