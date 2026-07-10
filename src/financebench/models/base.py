"""The ``ModelProvider`` contract and a small provider registry.

Every provider — mock or real — implements one async method::

    async def generate(self, request: ModelRequest) -> ModelResponse

Providers are registered by name with :func:`register_provider` and constructed from the
environment via :func:`create_provider`, so the execution engine and CLI never import a concrete
provider directly. This is the single seam new providers plug into (see
``docs/adding_models.md``).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import ClassVar, TypeVar
from urllib.parse import urlsplit, urlunsplit

from financebench.schemas.model_io import ModelRequest, ModelResponse
from financebench.utils.errors import ConfigError

__all__ = [
    "ModelProvider",
    "ProviderCapabilities",
    "ProviderInfo",
    "available_providers",
    "create_provider",
    "describe_providers",
    "get_provider_class",
    "register_provider",
]


@dataclass(frozen=True)
class ProviderCapabilities:
    """Best-effort capability introspection for a provider/model pair.

    Populated by known-model tables where a provider has them; unknown models fall back to a
    conservative default (text-only, no structured output guarantee) rather than a guess —
    ``doctor``/``benchmark-info`` must show what's actually known, never a fabricated superset.
    """

    text: bool = True
    vision: bool = False
    tool_calling: bool = False
    json_mode: bool = False
    max_context_tokens: int | None = None
    streaming: bool = False
    reports_usage: bool = False


class ModelProvider(ABC):
    """Abstract base for all model providers.

    Concrete providers set :attr:`provider` (done automatically by :func:`register_provider`)
    and implement :meth:`generate` and :meth:`from_env`.
    """

    provider: ClassVar[str] = ""

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Produce a single :class:`ModelResponse` for ``request``.

        Transport-level failures must raise a :class:`~financebench.utils.errors.ProviderError`
        subclass so the engine can record a failure and decide whether to retry.
        """
        raise NotImplementedError

    def capabilities(self, model: str) -> ProviderCapabilities:
        """Best-effort capability introspection for ``model`` under this provider.

        Default is a conservative text-only guess; concrete providers override this with a
        known-model table where they have one.
        """
        return ProviderCapabilities()

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ModelProvider:
        """Construct a provider from environment variables.

        Resolution precedence for base URLs etc. is env-var > built-in default.
        """
        raise NotImplementedError(f"{cls.__name__} does not implement from_env()")

    async def aclose(self) -> None:
        """Release any resources (e.g. HTTP clients). Default: no-op."""
        return None


_REGISTRY: dict[str, type[ModelProvider]] = {}

_ProviderT = TypeVar("_ProviderT", bound=type[ModelProvider])


def register_provider(name: str) -> Callable[[_ProviderT], _ProviderT]:
    """Class decorator registering a provider under ``name``."""

    def decorate(cls: _ProviderT) -> _ProviderT:
        cls.provider = name
        _REGISTRY[name] = cls
        return cls

    return decorate


def available_providers() -> list[str]:
    """Sorted list of registered provider names."""
    return sorted(_REGISTRY)


def get_provider_class(name: str) -> type[ModelProvider]:
    """Look up a registered provider class, or raise :class:`ConfigError`."""
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ConfigError(
            f"unknown provider {name!r}; available providers: {available_providers()}"
        ) from exc


def create_provider(name: str, env: Mapping[str, str] | None = None) -> ModelProvider:
    """Instantiate the provider for ``name`` from the environment."""
    return get_provider_class(name).from_env(env)


@dataclass(frozen=True)
class ProviderInfo:
    """Non-secret configuration status for a registered provider."""

    provider: str
    requires_key: bool
    key_env_var: str | None
    base_url: str | None
    key_present: bool


def _strip_userinfo(url: str | None) -> str | None:
    """Remove any ``user:pass@`` credentials from a URL before displaying it."""
    if not url:
        return url
    parts = urlsplit(url)
    if "@" in parts.netloc:
        host = parts.netloc.rsplit("@", 1)[1]
        return urlunsplit(parts._replace(netloc=host))
    return url


def describe_providers(env: Mapping[str, str] | None = None) -> list[ProviderInfo]:
    """Report each registered provider's config status — **never the key value itself**."""
    source = env if env is not None else os.environ
    infos: list[ProviderInfo] = []
    for name, cls in sorted(_REGISTRY.items()):
        key_env = getattr(cls, "API_KEY_ENV", None)
        base_env = getattr(cls, "BASE_URL_ENV", None)
        base_url = getattr(cls, "DEFAULT_BASE_URL", None)
        if base_env and source.get(base_env):
            base_url = source[base_env]
        base_url = _strip_userinfo(base_url)
        infos.append(
            ProviderInfo(
                provider=name,
                requires_key=bool(getattr(cls, "REQUIRES_KEY", False)),
                key_env_var=key_env,
                base_url=base_url,
                key_present=bool(key_env and source.get(key_env)),
            )
        )
    return infos
