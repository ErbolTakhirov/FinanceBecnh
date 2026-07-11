"""Provider unit tests against a mocked HTTP transport — no network, no keys.

The thing most worth pinning down here is **error classification**. The run engine asks a failure
exactly one question: *is retrying worth it?* Get that wrong and you either burn the budget
re-sending doomed requests (a 401 will still be a 401), or you give up on a transient blip and
record a false failure that pollutes the results.
"""

from __future__ import annotations

import httpx
import pytest

from financebench.models.ollama import OllamaProvider
from financebench.models.openai_compatible import OpenAICompatibleProvider
from financebench.schemas.model_io import ChatMessage, ModelRequest, ModelSpec, Role
from financebench.utils.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)


def _request(model: str = "openai_compatible/some-model") -> ModelRequest:
    return ModelRequest(
        model=ModelSpec.parse(model),
        messages=(ChatMessage(role=Role.USER, content="What was FY23 revenue?"),),
        prompt_version="structured_financial_v1",
        benchmark="finqa",
        benchmark_version="1",
        sample_id="finqa:test:1",
    )


def _provider(handler, cls=OpenAICompatibleProvider) -> OpenAICompatibleProvider:
    return cls(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


_OK_BODY = {
    "id": "chatcmpl-1",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": '{"answer": "42", "numeric_value": 42}'},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
}


async def test_a_successful_call_is_parsed_into_a_model_response() -> None:
    provider = _provider(lambda _: httpx.Response(200, json=_OK_BODY))
    response = await provider.generate(_request())

    assert response.parsed is True
    assert response.financial_answer is not None
    assert response.financial_answer.numeric_value == 42
    assert response.token_usage is not None
    assert response.token_usage.total_tokens == 120
    assert response.latency_ms is not None


async def test_missing_usage_stays_none_rather_than_being_invented() -> None:
    """A fabricated token count would flow straight into the cost report."""
    body = {**_OK_BODY}
    body.pop("usage")
    provider = _provider(lambda _: httpx.Response(200, json=body))
    response = await provider.generate(_request())

    assert response.token_usage is not None
    assert response.token_usage.total_tokens is None
    assert response.token_usage.prompt_tokens is None


# --------------------------------------------------------------------------- error classification


async def test_401_is_not_retryable() -> None:
    """Retrying a rejected credential just wastes the budget — it will be rejected again."""
    provider = _provider(lambda _: httpx.Response(401, text="bad key"))
    with pytest.raises(ProviderAuthError) as excinfo:
        await provider.generate(_request())
    assert excinfo.value.retryable is False


async def test_429_is_retryable_and_carries_retry_after() -> None:
    provider = _provider(
        lambda _: httpx.Response(429, text="slow down", headers={"retry-after": "7"})
    )
    with pytest.raises(ProviderRateLimitError) as excinfo:
        await provider.generate(_request())
    assert excinfo.value.retryable is True
    assert excinfo.value.retry_after == 7.0


async def test_500_is_retryable() -> None:
    provider = _provider(lambda _: httpx.Response(503, text="overloaded"))
    with pytest.raises(ProviderResponseError) as excinfo:
        await provider.generate(_request())
    assert excinfo.value.retryable is True


async def test_400_is_not_retryable() -> None:
    """A malformed request will be just as malformed next time."""
    provider = _provider(lambda _: httpx.Response(400, text="bad request"))
    with pytest.raises(ProviderResponseError) as excinfo:
        await provider.generate(_request())
    assert excinfo.value.retryable is False


async def test_a_timeout_is_retryable() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow")

    provider = _provider(handler)
    with pytest.raises(ProviderTimeoutError) as excinfo:
        await provider.generate(_request())
    assert excinfo.value.retryable is True


async def test_a_connection_error_is_retryable() -> None:
    """A local server still loading a model looks exactly like this."""

    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(handler)
    with pytest.raises(ProviderResponseError) as excinfo:
        await provider.generate(_request())
    assert excinfo.value.retryable is True


async def test_an_empty_choices_list_is_retryable_not_a_silent_empty_answer() -> None:
    provider = _provider(lambda _: httpx.Response(200, json={"choices": []}))
    with pytest.raises(ProviderResponseError):
        await provider.generate(_request())


# --------------------------------------------------------------------------- secrets


async def test_the_api_key_is_sent_as_a_bearer_header_and_never_in_the_url() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=_OK_BODY)

    provider = OpenAICompatibleProvider(
        base_url="https://example.test/v1",
        api_key="sk-secret-value",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    await provider.generate(_request())

    (request,) = seen
    assert request.headers["authorization"] == "Bearer sk-secret-value"
    assert "sk-secret-value" not in str(request.url)


def test_base_url_id_strips_any_credentials_before_it_is_recorded() -> None:
    provider = OpenAICompatibleProvider(base_url="https://user:pass@example.test/v1")
    identifier = provider.base_url_id()
    assert "pass" not in identifier
    assert "user" not in identifier


# --------------------------------------------------------------------------- ollama specifics


def test_ollama_defaults_to_the_local_endpoint_and_needs_no_key() -> None:
    assert OllamaProvider.DEFAULT_BASE_URL == "http://localhost:11434/v1"
    assert OllamaProvider.REQUIRES_KEY is False
    assert OllamaProvider.IS_LOCAL is True


def test_ollama_reports_a_context_window_only_for_families_it_actually_knows() -> None:
    """A wrong max_context_tokens is worse than an absent one — it is used to warn about
    truncation."""
    provider = OllamaProvider()
    assert provider.capabilities("qwen2.5:7b").max_context_tokens == 32_768
    assert provider.capabilities("some-model-nobody-has-heard-of").max_context_tokens is None


async def test_ollama_rejects_an_embedding_model_as_the_model_under_test() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "nomic-embed-text:latest"}]})

    provider = OllamaProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    ok, detail = await provider.check_model("nomic-embed-text")

    assert ok is False
    assert "embedding model" in detail


async def test_ollama_names_the_missing_model_instead_of_failing_opaquely() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "qwen2.5:3b"}]})

    provider = OllamaProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    ok, detail = await provider.check_model("llama3.3:70b")

    assert ok is False
    assert "ollama pull llama3.3:70b" in detail
    assert "qwen2.5:3b" in detail  # tells you what you *do* have


async def test_ollama_local_inference_is_costed_at_zero_not_none() -> None:
    """Local inference really is free — 0.0 is the truth here, and a None would make the cost
    report look broken. (A *cloud* model with no published price gets None, not 0.0.)"""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_OK_BODY)

    provider = OllamaProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    response = await provider.generate(_request("ollama/qwen2.5:7b"))
    assert response.estimated_cost_usd == 0.0
