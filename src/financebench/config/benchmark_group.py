"""The YAML benchmark-group file shape (``configs/benchmark_groups/*.yaml``): a named set of
(dataset, split, weight) entries evaluated together as one ``--group``."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from financebench.utils.errors import ConfigError, ManifestError

__all__ = ["BenchmarkEntry", "BenchmarkGroup", "load_benchmark_group"]


class BenchmarkEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    split: str
    weight: float = 1.0


class BenchmarkGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    benchmarks: tuple[BenchmarkEntry, ...]


def load_benchmark_group(path: str | Path) -> BenchmarkGroup:
    """Load and validate a benchmark-group YAML file."""
    file_path = Path(path)
    try:
        raw = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"could not read benchmark group at {file_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in benchmark group at {file_path}: {exc}") from exc
    group = BenchmarkGroup.model_validate(raw)
    if not group.benchmarks:
        raise ManifestError(f"benchmark group {file_path} declares no benchmarks")
    return group
