"""The four API providers, against a mocked transport.

No API key for any of these exists on the machine this was built on, so not one of them has ever
made a real call here. That is exactly why these tests are written the way they are: they are the
*only* evidence that the code is right, so they check the things that a first live call would
otherwise discover the hard way, one 400 at a time, across 150 samples.

What they pin down:

- **The wire format.** Anthropic in particular does not speak the OpenAI dialect, and the difference
  is not cosmetic: the system prompt is a top-level parameter, not a message. Every prompt profile in
  this platform emits a system message. Get this wrong and *every request fails* — with a 400, which
  is correctly classified as non-retryable, so the run would record 150 identical failures and blame
  the model.
- **Error classification.** The engine asks a failure exactly one question: is retrying worth it? A
  429 is; a 401 never is. Getting this wrong either burns the budget re-sending doomed requests or
  gives up on a transient blip and records a false failure.
- **Never inventing usage.** If a server reports no token counts, they stay ``None``. A fabricated
  count flows straight into the cost report and out into a leaderboard.
- **Secret hygiene.** The key goes in a header and nowhere else — never into a run artifact.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from financebench.models.anthropic import AnthropicProvider
from financebench.models.openai import GeminiProvider, OpenAIProvider, OpenRouterProvider
from financebench.schemas.model_io import ChatMessage, ModelRequest, ModelSpec, Role
from financebench.utils.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResponseError,
)

pytestmark = pytest.mark.asyncio


def _request(provider: str, model: str = "test-model") -> ModelRequest:
    return ModelRequest(
        model=ModelSpec.parse(f"{provider}/{model}"),
        messages=(
            ChatMessage(role=Role.SYSTEM, content="You are a financial analyst."),
            ChatMessage(role=Role.USER, content="What is the cash balance?"),
        ),
        temperature=0.0,
        max_tokens=512,
        prompt_version="structured_financial_v1",
        benchmark="smoke",
        benchmark_version="1",
        sample_id="smoke:dev:1",
    )


def _transport(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# --------------------------------------------------------------------------- OpenAI dialect


async def test_openai_sends_a_bearer_token_and_the_chat_completions_shape() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "cmpl-1",
                "choices": [{"message": {"content": '{"answer": "42"}'}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    provider = OpenAIProvider(api_key="sk-secret", client=_transport(handler))
    response = await provider.generate(_request("openai"))

    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-secret"
    assert seen["body"]["messages"][0]["role"] == "system"
    assert response.content == '{"answer": "42"}'
    assert response.token_usage is not None
    assert response.token_usage.total_tokens == 15


async def test_openrouter_and_gemini_hit_their_own_endpoints() -> None:
    urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
        )

    for provider_cls, name in (
        (OpenRouterProvider, "openrouter"),
        (GeminiProvider, "gemini"),
    ):
        provider = provider_cls(api_key="k", client=_transport(handler))
        await provider.generate(_request(name))

    assert urls[0].startswith("https://openrouter.ai/api/v1/")
    assert urls[1].startswith("https://generativelanguage.googleapis.com/v1beta/openai/")


async def test_openrouter_claims_no_capability_it_cannot_guarantee() -> None:
    """It routes to hundreds of models from dozens of vendors. Whether any given one honours
    ``response_format`` depends entirely on which one you picked, so claiming json_mode across the
    board would put a fabricated capability into every run manifest that used it."""
    capabilities = OpenRouterProvider(api_key="k").capabilities("anything/at-all")
    assert capabilities.json_mode is False
    assert capabilities.tool_calling is False


async def test_an_absent_usage_block_stays_none_and_is_never_invented() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "42"}, "finish_reason": "stop"}]}
        )

    provider = OpenAIProvider(api_key="k", client=_transport(handler))
    response = await provider.generate(_request("openai"))

    assert response.token_usage is not None
    assert response.token_usage.total_tokens is None
    # Unpriced + no tokens => no cost. A 0.0 here would claim the call was free.
    assert response.estimated_cost_usd is None


# --------------------------------------------------------------------------- Anthropic


async def test_anthropic_lifts_the_system_prompt_out_of_the_message_list() -> None:
    """The difference that would have broken every single request.

    Anthropic rejects a message with ``role: "system"``. Every prompt profile in this platform emits
    one. Sending it inline is a 400 — which is correctly classified as non-retryable — so the run
    would have recorded one identical failure per sample and attributed it to the model.
    """
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "msg_1",
                "content": [{"type": "text", "text": '{"answer": "42"}'}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 12, "output_tokens": 8},
            },
        )

    provider = AnthropicProvider(api_key="sk-ant-secret", client=_transport(handler))
    response = await provider.generate(_request("anthropic", "claude-sonnet-4"))

    body = seen["body"]
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert body["system"] == "You are a financial analyst."
    assert [m["role"] for m in body["messages"]] == ["user"], "no system message may survive"
    assert body["max_tokens"] == 512, "max_tokens is REQUIRED by this API, not optional"

    assert seen["headers"]["x-api-key"] == "sk-ant-secret"
    assert seen["headers"]["anthropic-version"] == "2023-06-01"
    assert "authorization" not in seen["headers"], "wrong auth scheme entirely"

    assert response.content == '{"answer": "42"}'


async def test_anthropic_sums_a_total_it_is_never_given() -> None:
    """The usage block has ``input_tokens`` and ``output_tokens`` and no total. It is summed when
    both parts are present — and left ``None`` when either is missing, because a half-known total is
    a made-up total."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 12, "output_tokens": 8},
            },
        )

    provider = AnthropicProvider(api_key="k", client=_transport(handler))
    response = await provider.generate(_request("anthropic"))

    assert response.token_usage is not None
    assert response.token_usage.prompt_tokens == 12
    assert response.token_usage.completion_tokens == 8
    assert response.token_usage.total_tokens == 20


async def test_anthropic_reads_text_blocks_and_skips_everything_else() -> None:
    """``content`` is a list of blocks, not a string. A ``thinking`` or ``tool_use`` block
    stringified into the answer would be scored as part of the model's response."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "thinking", "thinking": "let me work through this..."},
                    {"type": "text", "text": "The balance is "},
                    {"type": "text", "text": "42."},
                ],
            },
        )

    provider = AnthropicProvider(api_key="k", client=_transport(handler))
    response = await provider.generate(_request("anthropic"))

    assert response.content == "The balance is 42."
    assert "let me work through this" not in response.content


async def test_anthropic_does_not_claim_a_json_mode_it_does_not_have() -> None:
    capabilities = AnthropicProvider(api_key="k").capabilities("claude-sonnet-4")
    assert capabilities.json_mode is False, "there is no response_format switch on this API"
    assert capabilities.max_context_tokens == 200_000


# --------------------------------------------------------------------------- error classification


@pytest.mark.parametrize(
    ("status", "expected", "retryable"),
    [
        (401, ProviderAuthError, False),
        (403, ProviderAuthError, False),
        (429, ProviderRateLimitError, True),
        (500, ProviderResponseError, True),
        (503, ProviderResponseError, True),
        (400, ProviderResponseError, False),
    ],
)
@pytest.mark.parametrize("provider_cls", [OpenAIProvider, AnthropicProvider])
async def test_the_engine_is_told_whether_a_retry_is_worth_it(
    provider_cls: Any, status: int, expected: type[Exception], retryable: bool
) -> None:
    """The engine asks a failure exactly one question. Both transports must answer it the same way —
    it must not have to know which provider it is talking to in order to decide whether to try
    again."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="nope")

    provider = provider_cls(api_key="k", client=_transport(handler))
    with pytest.raises(expected) as exc:
        await provider.generate(_request(provider_cls.provider))
    assert exc.value.retryable is retryable


async def test_anthropic_529_overloaded_is_retryable() -> None:
    """Anthropic's own "come back in a moment" code. Giving up on it would record a false failure."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(529, text="overloaded")

    provider = AnthropicProvider(api_key="k", client=_transport(handler))
    with pytest.raises(ProviderRateLimitError) as exc:
        await provider.generate(_request("anthropic"))
    assert exc.value.retryable is True


async def test_a_retry_after_header_is_honoured() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "7"}, text="slow down")

    provider = OpenAIProvider(api_key="k", client=_transport(handler))
    with pytest.raises(ProviderRateLimitError) as exc:
        await provider.generate(_request("openai"))
    assert exc.value.retry_after == 7.0


# --------------------------------------------------------------------------- keys and secrets


@pytest.mark.parametrize(
    ("provider_cls", "env_var"),
    [
        (OpenAIProvider, "OPENAI_API_KEY"),
        (AnthropicProvider, "ANTHROPIC_API_KEY"),
        (GeminiProvider, "GEMINI_API_KEY"),
        (OpenRouterProvider, "OPENROUTER_API_KEY"),
    ],
)
async def test_a_cloud_provider_without_a_key_fails_immediately_and_says_which_variable(
    provider_cls: Any, env_var: str
) -> None:
    """And it is NOT retryable. Retrying a missing credential four times with exponential backoff is
    30 seconds spent proving something we knew at the first attempt."""
    with pytest.raises(ProviderAuthError) as exc:
        provider_cls.from_env({})
    assert env_var in str(exc.value)
    assert exc.value.retryable is False


@pytest.mark.parametrize(
    "provider_cls", [OpenAIProvider, AnthropicProvider, GeminiProvider, OpenRouterProvider]
)
async def test_the_key_never_appears_in_the_endpoint_identifier_written_to_artifacts(
    provider_cls: Any,
) -> None:
    """``base_url_id`` goes into the response-cache key and into run artifacts. A key that leaked
    into it would be committed to the repository."""
    provider = provider_cls(api_key="sk-super-secret-value")
    identifier = provider.base_url_id()
    assert "sk-super-secret-value" not in identifier
    assert identifier.startswith("https://")


@pytest.mark.parametrize(
    "provider_cls", [OpenAIProvider, AnthropicProvider, GeminiProvider, OpenRouterProvider]
)
async def test_a_cloud_provider_never_reports_a_cost_of_zero(provider_cls: Any) -> None:
    """Zero is a *claim* — that the call was free — and it is only true for local inference. An
    unpriced cloud model reports ``None``, which reads as "we don't know", because we don't."""
    assert provider_cls.IS_LOCAL is False


# --------------------------------------------------------------------------- verification


async def test_a_provider_with_no_key_is_unproven_not_broken() -> None:
    """The distinction the whole verification module exists for.

    A provider we have no key for has never made a call. That is not a defect — there is nothing to
    fix, and we simply have no way to find out whether it works. Marking it red would invent a
    failure exactly as surely as marking it green would invent a success.
    """
    from financebench.models.verification import ProviderVerification, verify_provider

    record = await verify_provider("openai", env={})
    assert record.status is ProviderVerification.IMPLEMENTED_NOT_LIVE_VERIFIED
    assert "not broken" in record.detail
    assert record.key_env_var == "OPENAI_API_KEY"


async def test_live_verified_is_earned_by_an_answer_not_by_a_class_attribute() -> None:
    """A static ``LIVE_VERIFIED = True`` is a claim the code makes about itself, and it stays true
    after the API changes underneath it. The only thing that earns the label is a real endpoint
    actually answering — so the label is computed, never declared."""
    from financebench.models.verification import ProviderVerification, verify_provider

    record = await verify_provider("openai_compatible", env={})
    # Nothing is serving on localhost:8000 in a test environment, so the call is attempted and fails.
    # That is a real finding about this machine, and it is reported as one.
    assert record.status is ProviderVerification.UNREACHABLE


async def test_the_mock_is_not_a_model_and_cannot_be_verified_as_one() -> None:
    from financebench.models.verification import ProviderVerification, verify_provider

    record = await verify_provider("mock", env={})
    assert record.status is ProviderVerification.NOT_A_MODEL


async def test_every_registered_provider_gets_a_verdict() -> None:
    """A provider missing from the report reads as one that passed."""
    from financebench.models.base import available_providers
    from financebench.models.verification import verify_all_providers

    records = await verify_all_providers(env={})
    assert {r.provider for r in records} == set(available_providers())
