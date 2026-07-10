"""The response cache — and, by construction, the platform's resume mechanism.

Cache key = a canonicalized hash of the validated :class:`ModelRequest`: provider, exact model
id, secret-free ``base_url_id``, prompt version, generation params, normalized messages,
benchmark + benchmark version, sample id, and tool config. Two fields are excluded because they
are delivery-mechanism details that must never affect whether a cached answer is reused:
``request_id`` (a per-call correlation id) and ``timeout_s`` (how long we're willing to wait,
not part of what determines the answer).

Because a run's id is itself deterministic (:func:`financebench.utils.ids.make_run_id` hashes
the benchmark/group, model, and seed), re-invoking an identical ``eval`` command always targets
the same ``runs/{run_id}/`` directory and re-derives every artifact in one pass over the same
ordered sample list — samples whose request hash is already cached resolve instantly with zero
network calls. ``--resume`` is a UX flag on that same idempotent command, not a second mechanism.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from financebench.schemas.model_io import ModelRequest, ModelResponse
from financebench.schemas.run import CacheMode

__all__ = ["CACHE_KEY_VERSION", "CacheStats", "ResponseCache", "request_hash"]

#: Bump on any change to what/how a request is hashed — invalidates every prior cache entry by
#: construction (they simply won't collide with newly computed keys).
CACHE_KEY_VERSION = 1

#: Delivery-mechanism fields that must not affect whether a cached answer is reused.
_EXCLUDED_FIELDS = frozenset({"request_id", "timeout_s"})


def request_hash(request: ModelRequest) -> str:
    """A stable hash of everything about ``request`` that determines the answer.

    ``model_dump(mode="json")`` already reduces the validated request to plain JSON-compatible
    types (tuples become lists, enums become their values), so ``json.dumps(..., sort_keys=True)``
    alone is sufficient to canonicalize it — no separate tuple/dict-order normalization pass
    is needed on top.
    """
    payload = {
        "v": CACHE_KEY_VERSION,
        **{
            key: value
            for key, value in request.model_dump(mode="json").items()
            if key not in _EXCLUDED_FIELDS
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CacheStats:
    """Summary of what's on disk, for the ``cache stats`` CLI command."""

    entry_count: int
    total_size_bytes: int


class ResponseCache:
    """A sharded, content-addressed, on-disk cache of :class:`ModelResponse` objects.

    Sharded on the first two hex characters of the key (git's ``objects/`` trick) so no single
    directory ever holds more than ~64k files. Writes are atomic (write to a temp file, then
    rename) so a killed process never leaves a torn cache entry, and a failed provider call is
    never cached — only a successful :meth:`~financebench.models.base.ModelProvider.generate`
    result is, so a transient error doesn't get pinned forever.
    """

    def __init__(self, cache_dir: str | Path, *, mode: CacheMode = CacheMode.READ_WRITE) -> None:
        self.cache_dir = Path(cache_dir)
        self.mode = mode

    @property
    def _root(self) -> Path:
        return self.cache_dir / "responses" / f"v{CACHE_KEY_VERSION}"

    def _path_for(self, key: str) -> Path:
        return self._root / key[:2] / f"{key}.json"

    def get(self, request: ModelRequest) -> ModelResponse | None:
        """Look up a cached response, or ``None`` on a miss (or when the mode bypasses reads)."""
        if self.mode in (CacheMode.OFF, CacheMode.REFRESH):
            return None
        path = self._path_for(request_hash(request))
        if not path.is_file():
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            return ModelResponse.model_validate(envelope["response"])
        except (OSError, json.JSONDecodeError, KeyError, ValidationError):
            # A corrupt or foreign-shaped cache entry is treated as a miss, not a crash.
            return None

    def put(
        self,
        request: ModelRequest,
        response: ModelResponse,
        *,
        financebench_version: str,
        written_at: str,
    ) -> None:
        """Persist ``response`` under ``request``'s hash, unless the mode forbids writes."""
        if self.mode in (CacheMode.OFF, CacheMode.READ_ONLY):
            return
        path = self._path_for(request_hash(request))
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {
            "cache_key": path.stem,
            "written_at": written_at,
            "financebench_version": financebench_version,
            "response": response.model_dump(mode="json"),
        }
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        tmp_path.replace(path)

    def stats(self) -> CacheStats:
        """Entry count and total size on disk, for the ``cache stats`` CLI command."""
        if not self._root.is_dir():
            return CacheStats(entry_count=0, total_size_bytes=0)
        files = [p for p in self._root.rglob("*.json") if p.is_file()]
        return CacheStats(
            entry_count=len(files), total_size_bytes=sum(p.stat().st_size for p in files)
        )

    def clear(self) -> int:
        """Delete every cached response; returns the number of entries removed."""
        if not self._root.is_dir():
            return 0
        files = [p for p in self._root.rglob("*.json") if p.is_file()]
        for file_path in files:
            file_path.unlink()
        return len(files)
