"""Deterministic mock provider — a *simulator*, not a model under test.

The mock reads the ``simulation_context`` that the execution engine attaches to each request
**only** when the target provider is ``mock`` (real providers never see this channel — see
``ModelRequest.simulation_context``). This lets the smoke benchmark and Milestone 1's acceptance
bar run fully offline, produce byte-stable artifacts, and — crucially — *differentiate*
behaviors so scoring is demonstrably meaningful rather than trivially 100% or 0%:

- ``echo-gold`` returns the exact gold answer verbatim (the happy path).
- ``formatting-noise`` returns the right number wrapped in messy prose (commas, currency
  symbols, percent signs) — exercises the numeric parser (Milestone 2) rather than the mock
  itself.
- ``always-wrong`` returns a deterministic, obviously-wrong numeric answer.
- ``refuse`` always declines to answer (exercises refusal/``should_refuse`` grading).
- ``error`` / ``timeout`` deterministically raise a non-retryable / retryable
  :class:`~financebench.utils.errors.ProviderError` (exercises backoff and ``errors.jsonl``).

Because the mock can see the answer key, **mock scores validate the pipeline, not model
quality.** That separation is the whole point of the ``simulation_context`` channel.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import ClassVar

from financebench.models.base import ModelProvider, ProviderCapabilities, register_provider
from financebench.schemas.model_io import FinancialAnswer, ModelRequest, ModelResponse, TokenUsage
from financebench.utils.errors import ProviderResponseError, ProviderTimeoutError

__all__ = ["MockProvider"]


def _tok(text: str) -> int:
    """A crude but deterministic token estimate (~4 chars/token)."""
    return max(1, len(text) // 4)


@dataclass(frozen=True)
class _GoldContext:
    """Typed view over the request's ``simulation_context`` (mock-only)."""

    gold_answer: str = ""
    gold_numeric_value: float | None = None
    unit: str | None = None

    @classmethod
    def from_ctx(cls, ctx: Mapping[str, object]) -> _GoldContext:
        numeric = ctx.get("gold_numeric_value")
        return cls(
            gold_answer=str(ctx.get("gold_answer", "")),
            gold_numeric_value=float(numeric) if isinstance(numeric, int | float) else None,
            unit=str(ctx["unit"]) if ctx.get("unit") is not None else None,
        )


def _messy_number(value: float | None, unit: str | None) -> str:
    """Render a number the way a real model's prose often does: commas, currency signs,
    percent signs, and parenthesized negatives — deliberately hostile to a naive ``float()``
    call so the numeric parser (Milestone 2) has something real to prove itself against."""
    if value is None:
        return "an unspecified amount"
    if unit == "percent":
        return f"{value:.2f}%"
    magnitude = abs(value)
    formatted = f"{magnitude:,.2f}"
    if unit in {"usd", "usd_millions", "usd_thousands", "usd_billions"}:
        formatted = f"${formatted}"
    return f"({formatted})" if value < 0 else formatted


def _echo_gold(ctx: _GoldContext) -> FinancialAnswer:
    return FinancialAnswer(
        answer=ctx.gold_answer,
        numeric_value=ctx.gold_numeric_value,
        unit=ctx.unit,
        brief_explanation="Directly taken from the referenced data.",
    )


def _formatting_noise(ctx: _GoldContext) -> FinancialAnswer:
    noisy = _messy_number(ctx.gold_numeric_value, ctx.unit)
    return FinancialAnswer(
        answer=f"Based on the filing, the figure comes out to approximately {noisy}, "
        "per the table referenced above.",
        numeric_value=ctx.gold_numeric_value,
        unit=ctx.unit,
        brief_explanation="Derived from the referenced table.",
    )


def _always_wrong(ctx: _GoldContext) -> FinancialAnswer:
    # Deterministically wrong, but not by an amount so large the numeric-tolerance metric
    # would treat it as a formatting artifact rather than a genuine miss.
    wrong_value = (ctx.gold_numeric_value or 0.0) + 999.0
    return FinancialAnswer(answer=str(wrong_value), numeric_value=wrong_value, unit=ctx.unit)


def _refuse(_: _GoldContext) -> FinancialAnswer:
    return FinancialAnswer(
        answer="I don't have enough information in the provided context to answer this.",
        insufficient_information=True,
    )


_ANSWER_PROFILES: dict[str, Callable[[_GoldContext], FinancialAnswer]] = {
    "echo-gold": _echo_gold,
    "formatting-noise": _formatting_noise,
    "always-wrong": _always_wrong,
    "refuse": _refuse,
}

# Fixed simulated latencies keep artifacts byte-stable regardless of the host clock.
_LATENCY_MS: dict[str, float] = {
    "echo-gold": 5.0,
    "formatting-noise": 6.0,
    "always-wrong": 4.0,
    "refuse": 3.0,
}


@register_provider("mock")
class MockProvider(ModelProvider):
    """A deterministic, offline financial-answer simulator with selectable profiles."""

    provider = "mock"

    PROFILES: ClassVar[tuple[str, ...]] = (*_ANSWER_PROFILES, "error", "timeout")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> MockProvider:
        return cls()

    def capabilities(self, model: str) -> ProviderCapabilities:
        return ProviderCapabilities(
            text=True,
            json_mode=True,
            streaming=True,
            max_context_tokens=32_768,
            reports_usage=True,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        profile = request.model.model
        if profile not in self.PROFILES:
            raise ProviderResponseError(
                f"unknown mock profile {profile!r}; available: {list(self.PROFILES)}",
                provider="mock",
                retryable=False,
            )
        if profile == "timeout":
            raise ProviderTimeoutError(
                "mock/timeout deliberately times out", provider="mock", retryable=True
            )
        if profile == "error":
            raise ProviderResponseError(
                "mock/error deliberately fails", provider="mock", retryable=False
            )

        situation = _GoldContext.from_ctx(request.simulation_context or {})
        answer = _ANSWER_PROFILES[profile](situation)
        content = answer.to_json()
        prompt_tokens = sum(_tok(m.content) for m in request.messages)
        completion_tokens = _tok(content)
        return ModelResponse(
            provider="mock",
            model=profile,
            content=content,
            financial_answer=answer,
            parsed=True,
            token_usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            latency_ms=_LATENCY_MS.get(profile, 5.0),
            estimated_cost_usd=0.0,
            raw={"profile": profile},
        )
