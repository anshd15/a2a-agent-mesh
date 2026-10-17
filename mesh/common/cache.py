"""Tiny TTL cache so identical specialist queries don't pay for a second LLM call."""
import time
from collections.abc import Callable


class TTLCache:
    """In-memory, per-process cache keyed on whitespace/case-normalised query text."""

    def __init__(self, ttl_s: float, max_items: int = 256,
                 clock: Callable[[], float] = time.monotonic):
        self.ttl_s = ttl_s
        self.max_items = max_items
        self.clock = clock
        self._items: dict[str, tuple[float, str]] = {}

    @staticmethod
    def key(text: str) -> str:
        return " ".join(text.lower().split())

    def get(self, text: str) -> str | None:
        key = self.key(text)
        hit = self._items.get(key)
        if hit is None:
            return None
        expires, value = hit
        if self.clock() >= expires:
            del self._items[key]
            return None
        return value

    def put(self, text: str, value: str) -> None:
        if self.ttl_s <= 0:
            return
        if len(self._items) >= self.max_items:
            self._items.pop(next(iter(self._items)))  # evict the oldest insertion
        self._items[self.key(text)] = (self.clock() + self.ttl_s, value)
