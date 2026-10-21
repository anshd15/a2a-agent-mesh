from types import SimpleNamespace

from a2a.helpers import get_message_text

from mesh.common.a2a_server import FnExecutor


class Queue:
    def __init__(self):
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)


async def ask(executor: FnExecutor, text: str) -> str:
    queue = Queue()
    ctx = SimpleNamespace(get_user_input=lambda: text, call_context=None,
                          context_id="c", task_id="t")
    await executor.execute(ctx, queue)
    return get_message_text(queue.events[-1])


async def llm_down(query: str) -> str:
    raise RuntimeError("model unavailable")


async def rules(query: str) -> str:
    return f"rule-based answer for {query}"


async def test_fallback_answers_when_the_llm_path_fails():
    executor = FnExecutor("flights_agent", llm_down, fallback=rules, retry_attempts=1)
    assert await ask(executor, "BOM-GOI") == "[degraded mode] rule-based answer for BOM-GOI"


async def test_fallback_replies_are_not_cached():
    calls = []

    async def recovers(query: str) -> str:
        calls.append(query)
        if len(calls) == 1:
            raise RuntimeError("blip")
        return "full answer"

    executor = FnExecutor("flights_agent", recovers, fallback=rules, cache_ttl_s=60,
                          retry_attempts=1)
    assert (await ask(executor, "q")).startswith("[degraded mode]")
    assert await ask(executor, "q") == "full answer"


async def test_broken_fallback_still_yields_the_error_reply():
    async def also_down(query: str) -> str:
        raise ValueError("no data")

    executor = FnExecutor("flights_agent", llm_down, fallback=also_down, retry_attempts=1)
    assert "could not complete" in await ask(executor, "q")
