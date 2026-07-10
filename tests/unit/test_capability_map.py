from __future__ import annotations

from financebench.evaluation.capability_map import (
    CAPABILITY_WEIGHTS,
    CapabilityDimension,
    dimensions_for_sample,
    rollup_capabilities,
)
from financebench.schemas.common import AnswerType, SplitOrigin
from financebench.schemas.metric import MetricResult
from financebench.schemas.sample import CanonicalSample, GoldAnswer, SourceInfo


def _sample(sample_id: str, tags: tuple[str, ...]) -> CanonicalSample:
    return CanonicalSample(
        benchmark="smoke",
        benchmark_version="1",
        split="dev",
        split_origin=SplitOrigin.GENERATED_FROZEN,
        sample_id=sample_id,
        task_family="arithmetic",
        capability_tags=tags,
        question="q",
        gold=GoldAnswer(answer="1", answer_type=AnswerType.NUMERIC, numeric_value=1.0),
        source=SourceInfo(license="public-domain", url="generated", redistributable=True),
    )


def test_capability_weights_sum_to_one() -> None:
    assert abs(sum(CAPABILITY_WEIGHTS.values()) - 1.0) < 1e-9


def test_every_dimension_has_a_weight() -> None:
    assert set(CAPABILITY_WEIGHTS) == set(CapabilityDimension)


def test_dimensions_for_sample_maps_known_tags() -> None:
    sample = _sample("smoke:dev:1", ("calculation",))
    assert dimensions_for_sample(sample) == (CapabilityDimension.NUMERICAL_REASONING,)


def test_dimensions_for_sample_ignores_unmapped_tags() -> None:
    sample = _sample("smoke:dev:1", ("some_future_tag_not_yet_mapped",))
    assert dimensions_for_sample(sample) == ()


def test_dimensions_for_sample_can_map_to_multiple_dimensions() -> None:
    sample = _sample("smoke:dev:1", ("table_text", "evidence_grounding"))
    dims = dimensions_for_sample(sample)
    assert CapabilityDimension.TABLE_TEXT_REASONING in dims
    assert CapabilityDimension.DOCUMENT_GROUNDING_AND_RETRIEVAL in dims


def test_dimensions_for_sample_dedupes_when_two_tags_map_to_one_dimension() -> None:
    sample = _sample("smoke:dev:1", ("evidence_grounding", "retrieval"))
    dims = dimensions_for_sample(sample)
    assert dims.count(CapabilityDimension.DOCUMENT_GROUNDING_AND_RETRIEVAL) == 1


def test_rollup_capabilities_aggregates_per_dimension() -> None:
    samples = [
        _sample("smoke:dev:1", ("calculation",)),
        _sample("smoke:dev:2", ("calculation",)),
        _sample("smoke:dev:3", ("table_text",)),
    ]
    results = [
        MetricResult(sample_id="smoke:dev:1", metric_name="exact_match", value=True, passed=True),
        MetricResult(sample_id="smoke:dev:2", metric_name="exact_match", value=False, passed=False),
        MetricResult(sample_id="smoke:dev:3", metric_name="exact_match", value=True, passed=True),
    ]

    rollup = rollup_capabilities(samples, results)

    assert rollup[CapabilityDimension.NUMERICAL_REASONING].n == 2
    assert rollup[CapabilityDimension.NUMERICAL_REASONING].mean == 0.5
    assert rollup[CapabilityDimension.TABLE_TEXT_REASONING].n == 1
    assert rollup[CapabilityDimension.TABLE_TEXT_REASONING].mean == 1.0


def test_rollup_capabilities_skips_samples_with_no_result() -> None:
    samples = [_sample("smoke:dev:1", ("calculation",))]
    rollup = rollup_capabilities(samples, results=[])
    assert rollup == {}
