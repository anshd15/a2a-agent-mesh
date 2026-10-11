"""Wrap an agent from any framework as an A2A server."""
from collections.abc import Awaitable, Callable

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

Handler = Callable[[str], Awaitable[str]]


class FnExecutor(AgentExecutor):
    """Runs a text-in/text-out async handler for each A2A request."""

    def __init__(self, handler: Handler):
        self.handler = handler

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        reply = await self.handler(context.get_user_input())
        await event_queue.enqueue_event(new_agent_text_message(reply))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel is not supported")


def build_card(name: str, description: str, port: int, skills: list[AgentSkill]) -> AgentCard:
    return AgentCard(
        name=name,
        description=description,
        url=f"http://localhost:{port}/",
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=skills,
    )


def build_app(card: AgentCard, handler: Handler):
    request_handler = DefaultRequestHandler(
        agent_executor=FnExecutor(handler), task_store=InMemoryTaskStore()
    )
    return A2AStarletteApplication(agent_card=card, http_handler=request_handler).build()
