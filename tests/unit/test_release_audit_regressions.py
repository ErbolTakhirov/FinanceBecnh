"""Regressions for the defects the v0.1.0-rc1 release audit found.

Every one of these produced a *plausible number* rather than an exception, and three of the four
moved a score in the direction that flatters the model or the platform. That is the failure mode
this suite exists to catch: a benchmark that crashes gets fixed on Tuesday, and a benchmark that
quietly reports 0.900 gets cited.
"""

from __future__ import annotations

from financebench.evaluation.capability_map import CapabilityDimension, rollup_capabilities
from financebench.evaluation.gates import GATE_THRESHOLDS, evaluate_gates
from financebench.evaluation.metrics.base import aggregate_metric
from financebench.schemas.common import AnswerType, SplitOrigin
from financebench.schemas.metric import MetricResult
from financebench.schemas.sample import CanonicalSample, GoldAnswer, SampleContext, SourceInfo


def _secque_sample(sample_id: str) -> CanonicalSample:
    return CanonicalSample(
        sample_id=sample_id,
        benchmark="secque",
        benchmark_version="hf@894196b8",
        split="test",
        split_origin=SplitOrigin.OFFICIAL,
        task_family="analysis",
        capability_tags=("evidence_grounding", "table_text"),
        question="What drove the change in operating margin?",
        context=SampleContext(text=("... a 10-K excerpt ...",)),
        gold=GoldAnswer(answer="Margin fell on higher input costs.", answer_type=AnswerType.TEXT),
        source=SourceInfo(license="MIT", url="https://huggingface.co/datasets/nogabenyoash/SecQue"),
    )


# --------------------------------------------------------------------------------------------
# 1. A dimension must be scored by the metric that MEASURES it.
# --------------------------------------------------------------------------------------------


def test_secque_dimensions_are_not_all_the_hallucination_detector() -> None:
    """The bug: SECQUE's preferred metric is ``secque_unsupported_numeric_claim`` — an
    *absence-of-hallucination* rate — and every dimension its tags reached was fed that metric.

    So a live 7B run published ``document_grounding: 0.900`` and ``table_text_reasoning: 0.900``
    (and a Financial Core Score of 0.900) while agreeing with the expert's figures 11 % of the time
    and naming the wrong company in 55 % of its answers. Both models scored 0.900. The metrics that
    discriminate between them fed nothing.

    A model that emits no numbers at all scores 1.000 on "did it invent a number", which is why that
    metric cannot be allowed to stand in for grounding.
    """
    samples = [_secque_sample(f"secque:test:q{i}") for i in range(4)]

    # The model invented nothing (the hallucination detector is delighted) ...
    unsupported = [
        MetricResult(
            sample_id=s.sample_id,
            metric_name="secque_unsupported_numeric_claim",
            value=True,
            passed=True,
        )
        for s in samples
    ]
    # ... but it agrees with almost none of the expert's figures, and mostly names the wrong filing.
    agreement = [
        MetricResult(
            sample_id=s.sample_id,
            metric_name="secque_numeric_agreement",
            value=0.0 if i < 3 else 1.0,
            passed=i >= 3,
        )
        for i, s in enumerate(samples)
    ]
    filing = [
        MetricResult(
            sample_id=s.sample_id,
            metric_name="secque_filing_identification",
            value=i >= 2,
            passed=i >= 2,
        )
        for i, s in enumerate(samples)
    ]

    aggregates = rollup_capabilities(
        samples, unsupported, all_results=[*unsupported, *agreement, *filing]
    )

    grounding = aggregates[CapabilityDimension.DOCUMENT_GROUNDING]
    table_text = aggregates[CapabilityDimension.TABLE_TEXT_REASONING]

    # Grounding is "is this about the right filing", not "did it avoid inventing a number".
    assert grounding.mean == 0.5, "document_grounding must come from filing identification"
    assert table_text.mean == 0.25, "table_text_reasoning must come from numeric agreement"

    # The regression itself: neither may be the hallucination rate (1.0).
    assert grounding.mean != 1.0
    assert table_text.mean != 1.0

    # And the discarded dimension must not reappear: SECQUE cannot score analytical insight without
    # a calibrated judge, and no local judge has passed calibration.
    assert CapabilityDimension.ANALYTICAL_INSIGHT not in aggregates


# --------------------------------------------------------------------------------------------
# 2. `n` is what was GRADED, not what was offered.
# --------------------------------------------------------------------------------------------


def test_n_counts_only_the_samples_a_metric_actually_graded() -> None:
    """``n: 80`` on a mean computed over 62 samples overstates the evidence by a third.

    The repo's own release schema says ``n`` is "samples actually graded — excluding not-applicable
    ones". The code disagreed with the schema, and the schema was right.
    """
    results = [
        MetricResult(sample_id="a", metric_name="m", value=True, passed=True),
        MetricResult(sample_id="b", metric_name="m", value=False, passed=False),
        # Not applicable: this question contains no figure to agree with. Not a zero.
        MetricResult(sample_id="c", metric_name="m", value=None, passed=None),
        MetricResult(sample_id="d", metric_name="m", value=None, passed=None),
    ]
    aggregate = aggregate_metric("m", results)

    assert aggregate.n == 2, "n must be the graded count"
    assert aggregate.n_not_applicable == 2, "the excluded ones are reported, not hidden"
    assert aggregate.mean == 0.5, "and the mean is over the graded ones only"


def test_an_all_not_applicable_metric_is_not_a_zero() -> None:
    results = [
        MetricResult(sample_id=str(i), metric_name="m", value=None, passed=None) for i in range(5)
    ]
    aggregate = aggregate_metric("m", results)

    assert aggregate.mean is None, "None is not zero — it means NOT MEASURED"
    assert aggregate.n == 0
    assert aggregate.n_not_applicable == 5


# --------------------------------------------------------------------------------------------
# 3. The sandbox gate: an escape is a failed release, and an untested sandbox is not a pass.
# --------------------------------------------------------------------------------------------


def test_a_single_sandbox_escape_fails_a_critical_gate() -> None:
    report = evaluate_gates(
        failures=[],
        n_scored=100,
        numeric_accuracy=0.99,
        # 99 of 100 probes refused. One did not. That is not a 99 % score, it is a breach.
        tool_security_rejection=0.99,
    )
    gate = next(g for g in report.gates if g.gate_name == "tool_security_rejection_min")

    assert GATE_THRESHOLDS["tool_security_rejection_min"] == 1.0
    assert gate.passed is False
    assert report.any_critical_gate_failed is True


def test_a_run_with_no_tools_does_not_pass_the_sandbox_gate_by_default() -> None:
    """A run that never offered a tool has said nothing about the sandbox. `None` is NOT TESTED —
    it is neither a pass (a guarantee we did not earn) nor a fail (a defect we did not observe)."""
    report = evaluate_gates(
        failures=[], n_scored=100, numeric_accuracy=0.99, tool_security_rejection=None
    )
    gate = next(g for g in report.gates if g.gate_name == "tool_security_rejection_min")

    assert gate.skipped is True
    assert gate.passed is None, "not tested is not passed"
    assert gate.observed is None
    assert report.any_critical_gate_failed is False, "an untested gate is not a failed one either"


def test_a_sandbox_that_refused_everything_passes() -> None:
    report = evaluate_gates(
        failures=[], n_scored=100, numeric_accuracy=0.99, tool_security_rejection=1.0
    )
    gate = next(g for g in report.gates if g.gate_name == "tool_security_rejection_min")

    assert gate.passed is True
    assert report.any_critical_gate_failed is False
