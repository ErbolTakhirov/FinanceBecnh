"""The seven unified capability dimensions, their weights, and a rollup skeleton mapping each
sample's ``capability_tags`` to the dimension(s) it counts toward.

This is a Milestone 1 skeleton: the tag→dimension mapping is a plain Python dict good enough to
route the ``smoke`` fixture's tags. The mission requires this mapping be *configurable* (so a
new benchmark's task types can be routed without touching this module) — that YAML-driven
version, plus the full aggregation hierarchy (sample → task → benchmark → capability) and the
Finance Capability Index itself, land in Milestone 6. What's here already enforces the real
invariant early: weights sum to 1.0, and every dimension has an explicit weight.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from enum import StrEnum

from financebench.evaluation.metrics.base import aggregate_metric
from financebench.schemas.metric import MetricAggregate, MetricResult
from financebench.schemas.sample import CanonicalSample

__all__ = [
    "CAPABILITY_WEIGHTS",
    "CapabilityDimension",
    "dimensions_for_sample",
    "rollup_capabilities",
]


class CapabilityDimension(StrEnum):
    """The seven normalized capability dimensions the platform scores independently, so a model
    can't hide a critical weakness behind one strong area (see ``docs/research/scoring_design.md``)."""

    NUMERICAL_REASONING = "numerical_reasoning"
    DOCUMENT_GROUNDING_AND_RETRIEVAL = "document_grounding_and_retrieval"
    TABLE_TEXT_REASONING = "table_text_reasoning"
    FINANCIAL_ANALYSIS_AND_INSIGHT = "financial_analysis_and_insight"
    CONVERSATIONAL_CONSISTENCY = "conversational_consistency"
    CALIBRATION_REFUSAL_AND_RELIABILITY = "calibration_refusal_and_reliability"
    BILINGUAL_EN_RU = "bilingual_en_ru"


CAPABILITY_WEIGHTS: dict[CapabilityDimension, float] = {
    CapabilityDimension.NUMERICAL_REASONING: 0.25,
    CapabilityDimension.DOCUMENT_GROUNDING_AND_RETRIEVAL: 0.20,
    CapabilityDimension.TABLE_TEXT_REASONING: 0.15,
    CapabilityDimension.FINANCIAL_ANALYSIS_AND_INSIGHT: 0.15,
    CapabilityDimension.CONVERSATIONAL_CONSISTENCY: 0.10,
    CapabilityDimension.CALIBRATION_REFUSAL_AND_RELIABILITY: 0.10,
    CapabilityDimension.BILINGUAL_EN_RU: 0.05,
}

assert abs(sum(CAPABILITY_WEIGHTS.values()) - 1.0) < 1e-9, "capability weights must sum to 1.0"
assert set(CAPABILITY_WEIGHTS) == set(CapabilityDimension), (
    "every dimension needs an explicit weight"
)

#: Provisional tag→dimension routing (Milestone 1 only — see module docstring).
_TAG_TO_DIMENSION: dict[str, CapabilityDimension] = {
    "calculation": CapabilityDimension.NUMERICAL_REASONING,
    "evidence_grounding": CapabilityDimension.DOCUMENT_GROUNDING_AND_RETRIEVAL,
    "retrieval": CapabilityDimension.DOCUMENT_GROUNDING_AND_RETRIEVAL,
    "table_text": CapabilityDimension.TABLE_TEXT_REASONING,
    "analysis": CapabilityDimension.FINANCIAL_ANALYSIS_AND_INSIGHT,
    "insight": CapabilityDimension.FINANCIAL_ANALYSIS_AND_INSIGHT,
    "conversation": CapabilityDimension.CONVERSATIONAL_CONSISTENCY,
    "calibration_refusal": CapabilityDimension.CALIBRATION_REFUSAL_AND_RELIABILITY,
    "bilingual": CapabilityDimension.BILINGUAL_EN_RU,
}


def dimensions_for_sample(sample: CanonicalSample) -> tuple[CapabilityDimension, ...]:
    """Which capability dimension(s) a sample's score counts toward, from its ``capability_tags``.

    A sample with no recognized tag maps to no dimension (and is simply excluded from every
    capability rollup) rather than being guessed into one — an unmapped tag is a configuration
    gap to fix, not something to silently default.
    """
    matched = {_TAG_TO_DIMENSION[tag] for tag in sample.capability_tags if tag in _TAG_TO_DIMENSION}
    return tuple(sorted(matched, key=lambda dimension: dimension.value))


def rollup_capabilities(
    samples: Sequence[CanonicalSample], results: Sequence[MetricResult]
) -> dict[CapabilityDimension, MetricAggregate]:
    """Roll up per-sample metric results into a :class:`MetricAggregate` per capability
    dimension. A sample contributes to every dimension its tags map to (some samples span more
    than one, e.g. a cited table lookup counts toward both grounding and table/text reasoning)."""
    by_sample_id = {result.sample_id: result for result in results}
    buckets: dict[CapabilityDimension, list[MetricResult]] = defaultdict(list)
    for sample in samples:
        result = by_sample_id.get(sample.sample_id)
        if result is None:
            continue
        for dimension in dimensions_for_sample(sample):
            buckets[dimension].append(result)
    return {
        dimension: aggregate_metric(dimension.value, bucket_results)
        for dimension, bucket_results in buckets.items()
    }
