"""Anthropic — the one cloud provider that does not speak the OpenAI dialect.

OpenAI, OpenRouter and Gemini all take ``POST /v1/chat/completions`` with a bearer token and a flat
list of messages. Anthropic does not, and the differences are not cosmetic:

- ``POST /v1/messages``, not ``/v1/chat/completions``.
- ``x-api-key`` and ``anthropic-version`` headers, not ``Authorization: Bearer``.
- The **system prompt is a top-level parameter**, not a message with ``role: "system"``. Sending it
  as a message is rejected outright — and this platform's prompt profiles always emit a system
  message, so every request would fail.
- ``max_tokens`` is **required**, not optional. Omitting it is a 400 on every call.
- The response body is ``content: [{type, text}, …]``, not ``choices[0].message.content``.
- Usage is ``input_tokens`` / ``output_tokens``, and there is no ``total_tokens`` — it has to be
  summed, not read.

Subclassing the OpenAI transport and overriding six things would leave a class whose inherited
behaviour is wrong in every particular. It is a genuinely different API, so it gets a genuinely
different provider — while keeping the two things the engine actually depends on identical: error
classification (is a retry worth it?) and never inventing a token count.

**Not live-verified.** No Anthropic key exists on the machine this was built on, so this has never
made a successful call here. It is implemented and unit-tested against a mocked transport, and it is
labelled ``implemented_not_live_verified`` until a real call earns it otherwise. See
``models/verification.py``.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from typing import Any, ClassVar

import httpx

from financebench.models.base import ModelProvider, ProviderCapabilities, register_provider
from financebench.models.pricing import estimate_cost
from financebench.schemas.model_io import (
    FinancialAnswer,
    ModelRequest,
    ModelResponse,
    Role,
    TokenUsage,
)
from financebench.utils.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)

__all__ = ["AnthropicProvider"]

#: Pinned so a wrong number never reaches a run manifest. Unlisted models report ``None``.
_CONTEXT_TOKENS: dict[str, int] = {
    "claude-opus-4": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-haiku-4": 200_000,
    "claude-3-7-sonnet": 200_000,
    "claude-3-5-haiku": 200_000,
}

#: Anthropic requires max_tokens on every request. If a RunConfig somehow arrives without one, this
#: is used rather than letting the call 400 — but RunConfig always sets it, so this is a backstop.
_DEFAULT_MAX_TOKENS = 1024


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@register_provider("anthropic")
class AnthropicProvider(ModelProvider):
    """Anthropic's Messages API."""

    provider = "anthropic"

    API_KEY_ENV: ClassVar[str] = "ANTHROPIC_API_KEY"
    BASE_URL_ENV: ClassVar[str] = "FINANCEBENCH_ANTHROPIC_BASE_URL"
    DEFAULT_BASE_URL: ClassVar[str] = "https://api.anthropic.com/v1"
    API_VERSION: ClassVar[str] = "2023-06-01"
    REQUIRES_KEY: ClassVar[bool] = True
    IS_LOCAL: ClassVar[bool] = False

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._api_key = api_key
        self._client = client
        self._owns_client = client is None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AnthropicProvider:
        source = env if env is not None else os.environ
        api_key = source.get(cls.API_KEY_ENV)
        if not api_key:
            raise ProviderAuthError(
                f"{cls.provider} requires an API key; set {cls.API_KEY_ENV}",
                provider=cls.provider,
                retryable=False,
            )
        return cls(base_url=source.get(cls.BASE_URL_ENV) or cls.DEFAULT_BASE_URL, api_key=api_key)

    # -- transport ----------------------------------------------------------

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": self.API_VERSION,
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def base_url_id(self) -> str:
        """A secret-free identifier for the endpoint, safe to record in a run artifact."""
        parts = httpx.URL(self._base_url)
        return f"{parts.scheme}://{parts.host}{parts.path}".rstrip("/")

    def capabilities(self, model: str) -> ProviderCapabilities:
        context = next(
            (tokens for name, tokens in _CONTEXT_TOKENS.items() if model.startswith(name)), None
        )
        return ProviderCapabilities(
            text=True,
            vision=True,
            tool_calling=True,
            # Anthropic has no `response_format: json_object` switch. JSON is elicited by the prompt
            # — which is what the prompt profiles do anyway — so claiming a JSON mode it does not
            # have would put a fabricated capability into the run manifest.
            json_mode=False,
            max_context_tokens=context,
            reports_usage=True,
        )

    # -- payload ------------------------------------------------------------

    def _payload(self, request: ModelRequest) -> dict[str, Any]:
        """Split the system prompt out of the message list.

        This platform's prompt profiles always emit a system message. Anthropic rejects one, so
        without this every single request would fail — and it would fail with a 400, which is
        correctly classified as *not retryable*, so the run would record 150 identical
        non-retryable failures and blame the model.
        """
        system = "\n\n".join(
            message.content for message in request.messages if message.role is Role.SYSTEM
        )
        turns = [
            {"role": message.role.value, "content": message.content}
            for message in request.messages
            if message.role is not Role.SYSTEM
        ]

        payload: dict[str, Any] = {
            "model": request.model.model,
            "messages": turns,
            # Required by the API, unlike OpenAI's, where it is optional.
            "max_tokens": request.max_tokens or _DEFAULT_MAX_TOKENS,
            "temperature": request.temperature,
        }
        if system:
            payload["system"] = system
        payload.update(request.model.params)
        return payload

    # -- generate -----------------------------------------------------------

    async def generate(self, request: ModelRequest) -> ModelResponse:
        url = f"{self._base_url}/messages"
        start = time.perf_counter()
        try:
            response = await self.client.post(
                url,
                json=self._payload(request),
                headers=self._headers(),
                timeout=httpx.Timeout(request.timeout_s),
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"{self.provider} request timed out after {request.timeout_s}s",
                provider=self.provider,
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderResponseError(
                f"{self.provider} transport error: {exc}",
                provider=self.provider,
                retryable=True,
            ) from exc

        latency_ms = (time.perf_counter() - start) * 1000.0
        self._raise_for_status(response)

        try:
            body = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                f"{self.provider} returned non-JSON: {response.text[:200]!r}",
                provider=self.provider,
                retryable=False,
            ) from exc

        return self._to_model_response(request, body, latency_ms)

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Map HTTP status onto the engine's one question: is a retry worth it?

        Identical in spirit to the OpenAI transport's, and deliberately so — the engine must not
        have to know which provider it is talking to in order to decide whether to try again.
        Anthropic adds ``529 overloaded``, which is emphatically retryable and would otherwise fall
        into the >=500 bucket anyway; it is named here so the log says what actually happened.
        """
        if response.is_success:
            return

        detail = response.text[:300]
        if response.status_code in (401, 403):
            raise ProviderAuthError(
                f"{self.provider} rejected the credentials ({response.status_code})",
                provider=self.provider,
                retryable=False,
            )
        if response.status_code == 429:
            raise ProviderRateLimitError(
                f"{self.provider} rate limited",
                provider=self.provider,
                retryable=True,
                retry_after=_retry_after(response),
            )
        if response.status_code == 529:
            raise ProviderRateLimitError(
                f"{self.provider} overloaded (529)",
                provider=self.provider,
                retryable=True,
                retry_after=_retry_after(response),
            )
        if response.status_code >= 500:
            raise ProviderResponseError(
                f"{self.provider} server error {response.status_code}: {detail}",
                provider=self.provider,
                retryable=True,
                retry_after=_retry_after(response),
            )
        raise ProviderResponseError(
            f"{self.provider} request rejected ({response.status_code}): {detail}",
            provider=self.provider,
            retryable=False,
        )

    def _to_model_response(
        self, request: ModelRequest, body: Mapping[str, Any], latency_ms: float
    ) -> ModelResponse:
        # content is a list of blocks, not a single string. Text blocks are concatenated; any other
        # block type (tool_use, thinking) is skipped rather than stringified into the answer.
        blocks = body.get("content") or []
        content = "".join(
            str(block.get("text", ""))
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )

        raw_usage = body.get("usage") or {}
        prompt_tokens = raw_usage.get("input_tokens")
        completion_tokens = raw_usage.get("output_tokens")
        # There is no total_tokens in Anthropic's usage block. It is summed when both parts are
        # present, and left None when either is missing — a half-known total is a made-up total.
        total = (
            prompt_tokens + completion_tokens
            if prompt_tokens is not None and completion_tokens is not None
            else None
        )
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
        )

        answer = FinancialAnswer.from_text(content)
        return ModelResponse(
            provider=self.provider,
            model=request.model.model,
            content=content,
            financial_answer=answer,
            parsed=answer is not None,
            token_usage=usage,
            latency_ms=latency_ms,
            estimated_cost_usd=estimate_cost(request.model.ref, usage),
            raw={"id": body.get("id"), "stop_reason": body.get("stop_reason")},
        )

    # -- health -------------------------------------------------------------

    async def health(self) -> tuple[bool, str]:
        """Anthropic has no ``/models`` list on the public API, so reachability is checked with a
        one-token message. That is a *real call*, and it is the only honest way to say the endpoint
        works — but it costs a fraction of a cent, so it is only ever run on demand."""
        if not self._api_key:
            return False, f"no API key ({self.API_KEY_ENV} is unset)"
        try:
            response = await self.client.post(
                f"{self._base_url}/messages",
                headers=self._headers(),
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "ping"}],
                },
                timeout=httpx.Timeout(20.0),
            )
        except httpx.HTTPError as exc:
            return False, f"unreachable at {self.base_url_id()}: {exc}"
        if response.status_code in (401, 403):
            return False, "the API key was rejected"
        if not response.is_success:
            return False, f"{self.base_url_id()} returned {response.status_code}"
        return True, f"reachable at {self.base_url_id()}"
