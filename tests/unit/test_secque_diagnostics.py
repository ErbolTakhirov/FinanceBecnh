"""SECQUE Layer A: deterministic diagnostics, and the discipline that keeps them honest.

The single rule these tests exist to enforce: **a metric that cannot see a question says so, rather
than scoring it zero.**

SECQUE's Risk split is 85 narrative tasks about cybersecurity and fraud. Running a numeric metric
over them and reporting 0.0 would not be measuring a model's failure — it would be measuring the
metric's blindness and printing it as the model's fault. This project has already shipped that exact
bug once, in the capability rollup, and it understated a real model by 68 %.
"""

from __future__ import annotations

from financebench.evaluation.native.secque import (
    SecqueComparisonDirection,
    SecqueFilingIdentification,
    SecqueNumericAgreement,
    SecqueUnsupportedNumericClaim,
)
from financebench.execution.engine import build_request
from financebench.schemas.common import AnswerType, SplitOrigin
from financebench.schemas.model_io import FinancialAnswer, ModelResponse, ModelSpec
from financebench.schemas.prediction import Prediction
from financebench.schemas.run import RunConfig
from financebench.schemas.sample import (
    CanonicalSample,
    EvaluationSpec,
    GoldAnswer,
    SampleContext,
    SourceInfo,
)

MODEL = ModelSpec.parse("ollama/qwen2.5:3b")


def _sample(*, context: str, reference: str, category: str = "Ratio") -> CanonicalSample:
    from financebench.datasets.secque.adapter import _company_and_period

    company, period = _company_and_period(context)
    return CanonicalSample(
        benchmark="secque",
        benchmark_version="test",
        split="test",
        split_origin=SplitOrigin.OFFICIAL,
        sample_id="secque:test:q_Ra001",
        task_family=f"secque_{category.lower()}",
        capability_tags=("analysis",),
        question="How did the interest coverage ratio evolve?",
        context=SampleContext(text=(context,)),
        gold=GoldAnswer(answer=reference, answer_type=AnswerType.TEXT),
        evaluation=EvaluationSpec(),
        source=SourceInfo(license="MIT", url="https://e.com", redistributable=True),
        metadata={"category": category, "company": company, "period": period},
    )


def _prediction(sample: CanonicalSample, answer: str) -> Prediction:
    return Prediction(
        sample_id=sample.sample_id,
        benchmark="secque",
        split="test",
        request=build_request(sample, MODEL, RunConfig()),
        created_at="t",
        response=ModelResponse(
            provider="ollama",
            model="x",
            content="{}",
            financial_answer=FinancialAnswer(answer=answer),
            parsed=True,
        ),
    )


CONTEXT = (
    "Apple Inc. 10-K form for the fiscal year ended 2023-09-30, page 29:\n"
    "Operating income 108949 114301 . Interest expense 2687 2931 ."
)


# --------------------------------------------------------------------------- None is not zero


def test_a_narrative_task_is_not_applicable_to_a_numeric_metric_not_a_zero() -> None:
    """The rule the whole file exists for.

    The Risk split says "cybersecurity, fraud, and data protection". It has no numbers. A numeric
    metric reporting 0.0 here would be scoring an essay on its arithmetic.
    """
    sample = _sample(
        context=CONTEXT,
        reference=(
            "JPMorgan's 10-K identifies operational risks including cybersecurity, fraud, and data "
            "protection. Increasingly sophisticated cyberattacks could cause reputational harm."
        ),
        category="Risk",
    )
    result = SecqueNumericAgreement().score(sample, _prediction(sample, "Cyber and fraud risk."))

    assert result.passed is None, "not applicable — NOT a failure"
    assert result.value is None
    assert "no figures" in str(result.details)


def test_a_numeric_task_is_graded_because_it_can_be() -> None:
    sample = _sample(
        context=CONTEXT,
        reference="EBIT = $108,949 million. Interest = $2,687 million. Ratio = 40.5.",
    )
    good = SecqueNumericAgreement().score(
        sample, _prediction(sample, "EBIT 108949, interest 2687, coverage 40.5x")
    )
    bad = SecqueNumericAgreement().score(sample, _prediction(sample, "Roughly 3.2x, I think."))

    assert good.passed is True
    assert bad.passed is False


def test_years_are_not_counted_as_matched_financial_figures() -> None:
    """Without this, "2023" in a sentence about 2023 counts as agreement with the expert, and every
    model looks well-grounded on every task."""
    sample = _sample(context=CONTEXT, reference="In 2023 the ratio was 40.5, up from 39.0 in 2022.")
    result = SecqueNumericAgreement().score(
        sample, _prediction(sample, "In 2023 and 2022 the figures moved around.")
    )
    assert result.passed is False, "quoting only the years is not agreeing with the expert"


# --------------------------------------------------------------------------- invented numbers


def test_a_figure_that_appears_nowhere_in_the_filing_is_an_invention() -> None:
    """The most important metric here, and the only one a persuasive model cannot talk past.
    Fluent financial prose is exactly what a language model is best at. A number that is not in the
    document is not a matter of opinion."""
    sample = _sample(context=CONTEXT, reference="Ratio = 40.5")
    invented = SecqueUnsupportedNumericClaim().score(
        sample, _prediction(sample, "Operating income was 777888 million, giving a ratio of 289.5.")
    )
    assert invented.passed is False
    assert "NOWHERE" in str(invented.details)

    clean = SecqueUnsupportedNumericClaim().score(
        sample, _prediction(sample, "Operating income 108949 against interest 2687.")
    )
    assert clean.passed is True


def test_groundedness_is_judged_against_the_filing_not_against_the_answer_key() -> None:
    """A model that finds a correct figure the expert did not happen to quote has not invented it.
    Grading "supported" against the gold would mark real evidence as hallucination."""
    sample = _sample(context=CONTEXT, reference="Ratio = 40.5")  # expert never mentions 114301
    result = SecqueUnsupportedNumericClaim().score(
        sample, _prediction(sample, "Prior-year operating income was 114301 million.")
    )
    assert result.passed is True, "114301 IS in the filing, though not in the expert's answer"


def test_the_hallucination_check_applies_to_narrative_tasks_too() -> None:
    """A narrative answer that invents a figure has invented a figure. Unlike numeric agreement, this
    is never 'not applicable'."""
    sample = _sample(context=CONTEXT, reference="Cyber and fraud risks.", category="Risk")
    result = SecqueUnsupportedNumericClaim().score(
        sample, _prediction(sample, "Cyber losses totalled 45231 million last year.")
    )
    assert result.passed is False


# --------------------------------------------------------------------------- direction and filing


def test_inverting_the_direction_of_travel_is_caught() -> None:
    """In finance the sign is not a detail. "Coverage improved" and "coverage deteriorated" are the
    same sentence with opposite consequences — and a model can quote every correct figure and still
    invert the conclusion."""
    sample = _sample(context=CONTEXT, reference="Interest coverage increased, rising to 40.5.")
    metric = SecqueComparisonDirection()

    assert (
        metric.score(sample, _prediction(sample, "Coverage rose over the period.")).passed is True
    )
    inverted = metric.score(sample, _prediction(sample, "Coverage declined over the period."))
    assert inverted.passed is False
    assert "INVERTED" in str(inverted.details)


def test_direction_is_not_applicable_when_the_expert_states_none() -> None:
    sample = _sample(context=CONTEXT, reference="The ratio was 40.5 in 2023.")
    result = SecqueComparisonDirection().score(sample, _prediction(sample, "It was 40.5."))
    assert result.passed is None


def test_analysing_the_wrong_company_is_caught() -> None:
    """The cheapest catastrophic error, and one a fluent answer hides completely: an analysis of the
    wrong filing is not partially correct, it is a confident answer to a question nobody asked."""
    sample = _sample(context=CONTEXT, reference="Apple's coverage was 40.5.")
    metric = SecqueFilingIdentification()

    assert metric.score(sample, _prediction(sample, "Apple's coverage was 40.5x.")).passed is True
    wrong = metric.score(sample, _prediction(sample, "Microsoft's coverage was 40.5x in 2019."))
    assert wrong.passed is False
    assert "WRONG FILING" in str(wrong.details)


def test_a_refusal_is_not_a_wrong_company_error() -> None:
    """A model that correctly declines has misidentified nothing. Grading a refusal as a wrong-filing
    error is the same class of bug this project has already fixed twice."""
    sample = _sample(context=CONTEXT, reference="Apple's coverage was 40.5.")
    result = SecqueFilingIdentification().score(
        sample, _prediction(sample, "The provided excerpt does not contain enough information.")
    )
    assert result.passed is None


def test_a_three_year_trend_is_not_a_wrong_period_error() -> None:
    """SECQUE questions routinely ask about multi-year trends. Flagging the earlier years of a trend
    as 'wrong period' would fail the model for answering the question it was asked."""
    sample = _sample(context=CONTEXT, reference="Coverage across 2021-2023.")
    result = SecqueFilingIdentification().score(
        sample, _prediction(sample, "Apple's coverage in 2021, 2022 and 2023 improved.")
    )
    assert result.passed is True
