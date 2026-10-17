"""FnExecutor behaviour, driven directly with fake A2A context and queue."""
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
