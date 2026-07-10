"""FinQA dataset adapter — maps the official train/dev/test JSON into ``CanonicalSample``
records.

Schema of a raw FinQA record (verified directly against the official ``test.json``, not assumed
from the paper):

.. code-block:: text

    {
      "id": "ETR/2016/page_23.pdf-2",
      "pre_text": [...], "post_text": [...],
      "table": [["", "amount ( in millions )"], ["2014 net revenue", "$ 5735"], ...],
      "qa": {
        "question": "...", "answer": "94", "program": "subtract(5829, 5735)",
        "exe_ans": 94.0, "ann_table_rows": [...], "ann_text_rows": [...]
      }
    }

``table`` (not the prettier ``table_ori``) is used both for the model-facing context and by
``evaluation/native/finqa.py``'s program executor, because gold programs reference row labels
in ``table``'s normalized (lowercased, ``"-32 ( 32 )"``-style negative) form.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from financebench.datasets.base import DatasetAdapter, register_dataset
from financebench.datasets.downloader import download_file
from financebench.schemas.common import AnswerType, SplitOrigin
from financebench.schemas.manifest import AdapterStatus, DatasetManifest
from financebench.schemas.sample import (
    CanonicalSample,
    EvaluationSpec,
    GoldAnswer,
    SampleContext,
    SourceInfo,
    Table,
)
from financebench.utils.errors import DatasetLoadError
from financebench.utils.ids import slugify

__all__ = ["FinQAAdapter"]

# Pinned to a specific commit (not "main") so `prepare` always fetches the exact same bytes,
# independent of upstream changes — see docs/reproducibility.md.
_PINNED_COMMIT = "0f16e2867befa6840783e58be38c9efb9229d742"
_RAW_BASE = f"https://raw.githubusercontent.com/czyssrs/FinQA/{_PINNED_COMMIT}/dataset"
_OFFICIAL_URLS: dict[str, str] = {
    "train": f"{_RAW_BASE}/train.json",
    "dev": f"{_RAW_BASE}/dev.json",
    "test": f"{_RAW_BASE}/test.json",
}
_DEFAULT_DATA_DIR = Path("data/downloads/finqa")


@register_dataset("finqa")
class FinQAAdapter(DatasetAdapter):
    name = "finqa"

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self._data_dir = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_DIR

    def prepare(self) -> None:
        """Download the official train/dev/test JSON files (skips any already present)."""
        for split, url in _OFFICIAL_URLS.items():
            dest = self._data_dir / f"{split}.json"
            if dest.is_file():
                continue
            download_file(url, dest)

    def load(self, split: str) -> Sequence[CanonicalSample]:
        if split not in self.available_splits():
            raise DatasetLoadError(
                f"finqa has no split {split!r}; available: {self.available_splits()}"
            )
        path = self._data_dir / f"{split}.json"
        if not path.is_file():
            raise DatasetLoadError(
                f"finqa {split} data not found at {path}; run `financebench prepare finqa` "
                "first (or point this adapter at a data_dir containing it)"
            )
        try:
            raw_records = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DatasetLoadError(f"failed to read finqa {split} data at {path}: {exc}") from exc

        return [self._to_canonical_sample(record, split) for record in raw_records]

    def _to_canonical_sample(self, record: dict[str, Any], split: str) -> CanonicalSample:
        qa = record["qa"]
        table_rows = tuple(tuple(row) for row in record.get("table", ()))
        tables = (Table(table_id="table_1", rows=table_rows),) if table_rows else ()

        exe_ans = qa.get("exe_ans")
        numeric_value = float(exe_ans) if isinstance(exe_ans, int | float) else None

        return CanonicalSample(
            benchmark="finqa",
            benchmark_version=_PINNED_COMMIT,
            split=split,
            split_origin=SplitOrigin.OFFICIAL,
            sample_id=f"finqa:{split}:{slugify(str(record['id']))}",
            task_family="numerical_reasoning",
            capability_tags=("calculation", "table_text", "evidence_grounding"),
            question=str(qa["question"]),
            context=SampleContext(
                text=tuple(record.get("pre_text", ())) + tuple(record.get("post_text", ())),
                tables=tables,
            ),
            gold=GoldAnswer(
                answer=str(qa.get("answer", "")),
                answer_type=AnswerType.NUMERIC,
                numeric_value=numeric_value,
                program=qa.get("program"),
            ),
            evaluation=EvaluationSpec(relative_tolerance=0.001),
            source=SourceInfo(
                license="MIT (code) / CC BY 4.0 (data)",
                url="https://github.com/czyssrs/FinQA",
                redistributable=True,
            ),
            metadata={"source_document": str(record.get("filename", ""))},
        )

    def manifest(self) -> DatasetManifest:
        return DatasetManifest(
            name="finqa",
            official_source="https://github.com/czyssrs/FinQA",
            paper_url="https://aclanthology.org/2021.emnlp-main.300/",
            repository_url="https://github.com/czyssrs/FinQA",
            version_or_commit=_PINNED_COMMIT,
            download_method="official GitHub raw JSON (train/dev/test)",
            checksum=None,  # recorded per-file by `prepare()`'s download_file() call, not fixed
            official_splits=("train", "dev", "test", "private_test"),
            local_splits=("train", "dev", "test"),
            license="MIT (code) / CC BY 4.0 (data, via FinTabNet/CDLA-Permissive provenance)",
            redistribution_status="redistributable",
            expected_files=("train.json", "dev.json", "test.json"),
            status=AdapterStatus.FULLY_SUPPORTED,
            known_limitations=(
                "private_test is a blind split (no public gold) scorable only via the official "
                "CodaLab leaderboard — not supported by this adapter.",
                "Program accuracy (FinQA's second native metric) is not yet computed here — it "
                "requires a program-eliciting prompt profile this platform doesn't have yet; "
                "see evaluation/native/finqa.py's module docstring.",
            ),
            status_tested_at="2026-07-11T00:00:00Z",
        )
