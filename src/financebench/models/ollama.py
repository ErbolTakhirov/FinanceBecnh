"""Ollama, via its OpenAI-compatible endpoint.

Ollama serves an OpenAI-shaped API at ``/v1``, so this is mostly configuration on top of
:class:`OpenAICompatibleProvider`. What it adds is worth having:

- a **native health check** against ``/api/tags``, which lists the models actually pulled onto this
  machine — so ``doctor`` can say "you asked for qwen2.5:72b, you have qwen2.5:7b" instead of
  letting the run fail one request at a time;
- a **capability table** for the model families commonly run locally, rather than a guess;
- ``IS_LOCAL = True``, so cost is a truthful ``0.0`` rather than a ``None`` that would make the
  cost report look broken.

Verified against a live Ollama (its ``/v1`` accepts ``response_format: {"type": "json_object"}``,
``seed`` and ``temperature``, and reports real token usage).

vLLM and llama.cpp's server also speak this dialect — point ``openai_compatible`` at them; see
``configs/models/vllm.example.yaml`` and ``configs/models/llamacpp.example.yaml``.
"""

from __future__ import annotations

from typing import ClassVar

import httpx

from financebench.models.base import ProviderCapabilities, register_provider
from financebench.models.openai_compatible import OpenAICompatibleProvider

__all__ = ["OllamaProvider"]

#: Context windows for locally-common families. A model that isn't listed reports ``None`` rather
#: than a made-up number — ``max_context_tokens`` is used to warn about truncation, and a wrong
#: value is worse than an absent one.
_CONTEXT_TOKENS: dict[str, int] = {
    "qwen2.5": 32_768,
    "qwen3": 32_768,
    "llama3.1": 131_072,
    "llama3.2": 131_072,
    "mistral": 32_768,
    "gemma2": 8_192,
    "phi3": 131_072,
    "deepseek-r1": 65_536,
}

#: Embedding-only models. Asking one of these to chat produces confusing failures, so name them.
_EMBEDDING_MODELS = ("nomic-embed-text", "mxbai-embed", "all-minilm", "bge-")


def _family(model: str) -> str:
    return model.split(":", 1)[0]


@register_provider("ollama")
class OllamaProvider(OpenAICompatibleProvider):
    """Local models served by Ollama."""

    provider = "ollama"

    API_KEY_ENV: ClassVar[str] = "OLLAMA_API_KEY"  # unused locally; some proxies want one
    BASE_URL_ENV: ClassVar[str] = "OLLAMA_BASE_URL"
    DEFAULT_BASE_URL: ClassVar[str] = "http://localhost:11434/v1"
    REQUIRES_KEY: ClassVar[bool] = False
    IS_LOCAL: ClassVar[bool] = True

    def capabilities(self, model: str) -> ProviderCapabilities:
        return ProviderCapabilities(
            text=True,
            vision=False,
            tool_calling=False,  # supported by Ollama for some models; not relied on here
            json_mode=True,  # verified live against /v1/chat/completions
            max_context_tokens=_CONTEXT_TOKENS.get(_family(model)),
            streaming=True,
            reports_usage=True,
        )

    def _api_root(self) -> str:
        """Ollama's *native* API root, i.e. the base URL minus the trailing ``/v1``."""
        return self._base_url.removesuffix("/v1")

    async def list_models(self) -> list[str]:
        """Models actually pulled onto this machine, via Ollama's native ``/api/tags``."""
        response = await self.client.get(
            f"{self._api_root()}/api/tags", timeout=httpx.Timeout(10.0)
        )
        response.raise_for_status()
        return [entry["name"] for entry in response.json().get("models", [])]

    async def health(self) -> tuple[bool, str]:
        """Reachable, and is the requested model actually here?

        A missing model is the single most common local failure, and the OpenAI-compatible error
        for it is opaque. Naming it up front turns a confusing run-time failure into a one-line fix.
        """
        try:
            models = await self.list_models()
        except httpx.HTTPError as exc:
            return False, (
                f"Ollama unreachable at {self._api_root()}: {exc}. Is it running? Try: ollama serve"
            )
        if not models:
            return False, "Ollama is running but has no models pulled. Try: ollama pull qwen2.5:7b"

        chat_models = [m for m in models if not m.startswith(_EMBEDDING_MODELS)]
        return True, f"Ollama at {self._api_root()}; chat models: {', '.join(chat_models)}"

    async def check_model(self, model: str) -> tuple[bool, str]:
        """Is ``model`` pulled, and is it a chat model rather than an embedding model?"""
        try:
            models = await self.list_models()
        except httpx.HTTPError as exc:
            return False, f"Ollama unreachable: {exc}"

        if model.startswith(_EMBEDDING_MODELS):
            return False, (
                f"{model!r} is an embedding model — it cannot answer chat prompts. "
                "It is usable as a retriever (retrieval_required mode), not as the model under test."
            )
        if model not in models:
            # Ollama resolves a bare name to its ':latest' tag.
            if f"{model}:latest" in models:
                return True, f"{model} is available (as {model}:latest)"
            return False, (
                f"{model!r} is not pulled on this machine. Available: {', '.join(models)}. "
                f"Try: ollama pull {model}"
            )
        return True, f"{model} is available"
