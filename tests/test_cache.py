from mesh.common.cache import TTLCache


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_entries_expire_after_ttl():
    clock = Clock()
    cache = TTLCache(ttl_s=10, clock=clock)
    cache.put("Goa hotels", "list")
    clock.now = 9.9
    assert cache.get("goa  HOTELS") == "list"
    clock.now = 10
    assert cache.get("Goa hotels") is None


def test_oldest_entry_is_evicted_when_full():
    cache = TTLCache(ttl_s=60, max_items=2)
    for q in ("a", "b", "c"):
        cache.put(q, q.upper())
    assert cache.get("a") is None and cache.get("c") == "C"
