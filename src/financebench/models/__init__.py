"""Model providers: the ``ModelProvider`` contract, registry, and the built-in mock provider.

Importing this package registers every built-in provider (currently just ``mock``; real
providers land in Milestone 5) — CLI code should ``import financebench.models`` (not a specific
provider module) so the registry is always fully populated.
"""

from __future__ import annotations

from financebench.models import mock as _mock  # noqa: F401  (import registers "mock")
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

__all__ = [
    "MockProvider",
    "ModelProvider",
    "ProviderCapabilities",
    "ProviderInfo",
    "available_providers",
    "create_provider",
    "describe_providers",
    "get_provider_class",
    "register_provider",
]
