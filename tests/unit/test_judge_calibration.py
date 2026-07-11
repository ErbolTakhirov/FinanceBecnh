"""The judge, and the calibration that decides whether to believe it.

Every LLM-judged benchmark faces the same question and most decline to ask it: you run the judge, you
get 0.71, you print it. Nobody can tell *0.71 because the model is decent* from *0.71 because the
judge says yes to everything*. The number is not merely useless — it is confidently useless.

These tests pin the rules that stop that happening here.
"""

from __future__ import annotations

import pytest

from financebench.evaluation.judge import (
    MAX_FALSE_POSITIVE_RATE,
    MIN_ACCURACY,
    CalibrationCase,
    build_calibration_set,
    judge_answer,
    score_calibration,
)
from financebench.models.base import ModelProvider
from financebench.schemas.common import AnswerType, SplitOrigin
from financebench.schemas.model_io import ModelRequest, ModelResponse, ModelSpec
from financebench.schemas.sample import (
    CanonicalSample,
    EvaluationSpec,
    GoldAnswer,
    SampleContext,
    SourceInfo,
)


def _sample(reference: str = "Coverage rose to 40.5 in 2023.") -> CanonicalSample:
    return CanonicalSample(
        benchmark="secque",
        benchmark_version="test",
        split="test",
        split_origin=SplitOrigin.OFFICIAL,
        sample_id="secque:test:q_Ra001",
        task_family="secque_ratio",
        capability_tags=("analysis",),
        question="How did coverage evolve?",
        context=SampleContext(
            text=(
                "Apple Inc. 10-K form for the fiscal year ended 2023-09-30, page 29: EBIT 108949",
            )
        ),
        gold=GoldAnswer(answer=reference, answer_type=AnswerType.TEXT),
        evaluation=EvaluationSpec(),
        source=SourceInfo(license="MIT", url="https://e.com", redistributable=True),
        metadata={"category": "Ratio", "company": "Apple Inc.", "period": "2023-09-30"},
    )


class _Judge(ModelProvider):
    name = "mock"

    def __init__(self, content: str) -> None:
        self._content = content

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(provider="mock", model="judge", content=self._content, parsed=True)

    async def aclose(self) -> None:
        return None


# --------------------------------------------------------------------------- no self-judging


@pytest.mark.asyncio
async def test_a_model_may_not_judge_its_own_family() -> None:
    """A model grading its own output is not evidence. And a *warning* is not enough — somebody
    reads past a warning, and the resulting number looks exactly like a real one."""
    with pytest.raises(ValueError, match="not evidence"):
        await judge_answer(
            _sample(),
            "some answer",
            provider=_Judge("{}"),
            judge=ModelSpec.parse("ollama/qwen2.5:7b"),
            candidate=ModelSpec.parse("ollama/qwen2.5:3b"),
        )


@pytest.mark.asyncio
async def test_a_different_family_may_judge() -> None:
    verdict = await judge_answer(
        _sample(),
        "Coverage rose to 40.5.",
        provider=_Judge('{"correct": true, "overall_correctness": 5, "rationale": "right"}'),
        judge=ModelSpec.parse("ollama/qwen3:8b"),
        candidate=ModelSpec.parse("ollama/qwen2.5:3b"),
    )
    assert verdict.valid is True
    assert verdict.correct is True
    assert verdict.judge_model == "ollama/qwen3:8b"


# --------------------------------------------------------------------------- a failed judge is not
# a failed candidate


@pytest.mark.asyncio
async def test_a_judge_that_fails_does_not_produce_a_zero_for_the_candidate() -> None:
    """The single most common way an LLM-judged benchmark lies: the judge errors, and the harness
    quietly records a 0 for a candidate that may well have answered perfectly."""
    verdict = await judge_answer(
        _sample(),
        "a perfectly good answer",
        provider=_Judge("I'm sorry, I can't help with that."),
        judge=ModelSpec.parse("ollama/qwen3:8b"),
        retries=0,
    )
    assert verdict.valid is False, "the JUDGE failed"
    assert "THE JUDGE FAILED" in verdict.rationale
    assert verdict.error


def test_an_invalid_judgment_is_counted_as_a_judge_failure_not_a_candidate_failure() -> None:
    sample = _sample()
    cases = [
        CalibrationCase(sample, "right", True, "verbatim_expert_answer"),
        CalibrationCase(sample, "wrong", False, "invented_number"),
    ]
    report = score_calibration(cases, [True, None])

    assert report.invalid_judgments == 1
    assert report.n == 1, "only the judgment that actually happened is scored"


# --------------------------------------------------------------------------- the bar


def test_a_judge_that_waves_everything_through_fails_calibration() -> None:
    """The failure mode that matters. A pushover judge says "correct" to everything and produces a
    beautiful, meaningless number — and it inflates every score it touches, making every model look
    safer than it is. In finance that is the failure that costs money."""
    sample = _sample()
    cases = [
        CalibrationCase(sample, "right", True, "verbatim_expert_answer"),
        CalibrationCase(sample, "right", True, "correct_but_concise"),
        CalibrationCase(sample, "wrong company", False, "wrong_company"),
        CalibrationCase(sample, "invented figure", False, "invented_number"),
        CalibrationCase(sample, "inverted", False, "inverted_direction"),
        CalibrationCase(sample, "nonsense", False, "fluent_but_unsupported"),
    ]
    yes_to_everything = [True] * 6

    report = score_calibration(cases, yes_to_everything)
    assert report.false_positive_rate == 1.0
    assert report.passed is False
    assert "waves wrong answers through" in report.verdict


def test_a_judge_that_rejects_everything_also_fails() -> None:
    """The other direction. Harsh is not dangerous, but it is still not calibrated — and a set that
    was mostly wrong answers would let a reject-everything judge score well, which is why the
    calibration set is deliberately balanced."""
    sample = _sample()
    cases = [
        CalibrationCase(sample, "right", True, "verbatim_expert_answer"),
        CalibrationCase(sample, "right", True, "correct_but_concise"),
        CalibrationCase(sample, "right", True, "minor_rounding_variation"),
        CalibrationCase(sample, "wrong", False, "wrong_company"),
    ]
    report = score_calibration(cases, [False] * 4)
    assert report.false_negative_rate == 1.0
    assert report.accuracy == 0.25
    assert report.passed is False


def test_a_good_judge_passes() -> None:
    sample = _sample()
    cases = [
        CalibrationCase(sample, "right", True, "verbatim_expert_answer"),
        CalibrationCase(sample, "right", True, "correct_but_concise"),
        CalibrationCase(sample, "right", True, "minor_rounding_variation"),
        CalibrationCase(sample, "wrong", False, "wrong_company"),
        CalibrationCase(sample, "wrong", False, "invented_number"),
        CalibrationCase(sample, "wrong", False, "inverted_direction"),
    ]
    report = score_calibration(cases, [True, True, True, False, False, False])

    assert report.accuracy == 1.0
    assert report.false_positive_rate == 0.0
    assert report.passed is True
    assert "CALIBRATED" in report.verdict


def test_the_bar_is_stated_so_it_can_be_argued_with() -> None:
    """Thresholds buried in a function are thresholds nobody audits. The false-positive bound is the
    tighter of the two on purpose."""
    assert MIN_ACCURACY == 0.75
    assert MAX_FALSE_POSITIVE_RATE == 0.20
    assert MAX_FALSE_POSITIVE_RATE < (1 - MIN_ACCURACY) + 0.05


def test_a_failing_judge_is_diagnosable_not_just_a_number() -> None:
    """ "It accepts invented numbers" is actionable. "It scored 0.6" is not."""
    sample = _sample()
    cases = [
        CalibrationCase(sample, "a", False, "invented_number"),
        CalibrationCase(sample, "b", False, "invented_number"),
        CalibrationCase(sample, "c", False, "wrong_company"),
    ]
    report = score_calibration(cases, [True, True, False])  # blind to invented numbers only

    assert report.by_corruption["invented_number"] == 0.0
    assert report.by_corruption["wrong_company"] == 1.0


# --------------------------------------------------------------------------- the calibration set


def test_the_calibration_set_covers_every_way_an_answer_can_be_wrong() -> None:
    from pathlib import Path

    if not Path("data/downloads/secque/SECQUE_benchmark_Ratio.jsonl").is_file():
        pytest.skip("secque not prepared")

    from financebench.datasets.secque import SecqueAdapter

    cases = build_calibration_set(list(SecqueAdapter().load("test")), target=48)
    corruptions = {c.corruption for c in cases}

    assert {
        "verbatim_expert_answer",
        "correct_but_concise",
        "minor_rounding_variation",
        "wrong_company",
        "invented_number",
        "inverted_direction",
        "refusal_despite_sufficient_context",
        "fluent_but_unsupported",
    } <= corruptions

    # Balanced. A set that was 90% wrong answers would let a reject-everything judge score 90%.
    correct = sum(1 for c in cases if c.should_be_correct)
    assert 0.3 <= correct / len(cases) <= 0.7


def test_the_calibration_cases_are_never_reported_as_secque_tasks() -> None:
    from pathlib import Path

    if not Path("data/downloads/secque/SECQUE_benchmark_Ratio.jsonl").is_file():
        pytest.skip("secque not prepared")

    from financebench.datasets.secque import SecqueAdapter

    cases = build_calibration_set(list(SecqueAdapter().load("test")), target=16)
    assert all(c.provenance == "derived_judge_calibration" for c in cases)
