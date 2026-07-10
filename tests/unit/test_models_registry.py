from __future__ import annotations

import pytest

import financebench.models as models_pkg
from financebench.models.base import (
    ModelProvider,
    available_providers,
    create_provider,
    describe_providers,
    get_provider_class,
    register_provider,
)
from financebench.models.mock import MockProvider
from financebench.schemas.model_io import ModelRequest, ModelResponse
from financebench.utils.errors import ConfigError


def test_mock_is_registered_on_package_import() -> None:
    assert "mock" in available_providers()


def test_get_provider_class_returns_mock() -> None:
    assert get_provider_class("mock") is MockProvider


def test_get_provider_class_unknown_raises_config_error() -> None:
    with pytest.raises(ConfigError, match="unknown provider"):
        get_provider_class("does-not-exist")


def test_create_provider_builds_an_instance() -> None:
    provider = create_provider("mock")
    assert isinstance(provider, MockProvider)


def test_register_provider_sets_provider_classvar() -> None:
    @register_provider("throwaway-test-provider")
    class _Throwaway(ModelProvider):
        async def generate(self, request: ModelRequest) -> ModelResponse:  # pragma: no cover
            raise NotImplementedError

    assert _Throwaway.provider == "throwaway-test-provider"
    assert get_provider_class("throwaway-test-provider") is _Throwaway


def test_describe_providers_never_leaks_key_value() -> None:
    @register_provider("throwaway-secret-provider")
    class _SecretProvider(ModelProvider):
        API_KEY_ENV = "THROWAWAY_TEST_KEY"
        REQUIRES_KEY = True

        async def generate(self, request: ModelRequest) -> ModelResponse:  # pragma: no cover
            raise NotImplementedError

    infos = describe_providers({"THROWAWAY_TEST_KEY": "sk-super-secret-value"})
    entry = next(i for i in infos if i.provider == "throwaway-secret-provider")
    assert entry.key_present is True
    assert entry.requires_key is True
    for info in infos:
        assert "sk-super-secret-value" not in repr(info)


def test_package_all_exports_are_importable() -> None:
    for name in models_pkg.__all__:
        assert hasattr(models_pkg, name)
