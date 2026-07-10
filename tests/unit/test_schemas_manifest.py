from __future__ import annotations

import pytest
from pydantic import ValidationError

from financebench.schemas.manifest import AdapterStatus, DatasetManifest


def _base_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "name": "finqa",
        "official_source": "https://github.com/czyssrs/FinQA",
        "license": "MIT (code) / CC BY 4.0 (data)",
        "redistribution_status": "redistributable",
        "status": AdapterStatus.PLANNED,
    }
    kwargs.update(overrides)
    return kwargs


def test_planned_status_does_not_require_tested_at() -> None:
    manifest = DatasetManifest.model_validate(_base_kwargs())
    assert manifest.status is AdapterStatus.PLANNED
    assert manifest.status_tested_at is None


def test_unavailable_status_does_not_require_tested_at() -> None:
    manifest = DatasetManifest.model_validate(
        _base_kwargs(status=AdapterStatus.UNAVAILABLE, license="n/a")
    )
    assert manifest.status is AdapterStatus.UNAVAILABLE


@pytest.mark.parametrize(
    "status", [AdapterStatus.FULLY_SUPPORTED, AdapterStatus.SUPPORTED_PUBLIC_SUBSET]
)
def test_supported_status_requires_tested_at(status: AdapterStatus) -> None:
    with pytest.raises(ValidationError, match="status_tested_at"):
        DatasetManifest.model_validate(_base_kwargs(status=status))


def test_fully_supported_with_tested_at_succeeds() -> None:
    manifest = DatasetManifest.model_validate(
        _base_kwargs(
            status=AdapterStatus.FULLY_SUPPORTED,
            status_tested_at="2026-07-11T00:00:00Z",
        )
    )
    assert manifest.status_tested_at == "2026-07-11T00:00:00Z"
