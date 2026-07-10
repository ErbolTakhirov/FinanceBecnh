from __future__ import annotations

from datetime import UTC, datetime

from financebench.utils.timing import FrozenClock, RealClock, Stopwatch, iso


def test_iso_formats_utc_with_z_suffix() -> None:
    moment = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)
    assert iso(moment) == "2026-07-11T12:00:00Z"


def test_frozen_clock_now_is_fixed() -> None:
    clock = FrozenClock()
    assert clock.now() == clock.now()
    assert clock.now_iso().endswith("Z")


def test_frozen_clock_monotonic_advances_by_step() -> None:
    clock = FrozenClock(step_s=1.5)
    assert clock.monotonic() == 0.0
    assert clock.monotonic() == 1.5
    assert clock.monotonic() == 3.0


def test_frozen_clock_zero_step_is_zero_latency() -> None:
    clock = FrozenClock()
    assert clock.monotonic() == clock.monotonic() == 0.0


def test_frozen_clock_tick_advances_wall_clock() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    clock = FrozenClock(start=start)
    clock.tick(60)
    assert clock.now() == datetime(2026, 1, 1, 0, 1, 0, tzinfo=UTC)


def test_stopwatch_measures_elapsed_ms_deterministically() -> None:
    clock = FrozenClock(step_s=0.25)
    with Stopwatch(clock) as sw:
        pass
    assert sw.elapsed_ms == 250.0


def test_real_clock_returns_a_datetime() -> None:
    clock = RealClock()
    assert isinstance(clock.now(), datetime)
    assert isinstance(clock.monotonic(), float)
