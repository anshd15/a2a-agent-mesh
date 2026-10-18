"""Retry transient failures with exponential backoff and full jitter."""
import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")
TRANSIENT: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError)


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    attempts: int = 3,
    base_delay_s: float = 0.2,
    max_delay_s: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = TRANSIENT,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Call fn, retrying only transient errors; the last failure is re-raised."""
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except retry_on:
            if attempt >= attempts:
                raise
            cap = min(max_delay_s, base_delay_s * 2 ** (attempt - 1))
            await sleep(random.uniform(0, cap))  # full jitter avoids thundering herds
    raise ValueError("attempts must be >= 1")
