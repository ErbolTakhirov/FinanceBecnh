"""JSONL and single-object JSON read/write helpers shared by dataset adapters and the run-artifact
writer (``storage/artifacts.py``, Milestone 1 chunk 8).

Kept generic over any Pydantic model (via :class:`~pydantic.TypeAdapter`) rather than a single
mixed "Event" union — the platform's run artifacts are several distinctly-typed JSONL files
(``predictions.jsonl``, ``metric_details.jsonl``, ``errors.jsonl``, ...), not one event stream.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, TypeAdapter

__all__ = [
    "read_jsonl",
    "read_model_json",
    "read_model_list",
    "write_jsonl",
    "write_model_json",
    "write_model_list_json",
]

_ModelT = TypeVar("_ModelT", bound=BaseModel)


def read_jsonl(path: str | Path) -> Iterator[dict[str, object]]:
    """Yield each non-empty line of a JSONL file as a parsed dict."""
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                yield json.loads(stripped)


def read_model_list(path: str | Path, adapter: TypeAdapter[_ModelT]) -> list[_ModelT]:
    """Read and validate every record of a JSONL file into a list of ``_ModelT``."""
    return [adapter.validate_python(record) for record in read_jsonl(path)]


def write_model_json(path: str | Path, model: BaseModel) -> None:
    """Write a single Pydantic model to a pretty-printed JSON file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")


def read_model_json(path: str | Path, adapter: TypeAdapter[_ModelT]) -> _ModelT:
    """Read and validate a single-object JSON file into a model."""
    return adapter.validate_json(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path: str | Path, models: Iterable[BaseModel]) -> None:
    """Write one Pydantic model per line — the shape of every ``*.jsonl`` run artifact
    (``predictions.jsonl``, ``metric_details.jsonl``, ...). Overwrites any existing file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for model in models:
            handle.write(model.model_dump_json() + "\n")


def write_model_list_json(path: str | Path, models: Iterable[BaseModel]) -> None:
    """Write a JSON array of models to a single pretty-printed file (as opposed to
    :func:`write_jsonl`'s one-per-line — used for small manifest-style lists, not per-sample
    records)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = [model.model_dump(mode="json") for model in models]
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
