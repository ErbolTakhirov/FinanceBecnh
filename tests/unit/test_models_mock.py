from __future__ import annotations

import pytest

from financebench.models.mock import MockProvider
from financebench.schemas.model_io import ChatMessage, ModelRequest, ModelSpec, Role
from financebench.utils.errors import ProviderResponseError, ProviderTimeoutError


def _request(profile: str, simulation_context: dict[str, object] | None = None) -> ModelRequest:
    return ModelRequest(
        model=ModelSpec.parse(f"mock/{profile}"),
        messages=(ChatMessage(role=Role.USER, content="What was the revenue increase?"),),
        prompt_version="v1",
        benchmark="smoke",
        benchmark_version="1",
        sample_id="smoke:dev:1",
        simulation_context=simulation_context,
    )


GOLD_CTX = {"gold_answer": "12.5%", "gold_numeric_value": 12.5, "unit": "percent"}


@pytest.mark.asyncio
async def test_echo_gold_returns_the_gold_answer_verbatim() -> None:
    response = await MockProvider().generate(_request("echo-gold", GOLD_CTX))
    assert response.parsed is True
    assert response.financial_answer is not None
    assert response.financial_answer.answer == "12.5%"
    assert response.financial_answer.numeric_value == 12.5


@pytest.mark.asyncio
async def test_formatting_noise_preserves_the_numeric_value_but_not_the_plain_string() -> None:
    response = await MockProvider().generate(_request("formatting-noise", GOLD_CTX))
    answer = response.financial_answer
    assert answer is not None
    assert answer.numeric_value == 12.5
    assert answer.answer != "12.5%"
    assert "%" in answer.answer


@pytest.mark.asyncio
async def test_always_wrong_never_matches_gold_numeric_value() -> None:
    response = await MockProvider().generate(_request("always-wrong", GOLD_CTX))
    answer = response.financial_answer
    assert answer is not None
    assert answer.numeric_value != 12.5


@pytest.mark.asyncio
async def test_refuse_sets_insufficient_information() -> None:
    response = await MockProvider().generate(_request("refuse", GOLD_CTX))
    answer = response.financial_answer
    assert answer is not None
    assert answer.insufficient_information is True


@pytest.mark.asyncio
async def test_error_profile_raises_non_retryable() -> None:
    with pytest.raises(ProviderResponseError) as excinfo:
        await MockProvider().generate(_request("error"))
    assert excinfo.value.retryable is False


@pytest.mark.asyncio
async def test_timeout_profile_raises_retryable() -> None:
    with pytest.raises(ProviderTimeoutError) as excinfo:
        await MockProvider().generate(_request("timeout"))
    assert excinfo.value.retryable is True


@pytest.mark.asyncio
async def test_unknown_profile_raises_non_retryable_response_error() -> None:
    with pytest.raises(ProviderResponseError) as excinfo:
        await MockProvider().generate(_request("not-a-real-profile"))
    assert excinfo.value.retryable is False


@pytest.mark.asyncio
async def test_echo_gold_without_simulation_context_defaults_gracefully() -> None:
    response = await MockProvider().generate(_request("echo-gold", None))
    assert response.financial_answer is not None
    assert response.financial_answer.answer == ""


@pytest.mark.asyncio
async def test_token_usage_and_latency_are_populated() -> None:
    response = await MockProvider().generate(_request("echo-gold", GOLD_CTX))
    assert response.token_usage is not None
    assert response.token_usage.total_tokens is not None
    assert response.token_usage.total_tokens > 0
    assert response.latency_ms == 5.0


def test_capabilities_reports_text_and_json_mode() -> None:
    caps = MockProvider().capabilities("echo-gold")
    assert caps.text is True
    assert caps.json_mode is True
    assert caps.vision is False
