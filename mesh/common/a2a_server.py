"""Wrap an agent from any framework as an A2A server."""
import time
from collections.abc import Awaitable, Callable

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
from opentelemetry import propagate, trace

Handler = Callable[[str], Awaitable[str]]
tracer = trace.get_tracer("mesh.a2a")


class FnExecutor(AgentExecutor):
    """Runs a text-in/text-out async handler for each A2A request, inside a trace span."""

    def __init__(self, name: str, handler: Handler):
        self.name = name
        self.handler = handler

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Continue the caller's trace if it sent W3C traceparent headers.
        call = getattr(context, "call_context", None)
        headers = getattr(call, "state", {}).get("headers", {}) if call else {}
        with tracer.start_as_current_span(
            f"a2a.{self.name}", context=propagate.extract(headers)
        ) as span:
            query = context.get_user_input()
            started = time.perf_counter()
            reply = await self.handler(query)
            span.set_attribute("a2a.agent", self.name)
            span.set_attribute("a2a.input_chars", len(query))
            span.set_attribute("a2a.output_chars", len(reply))
            span.set_attribute("a2a.latency_ms", round((time.perf_counter() - started) * 1000))
        await event_queue.enqueue_event(new_agent_text_message(reply))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel is not supported")


def build_card(name: str, description: str, url: str, skills: list[AgentSkill]) -> AgentCard:
    return AgentCard(
        name=name,
        description=description,
        url=f"{url.rstrip('/')}/",
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=skills,
    )


def build_app(card: AgentCard, handler: Handler):
    request_handler = DefaultRequestHandler(
        agent_executor=FnExecutor(card.name, handler), task_store=InMemoryTaskStore()
    )
    return A2AStarletteApplication(agent_card=card, http_handler=request_handler).build()
