"""The ``smoke`` benchmark: a small, hand-written, in-repo fixture.

Not a real financial-reasoning benchmark — it exists purely so ``financebench eval --group
smoke`` can exercise the full pipeline (CLI, engine, cache, metrics, artifacts) end to end,
fully offline, before any real dataset adapter (Milestone 2+) exists. Every gold answer here is
a plain arithmetic fact this file's author computed directly, not model-generated — the same
discipline the mission requires for the custom SMB-CFO benchmark, applied in miniature.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pydantic import TypeAdapter

from financebench.datasets.base import DatasetAdapter, register_dataset
from financebench.schemas.manifest import AdapterStatus, DatasetManifest
from financebench.schemas.sample import CanonicalSample
from financebench.storage.jsonl import read_model_list
from financebench.utils.errors import DatasetLoadError

__all__ = ["SmokeDatasetAdapter"]

_DATA_FILE = Path(__file__).resolve().parent / "samples.jsonl"
_SAMPLE_ADAPTER: TypeAdapter[CanonicalSample] = TypeAdapter(CanonicalSample)


@register_dataset("smoke")
class SmokeDatasetAdapter(DatasetAdapter):
    name = "smoke"

    def load(self, split: str) -> Sequence[CanonicalSample]:
        if split not in self.available_splits():
            raise DatasetLoadError(
                f"smoke has no split {split!r}; available: {self.available_splits()}"
            )
        try:
            samples = read_model_list(_DATA_FILE, _SAMPLE_ADAPTER)
        except OSError as exc:
            raise DatasetLoadError(f"failed to read smoke fixture at {_DATA_FILE}: {exc}") from exc
        return [sample for sample in samples if sample.split == split]

    def manifest(self) -> DatasetManifest:
        return DatasetManifest(
            name="smoke",
            official_source=(
                "generated in-repo — this platform's own fixture, not a third-party benchmark"
            ),
            repository_url="https://github.com/ErbolTakhirov/FinanceBench",
            license="public-domain (synthetic, no copyrighted content)",
            redistribution_status="redistributable",
            official_splits=("dev",),
            local_splits=("dev",),
            expected_files=("samples.jsonl",),
            status=AdapterStatus.FULLY_SUPPORTED,
            known_limitations=(
                "Not a real financial-reasoning benchmark — exists solely to exercise the "
                "pipeline end to end offline (CLI, engine, cache, metrics, artifacts) without "
                "any external dependency. Never report smoke scores as evidence of financial "
                "capability.",
            ),
            status_tested_at="2026-07-11T00:00:00Z",
        )
