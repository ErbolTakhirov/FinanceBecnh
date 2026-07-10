"""Small, domain-agnostic utilities: errors, secrets handling, deterministic clocks, and ids."""

from __future__ import annotations

from financebench.utils.errors import (
    ConfigError,
    DatasetLoadError,
    ExportError,
    FinanceBenchError,
    ManifestError,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from financebench.utils.gitmeta import git_commit, git_is_dirty, os_name, python_version
from financebench.utils.ids import IdFactory, make_run_id, short_hash, slugify
from financebench.utils.secrets import SECRET_ENV_VARS, collect_secret_values, redact
from financebench.utils.timing import Clock, FrozenClock, RealClock, Stopwatch, iso

__all__ = [
    "SECRET_ENV_VARS",
    "Clock",
    "ConfigError",
    "DatasetLoadError",
    "ExportError",
    "FinanceBenchError",
    "FrozenClock",
    "IdFactory",
    "ManifestError",
    "ProviderAuthError",
    "ProviderError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "ProviderTimeoutError",
    "RealClock",
    "Stopwatch",
    "collect_secret_values",
    "git_commit",
    "git_is_dirty",
    "iso",
    "make_run_id",
    "os_name",
    "python_version",
    "redact",
    "short_hash",
    "slugify",
]
