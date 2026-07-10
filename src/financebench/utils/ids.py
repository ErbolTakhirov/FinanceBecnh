"""Deterministic id generation.

Run ids are derived purely from their inputs (benchmark/group, model, seed, and the run
configuration) so that re-running the same benchmark configuration yields an identical id — the
prerequisite for the response cache doubling as resume (see ``execution/cache.py``): the same
command always targets the same ``runs/{run_id}/`` directory.
"""

from __future__ import annotations

import hashlib
import re

__all__ = ["IdFactory", "make_run_id", "short_hash", "slugify"]

_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")


def slugify(text: str) -> str:
    """Lowercase, filesystem-safe slug."""
    return _SLUG_RE.sub("-", text).strip("-").lower()


def short_hash(*parts: str, length: int = 8) -> str:
    """A stable short hex digest of the given parts."""
    joined = "\x1f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:length]


def make_run_id(benchmark_or_group: str, model_ref: str, seed: int) -> str:
    """A deterministic, human-readable run id.

    Same (benchmark-or-group, model, seed) always produces the same id, e.g.
    ``smoke-mock-echo-gold-1f3c9a2b``.
    """
    digest = short_hash(benchmark_or_group, model_ref, str(seed))
    return f"{slugify(benchmark_or_group)}-{slugify(model_ref)}-{digest}"


class IdFactory:
    """Issues deterministic, sequential ids scoped to a run."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._counter = 0

    def next_id(self, kind: str = "item") -> str:
        item_id = f"{self._run_id}-{kind}-{self._counter:05d}"
        self._counter += 1
        return item_id

    @property
    def issued(self) -> int:
        return self._counter
