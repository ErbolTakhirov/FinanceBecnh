"""Typed exception hierarchy for FinanceBench.

All library errors derive from :class:`FinanceBenchError`. Provider errors carry a
``retryable`` flag so the run engine can decide whether to retry without inspecting
provider-specific details.
"""

from __future__ import annotations

__all__ = [
    "ConfigError",
    "DatasetLoadError",
    "ExportError",
    "FinanceBenchError",
    "ManifestError",
    "ProviderAuthError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "ProviderTimeoutError",
]


class FinanceBenchError(Exception):
    """Base class for all FinanceBench errors."""


class ConfigError(FinanceBenchError):
    """Invalid configuration, CLI arguments, or environment."""


class ManifestError(ConfigError):
    """A benchmark-group or dataset manifest is missing, malformed, or references an unknown
    dataset."""


class DatasetLoadError(ConfigError):
    """A dataset adapter failed to load, prepare, or validate its samples."""


class ExportError(FinanceBenchError):
    """An export or report target could not be produced (e.g. an optional dependency is
    missing)."""


class ProviderError(FinanceBenchError):
    """Base class for model-provider (adapter) failures.

    ``retryable`` tells the engine whether retrying the same request might succeed.
    """

    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        retryable: bool | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        # Server-suggested minimum wait before retrying (e.g. from a Retry-After header).
        self.retry_after = retry_after
        if retryable is not None:
            self.retryable = retryable


class ProviderAuthError(ProviderError):
    """Missing or invalid API credentials. Not retryable."""

    retryable = False


class ProviderTimeoutError(ProviderError):
    """The provider did not respond within the timeout. Retryable."""

    retryable = True


class ProviderRateLimitError(ProviderError):
    """The provider rejected the request due to rate limiting. Retryable, and should honor
    ``retry_after`` when the provider supplied one."""

    retryable = True


class ProviderResponseError(ProviderError):
    """The provider returned an error status or an unusable payload.

    Defaults to retryable (covers transient 5xx responses); callers should set
    ``retryable=False`` for definitive client errors (e.g. 400/404).
    """

    retryable = True
