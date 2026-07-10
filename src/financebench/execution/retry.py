"""Retry backoff + a simple per-run rate limiter.

Backoff is **deterministic** so runs stay reproducible: the jitter for each ``(sample, attempt)``
is drawn from a generator seeded by ``config.seed`` plus those ids, so it does not depend on
concurrent scheduling. Sleeping is injected (the engine passes ``asyncio.sleep``; tests pass a
recorder) so no test ever waits in real time.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

from financebench.schemas.run import RunConfig

__all__ = ["RateLimiter", "Sleeper", "backoff_delay"]

Sleeper = Callable[[float], Awaitable[None]]


def backoff_delay(
    config: RunConfig,
    attempts: int,
    retry_after: float | None,
    *,
    sample_id: str,
) -> float:
    """Exponential backoff with full jitter, raised to ``retry_after`` when the provider set it.

    ``attempts`` is the number of attempts made so far (1 after the first failure). The jitter
    is seeded per ``(seed, sample_id, attempts)`` so it is reproducible.
    """
    # Cap the exponent so a very large max_retries can't overflow the float power.
    exponent = min(max(attempts - 1, 0), 30)
    capped = min(config.max_delay_s, config.base_delay_s * (2.0**exponent))
    rng = random.Random(f"{config.seed}:{sample_id}:{attempts}")
    delay = rng.random() * capped  # full jitter in [0, capped)
    if retry_after is not None:
        delay = max(delay, retry_after)
    return delay


class RateLimiter:
    """Spaces request starts by at least ``1/requests_per_second`` (conservative).

    Holding the lock across the sleep serializes starts, so the effective rate never exceeds
    the limit (it ignores per-request duration, so it can be slightly under). A ``None`` /
    non-positive rate is a no-op.
    """

    def __init__(self, requests_per_second: float | None, sleep: Sleeper) -> None:
        self._min_interval = 1.0 / requests_per_second if requests_per_second else 0.0
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._started = False

    async def acquire(self) -> None:
        if self._min_interval <= 0.0:
            return
        async with self._lock:
            if self._started:
                await self._sleep(self._min_interval)
            self._started = True
