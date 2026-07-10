"""Exact-match: the simplest possible metric, deliberately *not* numeric-tolerant.

Whitespace/case-normalized string equality only. A model that says "approximately 25%" instead
of "25%" fails this metric even though the underlying number is right — that gap is exactly what
motivates the numeric-tolerant metric (``evaluation/numeric.py``, Milestone 2): exact match
proves the pipeline works end to end, it is not meant to be a fair grader of prose answers.
"""

from __future__ import annotations

from financebench.evaluation.metrics.base import Metric, register_metric
from financebench.schemas.metric import MetricResult
from financebench.schemas.prediction import Prediction
from financebench.schemas.sample import CanonicalSample

__all__ = ["ExactMatchMetric"]


@register_metric("exact_match")
class ExactMatchMetric(Metric):
    name = "exact_match"

    def score(self, sample: CanonicalSample, prediction: Prediction) -> MetricResult:
        response = prediction.response
        if response is None or response.financial_answer is None:
            return MetricResult(
                sample_id=sample.sample_id,
                metric_name=self.name,
                value=False,
                passed=False,
                details={"reason": "no parsed answer"},
            )
        predicted = response.financial_answer.answer.strip().casefold()
        gold = sample.gold.answer.strip().casefold()
        is_match = predicted == gold
        return MetricResult(
            sample_id=sample.sample_id,
            metric_name=self.name,
            value=is_match,
            passed=is_match,
            details={"predicted": predicted, "gold": gold},
        )
