"""FnExecutor behaviour, driven directly with fake A2A context and queue."""
import asyncio
from types import SimpleNamespace

from a2a.helpers import get_message_text

from mesh.common.a2a_server import FnExecutor


class FakeQueue:
    def __init__(self):
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)


def ctx(text: str):
    return SimpleNamespace(get_user_input=lambda: text, call_context=None,
                           context_id="ctx-1", task_id="task-1")


async def run(executor: FnExecutor, text: str) -> str:
    queue = FakeQueue()
    await executor.execute(ctx(text), queue)
    return get_message_text(queue.events[-1])


async def test_failures_become_a_readable_reply():
    async def broken(query: str) -> str:
        raise TimeoutError("upstream API timed out")

    reply = await run(FnExecutor("flights_agent", broken), "BOM to GOI")
    assert "flights_agent could not complete" in reply and "TimeoutError" in reply


async def test_identical_queries_hit_the_cache():
    calls = []

    async def counting(query: str) -> str:
        calls.append(query)
        return f"answer {len(calls)}"

    executor = FnExecutor("hotels_agent", counting, cache_ttl_s=60)
    assert await run(executor, "Hotels in Goa") == "answer 1"
    assert await run(executor, "  hotels in  GOA ") == "answer 1"
    assert len(calls) == 1


async def test_cache_disabled_and_errors_never_cached():
    calls = []

    async def flaky(query: str) -> str:
        calls.append(query)
        if len(calls) == 1:
            raise RuntimeError("blip")
        return "ok"

    executor = FnExecutor("hotels_agent", flaky, cache_ttl_s=60)
    assert "could not complete" in await run(executor, "q")
    assert await run(executor, "q") == "ok"
    no_cache = FnExecutor("x", flaky, cache_ttl_s=0)
    await run(no_cache, "q")
    await run(no_cache, "q")
    assert len(calls) == 4


async def test_concurrency_is_capped():
    active = peak = 0

    async def slow(query: str) -> str:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return query

    executor = FnExecutor("flights_agent", slow, max_concurrency=2)
    replies = await asyncio.gather(*(run(executor, f"q{i}") for i in range(6)))
    assert peak == 2
    assert sorted(replies) == [f"q{i}" for i in range(6)]
