import asyncio
import time
from types import SimpleNamespace

from a2a.helpers import get_message_text

from mesh.common.a2a_server import FnExecutor


class Queue:
    def __init__(self):
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)


async def ask(executor: FnExecutor, text: str = "q") -> str:
    queue = Queue()
    ctx = SimpleNamespace(get_user_input=lambda: text, call_context=None,
                          context_id="c", task_id="t")
    await executor.execute(ctx, queue)
    return get_message_text(queue.events[-1])


def hangs():
    started = []

    async def handler(query: str) -> str:
        started.append(query)
        await asyncio.sleep(30)  # an LLM call that never comes back
        return "too late"

    return handler, started


async def test_hung_handler_is_cut_off_and_retried():
    handler, started = hangs()
    executor = FnExecutor("flights_agent", handler, timeout_s=0.05, retry_attempts=2)

    t0 = time.perf_counter()
    reply = await ask(executor)

    assert time.perf_counter() - t0 < 1.0
    assert "could not complete" in reply and "TimeoutError" in reply
    assert len(started) == 2  # timed out, retried once, timed out again


async def test_timeout_falls_back_to_degraded_mode():
    handler, _ = hangs()

    async def rules(query: str) -> str:
        return "inventory answer"

    executor = FnExecutor("flights_agent", handler, fallback=rules, timeout_s=0.05,
                          retry_attempts=1)
    assert await ask(executor) == "[degraded mode] inventory answer"
    assert 'outcome="degraded"} 1.0' in executor.metrics.render().decode()


async def test_zero_disables_the_limit():
    async def quick(query: str) -> str:
        await asyncio.sleep(0.01)
        return "done"

    assert await ask(FnExecutor("x", quick, timeout_s=0)) == "done"
