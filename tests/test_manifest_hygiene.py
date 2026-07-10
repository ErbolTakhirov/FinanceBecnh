"""Repo-hygiene: every dataset manifest claiming `fully_supported` or `supported_public_subset`
must have a matching end-to-end test file. A Pydantic validator can prove `status_tested_at` was
*set*, but only a real test file proves the claim was actually *exercised* — this test makes that
the difference between "someone remembered to fill in a timestamp" and "there is a test that
would fail if this adapter broke."
"""

from __future__ import annotations

from pathlib import Path

import financebench.datasets  # noqa: F401  (import registers every built-in dataset adapter)
from financebench.datasets.base import available_datasets, create_dataset
from financebench.schemas.manifest import AdapterStatus

_TESTED_STATUSES = (AdapterStatus.FULLY_SUPPORTED, AdapterStatus.SUPPORTED_PUBLIC_SUBSET)
_TESTS_DATASETS_DIR = Path(__file__).parent / "datasets"


def test_every_supported_manifest_has_a_matching_e2e_test_file() -> None:
    missing: list[str] = []
    for name in available_datasets():
        manifest = create_dataset(name).manifest()
        if manifest.status not in _TESTED_STATUSES:
            continue
        expected = _TESTS_DATASETS_DIR / f"test_{name}_e2e.py"
        if not expected.is_file():
            missing.append(f"{name} (status={manifest.status.value}) -> expected {expected}")
    assert not missing, (
        "these manifests claim a tested-support status but have no matching e2e test file:\n"
        + "\n".join(missing)
    )
