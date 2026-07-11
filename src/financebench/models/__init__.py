"""Model providers: the ``ModelProvider`` contract, the registry, and every built-in provider.

Importing this package registers all of them, so CLI code should ``import financebench.models``
rather than a specific provider module — the registry is then always fully populated.

``mock`` is a *simulator holding the answer key*, not a model. It is gated behind ``--allow-mock``
and can never reach a leaderboard (see ``models/mock.py``).
"""

from __future__ import annotations

from financebench.models import mock as _mock  # noqa: F401  (import registers "mock")
from financebench.models import ollama as _ollama  # noqa: F401  (registers "ollama")
from financebench.models import (
    openai_compatible as _oai,  # noqa: F401  (registers "openai_compatible")
)
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
from financebench.models.openai_compatible import OpenAICompatibleProvider

__all__ = [
    "MockProvider",
    "ModelProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "ProviderCapabilities",
    "ProviderInfo",
    "available_providers",
    "create_provider",
    "describe_providers",
    "get_provider_class",
    "register_provider",
]
