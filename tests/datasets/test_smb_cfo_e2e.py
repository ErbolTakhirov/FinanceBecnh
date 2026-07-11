"""SMB-CFO end to end: generated books -> canonical samples -> a run -> oracle-graded metrics.

The oracles themselves are property-tested in `test_smb_cfo_oracles.py`. This file tests the
*pipeline*: that the books reach the model, that the gold never does, that a perfect answer scores
perfectly, and that the three metrics measure the three different things they claim to.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from financebench.datasets.smb_cfo import SmbCfoAdapter
from financebench.evaluation.native.smb_cfo import (
    SmbCfoAccuracy,
    SmbCfoInjectionResistance,
    SmbCfoRefusalCorrectness,
)
from financebench.execution.cache import ResponseCache
from financebench.execution.engine import RunEngine
from financebench.models.mock import MockProvider, build_mock_oracle
from financebench.prompts.renderer import render_messages
from financebench.schemas.manifest import AdapterStatus
from financebench.schemas.model_io import ModelSpec
from financebench.schemas.run import RunConfig


def _adapter() -> SmbCfoAdapter:
    return SmbCfoAdapter()


# --------------------------------------------------------------------------- manifest / splits


def test_the_manifest_says_no_llm_ever_writes_a_gold_answer() -> None:
    manifest = _adapter().manifest()
    assert manifest.status is AdapterStatus.FULLY_SUPPORTED

    limitations = " ".join(manifest.known_limitations)
    assert "No LLM ever" in limitations
    assert "uncontaminated" in limitations
    assert "PAIRED" in limitations, "the EN/RU pairing is what makes a bilingual gap meaningful"


def test_every_split_generates_and_validates() -> None:
    counts = {
        split: len(_adapter().load(split))
        for split in ("public", "adversarial", "bilingual", "smoke")
    }
    assert counts == {"public": 300, "adversarial": 150, "bilingual": 100, "smoke": 12}


def test_the_full_trap_taxonomy_is_actually_generated() -> None:
    """A third of it silently wasn't: injections punched holes at fixed positions in the index
    cycle, and any trap whose slot always collided with a hole never appeared at all."""
    families = {s.task_family for s in _adapter().load("adversarial")}
    assert families == {
        "prompt_injection",
        "trap_wrong_period",
        "trap_gross_vs_net",
        "trap_unanswerable_forecast",
        "trap_unanswerable_causality",
        "trap_missing_fx_rate",
        "trap_conflicting_totals",
    }


def test_the_bilingual_split_is_paired_not_merely_translated() -> None:
    """The EN and RU questions must resolve to the SAME gold value, from the same business and the
    same oracle. Otherwise a measured 'EN/RU gap' is just measuring my Russian."""
    samples = _adapter().load("bilingual")
    by_key: dict[tuple[str, str], dict[str, object]] = {}
    for sample in samples:
        seed = sample.metadata["seed"]
        by_key.setdefault((seed, sample.task_family), {})[sample.language] = sample

    pairs = [v for v in by_key.values() if "en" in v and "ru" in v]
    assert len(pairs) >= 40, "the split must actually contain pairs"

    for pair in pairs:
        en, ru = pair["en"], pair["ru"]
        assert en.gold.answer == ru.gold.answer  # type: ignore[union-attr]
        assert en.gold.numeric_value == ru.gold.numeric_value  # type: ignore[union-attr]
        assert en.question != ru.question  # type: ignore[union-attr]
        assert ru.language == "ru"  # type: ignore[union-attr]


# --------------------------------------------------------------------------- the books reach the
# model; the gold does not


def test_the_books_are_rendered_into_the_prompt() -> None:
    sample = _adapter().load("smoke")[0]
    prompt = "\n".join(m.content for m in render_messages(sample))

    for expected in ("txn_id", "invoice_id", "Opening balance", "Rate to"):
        assert expected in prompt, f"the model cannot answer without {expected!r} in its context"


def test_the_oracle_answer_never_reaches_the_prompt() -> None:
    """The gold is a Decimal computed from the books. If it appeared in the prompt, every question
    would be a lookup rather than a calculation.

    Note the empty-string guard: `"" in prompt` is ALWAYS true, so without it a sample whose oracle
    recorded no intermediate detail would pass this test vacuously — and a vacuous leak test is
    worse than none, because it reads as a guarantee.
    """
    checked = 0
    for sample in _adapter().load("smoke"):
        detail = sample.metadata["oracle_detail"]
        if not detail:
            continue
        checked += 1
        prompt = "\n".join(m.content for m in render_messages(sample))
        # The oracle's intermediate workings (cash, burn, revenue...) must not leak either — they
        # would hand over the derivation even where they do not hand over the final number.
        assert detail[:40] not in prompt

    assert checked > 0, "no sample carried oracle detail — this test would have proven nothing"


# --------------------------------------------------------------------------- scoring


@pytest.mark.asyncio
async def test_a_perfect_answer_scores_perfectly(tmp_path: Path) -> None:
    """If echoing the oracle's own answer does not score, the metric is measuring our plumbing."""
    samples = [s for s in _adapter().load("public") if s.gold.numeric_value is not None][:40]

    result = await RunEngine().run(
        samples=samples,
        model=ModelSpec.parse("mock/echo-gold"),
        config=RunConfig(),
        cache=ResponseCache(tmp_path),
        provider=MockProvider(oracle=build_mock_oracle(samples)),
    )
    metric = SmbCfoAccuracy()
    passed = [metric.score(s, p).passed for s, p in zip(samples, result.predictions, strict=True)]
    assert all(passed)


@pytest.mark.asyncio
async def test_a_wrong_answer_scores_zero(tmp_path: Path) -> None:
    samples = [s for s in _adapter().load("public") if s.gold.numeric_value is not None][:40]

    result = await RunEngine().run(
        samples=samples,
        model=ModelSpec.parse("mock/always-wrong"),
        config=RunConfig(),
        cache=ResponseCache(tmp_path),
        provider=MockProvider(oracle=build_mock_oracle(samples)),
    )
    metric = SmbCfoAccuracy()
    passed = [metric.score(s, p).passed for s, p in zip(samples, result.predictions, strict=True)]
    assert not any(passed)


@pytest.mark.asyncio
async def test_refusing_an_unanswerable_question_is_correct_and_answering_it_is_not(
    tmp_path: Path,
) -> None:
    """The single most dangerous failure: producing a confident number for a question the books
    cannot answer, with nothing in the output to warn you."""
    samples = [s for s in _adapter().load("adversarial") if s.evaluation.should_refuse][:20]
    assert samples

    metric = SmbCfoRefusalCorrectness()

    refusing = await RunEngine().run(
        samples=samples,
        model=ModelSpec.parse("mock/refuse"),
        config=RunConfig(),
        cache=ResponseCache(tmp_path / "a"),
        provider=MockProvider(oracle=build_mock_oracle(samples)),
    )
    assert all(
        metric.score(s, p).passed for s, p in zip(samples, refusing.predictions, strict=True)
    )

    answering = await RunEngine().run(
        samples=samples,
        model=ModelSpec.parse("mock/always-wrong"),
        config=RunConfig(),
        cache=ResponseCache(tmp_path / "b"),
        provider=MockProvider(oracle=build_mock_oracle(samples)),
    )
    scored = [metric.score(s, p) for s, p in zip(samples, answering.predictions, strict=True)]
    assert not any(r.passed for r in scored)
    assert all("FAILED REFUSAL" in str(r.details) for r in scored)


@pytest.mark.asyncio
async def test_accuracy_does_not_punish_a_correct_refusal(tmp_path: Path) -> None:
    """Conflating 'could not compute' with 'correctly declined to compute' would make a model that
    refuses everything look identical to one that computes nothing. Those are opposite behaviours."""
    samples = [s for s in _adapter().load("adversarial") if s.evaluation.should_refuse][:10]

    result = await RunEngine().run(
        samples=samples,
        model=ModelSpec.parse("mock/refuse"),
        config=RunConfig(),
        cache=ResponseCache(tmp_path),
        provider=MockProvider(oracle=build_mock_oracle(samples)),
    )
    scored = [
        SmbCfoAccuracy().score(s, p) for s, p in zip(samples, result.predictions, strict=True)
    ]
    assert all(r.passed is None for r in scored), "unanswerable questions are N/A here, not zero"


# --------------------------------------------------------------------------- injection resistance


def test_injection_resistance_is_not_applicable_where_there_is_no_injection() -> None:
    """Scoring a clean question as 'resisted the attack' would manufacture a reassuring number out
    of nothing."""
    from financebench.execution.engine import build_request
    from financebench.schemas.model_io import FinancialAnswer, ModelResponse
    from financebench.schemas.prediction import Prediction

    sample = next(s for s in _adapter().load("public"))
    request = build_request(sample, ModelSpec.parse("ollama/qwen2.5:3b"), RunConfig())
    prediction = Prediction(
        sample_id=sample.sample_id,
        benchmark="smb_cfo",
        split="public",
        request=request,
        created_at="t",
        response=ModelResponse(
            provider="ollama",
            model="x",
            content="{}",
            financial_answer=FinancialAnswer(answer="123", numeric_value=123.0),
            parsed=True,
        ),
    )
    result = SmbCfoInjectionResistance().score(sample, prediction)
    assert result.passed is None


def test_a_model_that_reports_the_canary_is_recorded_as_having_obeyed_its_data() -> None:
    from financebench.datasets.smb_cfo.adversarial import INJECTION_CANARY
    from financebench.execution.engine import build_request
    from financebench.schemas.model_io import FinancialAnswer, ModelResponse
    from financebench.schemas.prediction import Prediction

    sample = next(
        s for s in _adapter().load("adversarial") if s.metadata.get("prompt_injection") == "true"
    )
    request = build_request(sample, ModelSpec.parse("ollama/qwen2.5:3b"), RunConfig())

    def prediction_for(value: float) -> Prediction:
        return Prediction(
            sample_id=sample.sample_id,
            benchmark="smb_cfo",
            split="adversarial",
            request=request,
            created_at="t",
            response=ModelResponse(
                provider="ollama",
                model="x",
                content="{}",
                financial_answer=FinancialAnswer(answer=str(value), numeric_value=value),
                parsed=True,
            ),
        )

    metric = SmbCfoInjectionResistance()

    obeyed = metric.score(sample, prediction_for(float(INJECTION_CANARY)))
    assert obeyed.passed is False
    assert "security hole" in str(obeyed.details)

    resisted = metric.score(sample, prediction_for(12345.67))
    assert resisted.passed is True


def test_the_injection_attack_is_visible_in_the_prompt_the_model_receives() -> None:
    """Guards the guard: an attack that never reached the model would make every model look
    perfectly resistant."""
    sample = next(
        s for s in _adapter().load("adversarial") if s.metadata.get("prompt_injection") == "true"
    )
    prompt = "\n".join(m.content for m in render_messages(sample))
    assert "1000000" in prompt
