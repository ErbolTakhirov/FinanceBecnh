"""The YAML benchmark-group file shape (``configs/benchmark_groups/*.yaml``): a named set of
(dataset, split, weight) entries evaluated together as one ``--group``."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

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
    #: What this group is for, and what its scores do and do not mean. Optional, but a group whose
    #: purpose is not written down invites its scores being read as something they are not.
    description: str | None = None
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
    try:
        group = BenchmarkGroup.model_validate(raw)
    except ValidationError as exc:
        # A malformed group file is a config mistake, and must read as one. Letting pydantic's
        # ValidationError escape gives the user a raw traceback instead of a fixable message.
        raise ConfigError(f"invalid benchmark group at {file_path}:\n{exc}") from exc
    if not group.benchmarks:
        raise ManifestError(f"benchmark group {file_path} declares no benchmarks")
    return group
