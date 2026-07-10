from __future__ import annotations

from financebench.evaluation.metrics.base import aggregate_metric
from financebench.evaluation.metrics.exact_match import ExactMatchMetric
from financebench.schemas.common import AnswerType, SplitOrigin
from financebench.schemas.metric import MetricResult
from financebench.schemas.model_io import (
    ChatMessage,
    FinancialAnswer,
    ModelRequest,
    ModelResponse,
    ModelSpec,
    Role,
)
from financebench.schemas.prediction import Prediction
from financebench.schemas.sample import CanonicalSample, EvaluationSpec, GoldAnswer, SourceInfo


def _sample(gold_answer: str = "25%") -> CanonicalSample:
    return CanonicalSample(
        benchmark="smoke",
        benchmark_version="1",
        split="dev",
        split_origin=SplitOrigin.GENERATED_FROZEN,
        sample_id="smoke:dev:1",
        task_family="percentage_change",
        question="What was the percentage increase?",
        gold=GoldAnswer(answer=gold_answer, answer_type=AnswerType.NUMERIC, numeric_value=25.0),
        evaluation=EvaluationSpec(),
        source=SourceInfo(license="public-domain", url="generated", redistributable=True),
    )


def _request() -> ModelRequest:
    return ModelRequest(
        model=ModelSpec.parse("mock/echo-gold"),
        messages=(ChatMessage(role=Role.USER, content="q"),),
        prompt_version="v1",
        benchmark="smoke",
        benchmark_version="1",
        sample_id="smoke:dev:1",
    )


def _prediction(answer: str | None) -> Prediction:
    response = None
    if answer is not None:
        response = ModelResponse(
            provider="mock",
            model="echo-gold",
            content=answer,
            financial_answer=FinancialAnswer(answer=answer),
            parsed=True,
        )
    return Prediction(
        sample_id="smoke:dev:1",
        benchmark="smoke",
        split="dev",
        request=_request(),
        response=response,
        created_at="2026-07-11T00:00:00Z",
    )


def test_exact_match_passes_on_identical_answer() -> None:
    result = ExactMatchMetric().score(_sample("25%"), _prediction("25%"))
    assert result.passed is True
    assert result.value is True


def test_exact_match_is_case_and_whitespace_insensitive() -> None:
    result = ExactMatchMetric().score(_sample("Yes"), _prediction("  yes  "))
    assert result.passed is True


def test_exact_match_fails_on_differing_prose() -> None:
    result = ExactMatchMetric().score(
        _sample("25%"), _prediction("approximately 25%, per the table above")
    )
    assert result.passed is False


def test_exact_match_fails_gracefully_on_missing_response() -> None:
    result = ExactMatchMetric().score(_sample("25%"), _prediction(None))
    assert result.passed is False
    assert result.details["reason"] == "no parsed answer"


def test_aggregate_metric_computes_pass_rate() -> None:
    results = [
        MetricResult(sample_id=f"s{i}", metric_name="exact_match", value=passed, passed=passed)
        for i, passed in enumerate([True, True, False, True])
    ]
    agg = aggregate_metric("exact_match", results)
    assert agg.n == 4
    assert agg.mean == 0.75


def test_aggregate_metric_handles_empty_input() -> None:
    agg = aggregate_metric("exact_match", [])
    assert agg.n == 0
    assert agg.mean is None
