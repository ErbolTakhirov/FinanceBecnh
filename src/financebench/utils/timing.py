"""Clock abstraction so runs are reproducible under test.

The execution engine takes a :class:`Clock` for *both* wall-clock timestamps (recorded in
artifacts) and elapsed-time measurement (latency). Production uses :class:`RealClock`; tests
inject :class:`FrozenClock` to get byte-stable artifacts (fixed timestamps, zero/known latency).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable

__all__ = ["Clock", "FrozenClock", "RealClock", "Stopwatch", "iso"]


def iso(moment: datetime) -> str:
    """Render a UTC datetime as a ``...Z`` ISO-8601 string."""
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


@runtime_checkable
class Clock(Protocol):
    """Minimal time source: wall clock plus a monotonic counter for durations."""

    def now(self) -> datetime: ...

    def now_iso(self) -> str: ...

    def monotonic(self) -> float: ...


class RealClock:
    """Wall-clock + monotonic time from the standard library."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def now_iso(self) -> str:
        return iso(self.now())

    def monotonic(self) -> float:
        return time.monotonic()


class FrozenClock:
    """Deterministic clock for tests.

    Wall-clock time is fixed at ``start`` (advance it explicitly with :meth:`tick`). The
    monotonic counter returns ``0.0`` and advances by ``step_s`` on each read, so latency
    measurements are exactly reproducible (default ``0.0`` → zero latency).
    """

    def __init__(self, start: datetime | None = None, step_s: float = 0.0) -> None:
        self._now = start or datetime(2026, 1, 1, tzinfo=UTC)
        self._mono = 0.0
        self._step = step_s

    def now(self) -> datetime:
        return self._now

    def now_iso(self) -> str:
        return iso(self._now)

    def monotonic(self) -> float:
        value = self._mono
        self._mono += self._step
        return value

    def tick(self, seconds: float) -> None:
        """Advance the frozen wall clock by ``seconds``."""
        self._now += timedelta(seconds=seconds)


class Stopwatch:
    """Context manager measuring elapsed milliseconds against a :class:`Clock`."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._start = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> Stopwatch:
        self._start = self._clock.monotonic()
        return self

    def __exit__(self, *exc: object) -> None:
        self.elapsed_ms = (self._clock.monotonic() - self._start) * 1000.0
