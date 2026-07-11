"""Model providers: the ``ModelProvider`` contract, the registry, and every built-in provider.

Importing this package registers all of them, so CLI code should ``import financebench.models``
rather than a specific provider module — the registry is then always fully populated.

``mock`` is a *simulator holding the answer key*, not a model. It is gated behind ``--allow-mock``
and can never reach a leaderboard (see ``models/mock.py``).
"""

from __future__ import annotations

from financebench.models import anthropic as _anthropic  # noqa: F401  (registers "anthropic")
from financebench.models import mock as _mock  # noqa: F401  (import registers "mock")
from financebench.models import ollama as _ollama  # noqa: F401  (registers "ollama")
from financebench.models import (
    openai as _openai,  # noqa: F401  (registers "openai", "openrouter", "gemini")
)
from financebench.models import (
    openai_compatible as _oai,  # noqa: F401  (registers "openai_compatible")
)
from financebench.models.anthropic import AnthropicProvider
from financebench.models.base import (
    ModelProvider,
    ProviderCapabilities,
    ProviderInfo,
    available_providers,
    create_provider,
    describe_providers,
    get_provider_class,
    register_provider,
)
from financebench.models.mock import MockProvider
from financebench.models.ollama import OllamaProvider
from financebench.models.openai import GeminiProvider, OpenAIProvider, OpenRouterProvider
from financebench.models.openai_compatible import OpenAICompatibleProvider
from financebench.models.verification import (
    ProviderVerification,
    VerificationRecord,
    verify_all_providers,
    verify_provider,
)

__all__ = [
    "AnthropicProvider",
    "GeminiProvider",
    "MockProvider",
    "ModelProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
    "OpenRouterProvider",
    "ProviderCapabilities",
    "ProviderInfo",
    "ProviderVerification",
    "VerificationRecord",
    "available_providers",
    "create_provider",
    "describe_providers",
    "get_provider_class",
    "register_provider",
    "verify_all_providers",
    "verify_provider",
]
