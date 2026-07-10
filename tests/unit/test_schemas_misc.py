"""Lightweight construction/round-trip tests for the remaining schema modules — run config,
metrics, predictions, and leaderboard records don't have complex cross-field invariants like
``sample.py`` or ``manifest.py``, so one file covers all of them."""

from __future__ import annotations

from financebench.schemas.leaderboard import LeaderboardRecord
from financebench.schemas.metric import MetricAggregate, MetricResult
from financebench.schemas.model_io import ChatMessage, ModelRequest, ModelSpec, Role
from financebench.schemas.prediction import Prediction
from financebench.schemas.run import CacheMode, RunConfig
from financebench.schemas.tooling import ToolCall, ToolResult, ToolSpec


def test_run_config_defaults_match_determinism_requirements() -> None:
    config = RunConfig()
    assert config.seed == 42
    assert config.temperature == 0.0
    assert config.cache_mode is CacheMode.READ_WRITE


def test_metric_result_round_trip() -> None:
    result = MetricResult(
        sample_id="smoke:dev:1", metric_name="exact_match", value=True, passed=True
    )
    reloaded = MetricResult.model_validate(result.model_dump(mode="json"))
    assert reloaded == result


def test_metric_aggregate_allows_missing_ci() -> None:
    agg = MetricAggregate(metric_name="exact_match", n=10, mean=0.8)
    assert agg.ci_low is None
    assert agg.ci_high is None


def test_prediction_round_trip_without_response() -> None:
    request = ModelRequest(
        model=ModelSpec.parse("mock/echo-gold"),
        messages=(ChatMessage(role=Role.USER, content="hi"),),
        prompt_version="v1",
        benchmark="smoke",
        benchmark_version="1",
        sample_id="smoke:dev:1",
    )
    prediction = Prediction(
        sample_id="smoke:dev:1",
        benchmark="smoke",
        split="dev",
        request=request,
        error="timeout",
        error_type="ProviderTimeoutError",
        attempts=3,
        created_at="2026-07-11T00:00:00Z",
    )
    reloaded = Prediction.model_validate(prediction.model_dump(mode="json"))
    assert reloaded == prediction
    assert reloaded.response is None


def test_leaderboard_record_defaults_to_provisional() -> None:
    record = LeaderboardRecord(
        run_id="run-1",
        model_ref="mock/echo-gold",
        provider="mock",
        created_at="2026-07-11T00:00:00Z",
    )
    assert record.provisional is True
    assert record.fci is None


def test_tool_call_and_result_round_trip() -> None:
    spec = ToolSpec(name="calculator", description="evaluate arithmetic", parameters_schema={})
    call = ToolCall(tool_name=spec.name, arguments={"expression": "1+1"}, call_id="c1")
    result = ToolResult(call_id="c1", output="2")
    assert result.error is None
    assert call.arguments["expression"] == "1+1"
