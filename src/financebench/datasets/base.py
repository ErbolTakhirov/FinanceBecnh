"""The ``DatasetAdapter`` contract and a small dataset registry.

Every benchmark — the in-repo ``smoke`` fixture or a real one like FinQA — implements one
method, ``load``, returning :class:`~financebench.schemas.sample.CanonicalSample` records, plus
``manifest`` describing its provenance, license, and (honestly) how well-tested it is. Adapters
are registered by name with :func:`register_dataset` and constructed via :func:`create_dataset`,
so the CLI and execution layer never import a concrete adapter directly — the same seam
``models/base.py`` uses for providers (see ``docs/adding_benchmarks.md``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import ClassVar, TypeVar

from financebench.schemas.manifest import DatasetManifest
from financebench.schemas.sample import CanonicalSample
from financebench.utils.errors import ConfigError

__all__ = [
    "DatasetAdapter",
    "available_datasets",
    "create_dataset",
    "get_dataset_class",
    "register_dataset",
]


class DatasetAdapter(ABC):
    """Abstract base for all benchmark dataset adapters."""

    name: ClassVar[str] = ""

    @abstractmethod
    def load(self, split: str) -> Sequence[CanonicalSample]:
        """Return the canonical samples for ``split``.

        Must raise :class:`~financebench.utils.errors.DatasetLoadError` for an unknown split or
        missing/corrupt data — never return a silently-empty or partial list.
        """
        raise NotImplementedError

    @abstractmethod
    def manifest(self) -> DatasetManifest:
        """Provenance, license, and support-status record for this benchmark."""
        raise NotImplementedError

    def available_splits(self) -> tuple[str, ...]:
        """Local split names this adapter can actually load (from its own manifest)."""
        return self.manifest().local_splits


_REGISTRY: dict[str, type[DatasetAdapter]] = {}

_DatasetT = TypeVar("_DatasetT", bound=type[DatasetAdapter])


def register_dataset(name: str) -> Callable[[_DatasetT], _DatasetT]:
    """Class decorator registering a dataset adapter under ``name``."""

    def decorate(cls: _DatasetT) -> _DatasetT:
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return decorate


def available_datasets() -> list[str]:
    """Sorted list of registered benchmark names."""
    return sorted(_REGISTRY)


def get_dataset_class(name: str) -> type[DatasetAdapter]:
    """Look up a registered dataset adapter class, or raise :class:`ConfigError`."""
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ConfigError(
            f"unknown benchmark {name!r}; available benchmarks: {available_datasets()}"
        ) from exc


def create_dataset(name: str) -> DatasetAdapter:
    """Instantiate the dataset adapter registered under ``name``."""
    return get_dataset_class(name)()
