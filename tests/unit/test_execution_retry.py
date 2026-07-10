from __future__ import annotations

import pytest

from financebench.execution.retry import RateLimiter, backoff_delay
from financebench.schemas.run import RunConfig


def test_backoff_delay_is_deterministic() -> None:
    config = RunConfig(seed=42, base_delay_s=1.0, max_delay_s=30.0)
    first = backoff_delay(config, 2, None, sample_id="finqa:test:1")
    second = backoff_delay(config, 2, None, sample_id="finqa:test:1")
    assert first == second


def test_backoff_delay_differs_across_samples() -> None:
    config = RunConfig(seed=42, base_delay_s=1.0, max_delay_s=30.0)
    a = backoff_delay(config, 1, None, sample_id="finqa:test:1")
    b = backoff_delay(config, 1, None, sample_id="finqa:test:2")
    assert a != b


def test_backoff_delay_respects_the_cap() -> None:
    config = RunConfig(seed=42, base_delay_s=1.0, max_delay_s=5.0)
    for attempts in range(1, 10):
        delay = backoff_delay(config, attempts, None, sample_id="finqa:test:1")
        cap = min(config.max_delay_s, config.base_delay_s * (2.0 ** (attempts - 1)))
        assert 0.0 <= delay <= cap


def test_backoff_delay_floors_to_retry_after() -> None:
    config = RunConfig(seed=42, base_delay_s=0.01, max_delay_s=0.02)
    delay = backoff_delay(config, 1, retry_after=10.0, sample_id="finqa:test:1")
    assert delay >= 10.0


def test_backoff_delay_exponent_does_not_overflow_with_huge_attempts() -> None:
    config = RunConfig(seed=42, base_delay_s=1.0, max_delay_s=30.0)
    delay = backoff_delay(config, 10_000, None, sample_id="finqa:test:1")
    assert delay <= config.max_delay_s


@pytest.mark.asyncio
async def test_rate_limiter_none_rate_never_sleeps() -> None:
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    limiter = RateLimiter(None, record_sleep)
    await limiter.acquire()
    await limiter.acquire()
    assert sleeps == []


@pytest.mark.asyncio
async def test_rate_limiter_sleeps_from_the_second_call_onward() -> None:
    sleeps: list[float] = []

    async def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    limiter = RateLimiter(2.0, record_sleep)  # 0.5s minimum interval
    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()
    assert sleeps == [0.5, 0.5]
