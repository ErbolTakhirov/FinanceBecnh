from __future__ import annotations

from financebench.utils.errors import (
    FinanceBenchError,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)


def test_provider_error_is_a_finance_bench_error() -> None:
    assert issubclass(ProviderError, FinanceBenchError)


def test_default_retryable_flags() -> None:
    assert ProviderAuthError("bad key").retryable is False
    assert ProviderTimeoutError("slow").retryable is True
    assert ProviderRateLimitError("429").retryable is True
    assert ProviderResponseError("500").retryable is True


def test_retryable_override() -> None:
    err = ProviderResponseError("400 bad request", retryable=False)
    assert err.retryable is False


def test_retry_after_is_carried() -> None:
    err = ProviderRateLimitError("slow down", retry_after=2.5)
    assert err.retry_after == 2.5


def test_provider_field_defaults_to_none() -> None:
    err = ProviderTimeoutError("timed out")
    assert err.provider is None
    err2 = ProviderTimeoutError("timed out", provider="openai")
    assert err2.provider == "openai"
