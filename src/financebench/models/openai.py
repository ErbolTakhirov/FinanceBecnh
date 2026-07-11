"""OpenAI, OpenRouter and Gemini — three providers, one dialect.

All three speak the OpenAI ``/v1/chat/completions`` contract (Gemini via its
``/v1beta/openai/`` compatibility endpoint), so they are configuration on top of
:class:`OpenAICompatibleProvider` rather than three near-identical transports. What each adds is
what it actually knows: its base URL, its key, its capability table, and — for the cloud ones —
``IS_LOCAL = False``, so an unpriced model reports a cost of ``None`` rather than a ``0.00`` that
would claim the call was free.

**None of these is live-verified in this repository.** No API key for any of them exists on the
machine this was built on, so not one of them has ever made a successful call here. They are
implemented, unit-tested against a mocked transport, and labelled
``implemented_not_live_verified`` — which is a different statement from "working", and a different
statement again from "broken". See ``models/verification.py``: the label is earned by a real call,
not asserted in a docstring.
"""

from __future__ import annotations

from typing import ClassVar

from financebench.models.base import ProviderCapabilities, register_provider
from financebench.models.openai_compatible import OpenAICompatibleProvider

__all__ = ["GeminiProvider", "OpenAIProvider", "OpenRouterProvider"]


#: Context windows, pinned so a wrong number never reaches ``model_manifest.json``. A model that is
#: not listed reports ``None`` — ``max_context_tokens`` exists to warn about truncation, and a
#: fabricated value is worse than an absent one.
_OPENAI_CONTEXT: dict[str, int] = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4.1": 1_047_576,
    "gpt-4.1-mini": 1_047_576,
    "o3": 200_000,
    "o4-mini": 200_000,
}

_GEMINI_CONTEXT: dict[str, int] = {
    "gemini-2.5-pro": 1_048_576,
    "gemini-2.5-flash": 1_048_576,
    "gemini-2.0-flash": 1_048_576,
}


def _context_for(model: str, table: dict[str, int]) -> int | None:
    for name, tokens in table.items():
        if model.startswith(name):
            return tokens
    return None


@register_provider("openai")
class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI's own API."""

    provider = "openai"

    API_KEY_ENV: ClassVar[str] = "OPENAI_API_KEY"
    BASE_URL_ENV: ClassVar[str] = "FINANCEBENCH_OPENAI_BASE_URL"
    DEFAULT_BASE_URL: ClassVar[str] = "https://api.openai.com/v1"
    REQUIRES_KEY: ClassVar[bool] = True
    IS_LOCAL: ClassVar[bool] = False

    def capabilities(self, model: str) -> ProviderCapabilities:
        return ProviderCapabilities(
            text=True,
            vision=model.startswith(("gpt-4o", "gpt-4.1", "o3", "o4")),
            tool_calling=True,
            json_mode=True,
            max_context_tokens=_context_for(model, _OPENAI_CONTEXT),
            reports_usage=True,
        )


@register_provider("openrouter")
class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter — one key, many models, all behind the OpenAI dialect.

    Capabilities are deliberately **conservative**: OpenRouter routes to hundreds of models from
    dozens of vendors, and whether any given one honours ``response_format`` or tool calling depends
    entirely on which one you picked. Claiming ``json_mode=True`` across the board would put a
    fabricated capability into every run manifest that used it — and the prompt asks for JSON in
    words anyway, so the cost of not claiming it is nothing.
    """

    provider = "openrouter"

    API_KEY_ENV: ClassVar[str] = "OPENROUTER_API_KEY"
    BASE_URL_ENV: ClassVar[str] = "FINANCEBENCH_OPENROUTER_BASE_URL"
    DEFAULT_BASE_URL: ClassVar[str] = "https://openrouter.ai/api/v1"
    REQUIRES_KEY: ClassVar[bool] = True
    IS_LOCAL: ClassVar[bool] = False

    def capabilities(self, model: str) -> ProviderCapabilities:
        return ProviderCapabilities(text=True, reports_usage=True)


@register_provider("gemini")
class GeminiProvider(OpenAICompatibleProvider):
    """Google Gemini, through its OpenAI-compatibility endpoint.

    Google also publishes a native ``generativelanguage`` API with a different request shape. The
    compatibility endpoint is used here on purpose: it means Gemini shares the error classification,
    usage parsing and secret handling that the OpenAI-compatible transport already gets right, rather
    than acquiring a second, less-tested copy of all three.
    """

    provider = "gemini"

    API_KEY_ENV: ClassVar[str] = "GEMINI_API_KEY"
    BASE_URL_ENV: ClassVar[str] = "FINANCEBENCH_GEMINI_BASE_URL"
    DEFAULT_BASE_URL: ClassVar[str] = "https://generativelanguage.googleapis.com/v1beta/openai"
    REQUIRES_KEY: ClassVar[bool] = True
    IS_LOCAL: ClassVar[bool] = False

    def capabilities(self, model: str) -> ProviderCapabilities:
        return ProviderCapabilities(
            text=True,
            vision=True,
            tool_calling=True,
            json_mode=True,
            max_context_tokens=_context_for(model, _GEMINI_CONTEXT),
            reports_usage=True,
        )
