"""A generic OpenAI-compatible chat provider.

One implementation covers most of the serving landscape, because everything speaks this dialect:
Ollama (`:11434/v1`), vLLM (`:8000/v1`), llama.cpp's server (`:8080/v1`), LM Studio, Together,
Fireworks, and OpenAI itself. Rather than write five near-identical providers, this is the base and
the others configure it (see ``models/ollama.py``, ``configs/models/*.example.yaml``).

What it must get right, because the run engine depends on it:

- **Error classification.** The engine's retry loop asks one question of a failure: *is retrying
  worth it?* A 429 or a 503 is worth retrying; a 401 never is. Getting this wrong either burns the
  budget re-sending doomed requests, or gives up on a transient blip and records a false failure.
- **Never inventing usage or cost.** If a server doesn't report token counts, they stay ``None``.
  A fabricated token count would flow straight into the cost report.
- **Secret hygiene.** The API key is read from the environment, never logged, and never written
  into a request record or a run artifact.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from typing import Any, ClassVar

import httpx

from financebench.models.base import ModelProvider, ProviderCapabilities, register_provider
from financebench.models.pricing import estimate_cost
from financebench.schemas.model_io import FinancialAnswer, ModelRequest, ModelResponse, TokenUsage
from financebench.utils.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)

__all__ = ["OpenAICompatibleProvider"]


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@register_provider("openai_compatible")
class OpenAICompatibleProvider(ModelProvider):
    """Chat completions over the OpenAI ``/v1/chat/completions`` contract."""

    provider = "openai_compatible"

    API_KEY_ENV: ClassVar[str] = "FINANCEBENCH_OPENAI_COMPATIBLE_API_KEY"
    BASE_URL_ENV: ClassVar[str] = "FINANCEBENCH_OPENAI_COMPATIBLE_BASE_URL"
    DEFAULT_BASE_URL: ClassVar[str] = "http://localhost:8000/v1"
    #: Local servers generally need no key. Cloud subclasses flip this to True.
    REQUIRES_KEY: ClassVar[bool] = False
    #: Local inference is free. Cloud subclasses look themselves up in configs/pricing/.
    IS_LOCAL: ClassVar[bool] = True

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
    def from_env(cls, env: Mapping[str, str] | None = None) -> OpenAICompatibleProvider:
        source = env if env is not None else os.environ
        api_key = source.get(cls.API_KEY_ENV)
        if cls.REQUIRES_KEY and not api_key:
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
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def base_url_id(self) -> str:
        """A secret-free identifier for the endpoint, safe to record in a run artifact."""
        parts = httpx.URL(self._base_url)
        return f"{parts.scheme}://{parts.host}:{parts.port or ''}{parts.path}".rstrip(":/")

    # -- capabilities -------------------------------------------------------

    def capabilities(self, model: str) -> ProviderCapabilities:
        """Conservative by default.

        A generic OpenAI-compatible server may or may not honour ``response_format`` or tools;
        claiming otherwise would put a fabricated capability into ``model_manifest.json``. The
        specific subclasses (Ollama, OpenAI, …) override this with what they actually know.
        """
        return ProviderCapabilities(text=True, reports_usage=True)

    # -- payload ------------------------------------------------------------

    def _payload(self, request: ModelRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model.model,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in request.messages
            ],
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        # Only ask for JSON mode if the server actually supports it; a server that rejects the
        # field would fail every request, and the prompt already asks for JSON anyway.
        if (
            request.response_format == "json_object"
            and self.capabilities(request.model.model).json_mode
        ):
            payload["response_format"] = {"type": "json_object"}
        payload.update(request.model.params)
        return payload

    # -- generate -----------------------------------------------------------

    async def generate(self, request: ModelRequest) -> ModelResponse:
        url = f"{self._base_url}/chat/completions"
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
            # Connection refused, DNS failure, reset — all worth one more try; a local server that
            # is still loading a model looks exactly like this.
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
        """Map HTTP status onto the engine's one question: is a retry worth it?"""
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
        if response.status_code >= 500:
            raise ProviderResponseError(
                f"{self.provider} server error {response.status_code}: {detail}",
                provider=self.provider,
                retryable=True,
                retry_after=_retry_after(response),
            )
        # 4xx other than 429: a malformed request will be malformed next time too.
        raise ProviderResponseError(
            f"{self.provider} request rejected ({response.status_code}): {detail}",
            provider=self.provider,
            retryable=False,
        )

    def _to_model_response(
        self, request: ModelRequest, body: Mapping[str, Any], latency_ms: float
    ) -> ModelResponse:
        choices = body.get("choices") or []
        if not choices:
            raise ProviderResponseError(
                f"{self.provider} returned no choices",
                provider=self.provider,
                retryable=True,
            )
        content = (choices[0].get("message") or {}).get("content") or ""

        raw_usage = body.get("usage") or {}
        # Absent counts stay None. A fabricated token count flows straight into the cost report.
        usage = TokenUsage(
            prompt_tokens=raw_usage.get("prompt_tokens"),
            completion_tokens=raw_usage.get("completion_tokens"),
            total_tokens=raw_usage.get("total_tokens"),
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
            estimated_cost_usd=(0.0 if self.IS_LOCAL else estimate_cost(request.model.ref, usage)),
            raw={"id": body.get("id"), "finish_reason": choices[0].get("finish_reason")},
        )

    # -- health -------------------------------------------------------------

    async def health(self) -> tuple[bool, str]:
        """Can we reach this endpoint, and what does it serve? Used by ``doctor``/``validate-model``."""
        try:
            response = await self.client.get(
                f"{self._base_url}/models", headers=self._headers(), timeout=httpx.Timeout(10.0)
            )
        except httpx.HTTPError as exc:
            return False, f"unreachable at {self.base_url_id()}: {exc}"
        if not response.is_success:
            return False, f"{self.base_url_id()} returned {response.status_code}"
        try:
            models = [entry["id"] for entry in response.json().get("data", [])]
        except (ValueError, KeyError, TypeError):
            return True, f"reachable at {self.base_url_id()} (model list unparseable)"
        return True, f"reachable at {self.base_url_id()}; models: {', '.join(models) or 'none'}"
