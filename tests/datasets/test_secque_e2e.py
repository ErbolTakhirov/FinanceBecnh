"""SECQUE end to end: the SEC filing reaches the model, the expert answer does not, and what comes
back is graded by metrics that know what they cannot see.

The adapter is unit-tested in `test_secque.py` and the diagnostics in `test_secque_diagnostics.py`.
This file tests the *pipeline*: that a real task can actually be run and scored without the answer key
leaking into the prompt, and that the four metrics disagree with each other in the right ways.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from financebench.datasets.secque import SecqueAdapter
from financebench.evaluation.benchmark_metrics import metrics_for_run
from financebench.execution.cache import ResponseCache
from financebench.execution.engine import RunEngine
from financebench.models.mock import MockProvider, build_mock_oracle
from financebench.prompts.renderer import render_messages
from financebench.schemas.model_io import ModelSpec
from financebench.schemas.run import RunConfig

DATA_DIR = Path("data/downloads/secque")

pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "SECQUE_benchmark_Ratio.jsonl").is_file(),
    reason="secque not prepared; run `financebench prepare secque`",
)


def _samples(n: int = 8):
    return list(SecqueAdapter().load("test"))[:n]


def test_the_sec_filing_reaches_the_model_and_the_expert_answer_does_not() -> None:
    """The one property the whole benchmark rests on. The model must see the filing — it cannot
    analyse what it was not shown — and must never see the answer."""
    for sample in _samples():
        prompt = "\n".join(m.content for m in render_messages(sample))
        assert sample.question in prompt
        assert sample.context.text[0][:300] in prompt, "the SEC excerpt must reach the model"
        assert sample.gold.answer not in prompt, "the expert answer must NOT"


@pytest.mark.asyncio
async def test_a_real_task_runs_end_to_end_and_every_metric_returns_a_verdict(
    tmp_path: Path,
) -> None:
    samples = _samples(6)

    result = await RunEngine().run(
        samples=samples,
        model=ModelSpec.parse("mock/echo-gold"),
        config=RunConfig(),
        cache=ResponseCache(tmp_path),
        provider=MockProvider(oracle=build_mock_oracle(samples)),
    )
    assert result.n_errors == 0

    for sample, prediction in zip(samples, result.predictions, strict=True):
        for metric in metrics_for_run("secque"):
            scored = metric.score(sample, prediction)
            assert scored.sample_id == sample.sample_id
            # `passed` is True, False, or None — and None is a real, meaningful verdict here, not a
            # crash. A metric that cannot see a narrative task says so.
            assert scored.passed in (True, False, None)


@pytest.mark.asyncio
async def test_the_narrative_split_is_reported_as_not_applicable_not_as_failure(
    tmp_path: Path,
) -> None:
    """SECQUE's Risk split has almost no numbers. A numeric metric must return `passed=None` there,
    not 0.0 — otherwise the run reports the metric's blindness as the model's failure, and the
    capability rollup (correctly) excludes None but would have counted the zeros."""
    from financebench.evaluation.native.secque import SecqueNumericAgreement

    risk = [s for s in SecqueAdapter().load("test") if s.metadata["category"] == "Risk"][:10]
    assert risk

    result = await RunEngine().run(
        samples=risk,
        model=ModelSpec.parse("mock/echo-gold"),
        config=RunConfig(),
        cache=ResponseCache(tmp_path),
        provider=MockProvider(oracle=build_mock_oracle(risk)),
    )

    metric = SecqueNumericAgreement()
    scored = [metric.score(s, p) for s, p in zip(risk, result.predictions, strict=True)]

    # A Risk task whose expert answer asserts no figures MUST be not-applicable, never a zero. The
    # mock echoes the gold, so a `False` here could only mean the metric had graded a narrative
    # answer on arithmetic it does not contain — the metric's blindness, printed as the model's
    # failure.
    not_applicable = [r for r in scored if r.passed is None]
    assert not_applicable, "the narrative split must produce not-applicable verdicts"

    for verdict in not_applicable:
        assert verdict.value is None
        assert "no figures" in str(verdict.details)


def test_the_hallucination_detector_applies_to_every_category() -> None:
    """Unlike numeric agreement, this one is never 'not applicable': a narrative answer that invents
    a figure has invented a figure."""
    from financebench.evaluation.native.secque import SecqueUnsupportedNumericClaim
    from financebench.execution.engine import build_request
    from financebench.schemas.model_io import FinancialAnswer, ModelResponse
    from financebench.schemas.prediction import Prediction

    metric = SecqueUnsupportedNumericClaim()
    model = ModelSpec.parse("ollama/qwen2.5:3b")

    for sample in _samples(6):
        prediction = Prediction(
            sample_id=sample.sample_id,
            benchmark="secque",
            split="test",
            request=build_request(sample, model, RunConfig()),
            created_at="t",
            response=ModelResponse(
                provider="ollama",
                model="x",
                content="{}",
                financial_answer=FinancialAnswer(answer="The figure is 987654321."),
                parsed=True,
            ),
        )
        scored = metric.score(sample, prediction)
        assert scored.passed is False, "987654321 is in no SEC filing on earth"
