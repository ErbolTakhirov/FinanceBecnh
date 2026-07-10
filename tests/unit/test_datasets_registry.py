from __future__ import annotations

import pytest

import financebench.datasets as datasets_pkg
from financebench.datasets.base import (
    DatasetAdapter,
    available_datasets,
    create_dataset,
    get_dataset_class,
    register_dataset,
)
from financebench.datasets.smoke.adapter import SmokeDatasetAdapter
from financebench.schemas.manifest import AdapterStatus, DatasetManifest
from financebench.utils.errors import ConfigError


def test_smoke_is_registered_on_package_import() -> None:
    assert "smoke" in available_datasets()


def test_get_dataset_class_returns_smoke_adapter() -> None:
    assert get_dataset_class("smoke") is SmokeDatasetAdapter


def test_get_dataset_class_unknown_raises_config_error() -> None:
    with pytest.raises(ConfigError, match="unknown benchmark"):
        get_dataset_class("does-not-exist")


def test_create_dataset_builds_an_instance() -> None:
    assert isinstance(create_dataset("smoke"), SmokeDatasetAdapter)


def test_register_dataset_sets_name_classvar() -> None:
    @register_dataset("throwaway-test-benchmark")
    class _Throwaway(DatasetAdapter):
        def load(self, split: str):  # pragma: no cover
            raise NotImplementedError

        def manifest(self) -> DatasetManifest:
            return DatasetManifest(
                name="throwaway-test-benchmark",
                official_source="test",
                license="test",
                redistribution_status="test",
                status=AdapterStatus.PLANNED,
            )

    assert _Throwaway.name == "throwaway-test-benchmark"
    assert get_dataset_class("throwaway-test-benchmark") is _Throwaway


def test_package_all_exports_are_importable() -> None:
    for name in datasets_pkg.__all__:
        assert hasattr(datasets_pkg, name)
