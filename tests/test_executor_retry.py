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


def blips_once():
    calls = []

    async def handler(query: str) -> str:
        calls.append(query)
        if len(calls) == 1:
            raise ConnectionError("upstream reset")
        return "recovered"

    return handler, calls


async def test_transient_failure_is_retried_transparently():
    handler, calls = blips_once()
    assert await ask(FnExecutor("flights_agent", handler, retry_attempts=2), "q") == "recovered"
    assert len(calls) == 2


async def test_retries_can_be_disabled():
    handler, calls = blips_once()
    reply = await ask(FnExecutor("flights_agent", handler, retry_attempts=1), "q")
    assert "could not complete" in reply and len(calls) == 1
