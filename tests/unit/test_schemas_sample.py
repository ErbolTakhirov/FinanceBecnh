from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from financebench.schemas.sample import CanonicalSample

# The exact example JSON from the platform's canonical-schema specification. Any breaking
# change to CanonicalSample that can't validate this literal is a breaking schema change.
GOLDEN_SAMPLE: dict[str, object] = {
    "schema_version": "1.0",
    "benchmark": "finqa",
    "benchmark_version": "official_commit_or_release",
    "split": "test",
    "split_origin": "official",
    "sample_id": "finqa:test:123",
    "task_family": "numerical_reasoning",
    "capability_tags": ["calculation", "table_text", "evidence_grounding"],
    "language": "en",
    "question": "What was the percentage increase in revenue?",
    "context": {
        "text": [],
        "tables": [],
        "images": [],
        "documents": [],
        "conversation_history": [],
    },
    "choices": [],
    "tools": [],
    "gold": {
        "answer": "12.5%",
        "answer_type": "numeric",
        "numeric_value": 12.5,
        "unit": "percent",
        "scale": "unit",
        "evidence": [],
        "program": None,
        "acceptable_answers": [],
    },
    "evaluation": {
        "absolute_tolerance": None,
        "relative_tolerance": 0.002,
        "requires_citation": True,
        "should_refuse": False,
    },
    "source": {
        "license": "dataset-specific",
        "url": "official source",
        "checksum": "sha256",
        "redistributable": True,
    },
    "metadata": {},
}


def test_golden_sample_validates() -> None:
    sample = CanonicalSample.model_validate(GOLDEN_SAMPLE)
    assert sample.benchmark == "finqa"
    assert sample.gold.numeric_value == 12.5
    assert sample.gold.unit == "percent"
    assert sample.evaluation.relative_tolerance == 0.002
    assert sample.source.redistributable is True


def test_golden_sample_round_trips_through_json() -> None:
    sample = CanonicalSample.model_validate(GOLDEN_SAMPLE)
    dumped = sample.model_dump(mode="json")
    reloaded = CanonicalSample.model_validate(dumped)
    assert reloaded == sample


def test_sample_id_must_start_with_benchmark_and_split() -> None:
    bad = copy.deepcopy(GOLDEN_SAMPLE)
    bad["sample_id"] = "wrong-prefix:123"
    with pytest.raises(ValidationError, match="must start with"):
        CanonicalSample.model_validate(bad)


def test_non_english_requires_translation_provenance() -> None:
    ru_sample = copy.deepcopy(GOLDEN_SAMPLE)
    ru_sample["language"] = "ru"
    with pytest.raises(ValidationError, match="translation_provenance"):
        CanonicalSample.model_validate(ru_sample)

    ru_sample["translation_provenance"] = "human_verified_translation"
    validated = CanonicalSample.model_validate(ru_sample)
    assert validated.translation_provenance == "human_verified_translation"


def test_empty_question_rejected() -> None:
    bad = copy.deepcopy(GOLDEN_SAMPLE)
    bad["question"] = "   "
    with pytest.raises(ValidationError):
        CanonicalSample.model_validate(bad)


def test_extra_fields_forbidden() -> None:
    bad = copy.deepcopy(GOLDEN_SAMPLE)
    bad["unexpected_field"] = "nope"
    with pytest.raises(ValidationError):
        CanonicalSample.model_validate(bad)


def test_sample_is_frozen() -> None:
    sample = CanonicalSample.model_validate(GOLDEN_SAMPLE)
    with pytest.raises(ValidationError):
        sample.question = "different question"  # type: ignore[misc]
