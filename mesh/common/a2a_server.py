"""Wrap an agent from any framework as an A2A server (a2a-sdk 1.x)."""
import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from a2a.helpers import new_text_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from a2a.utils import AGENT_CARD_WELL_KNOWN_PATH
from opentelemetry import propagate, trace
from opentelemetry.trace import Status, StatusCode
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mesh.common.cache import TTLCache
from mesh.common.retry import retry_async
from mesh.config import MAX_CONCURRENCY, RETRY_ATTEMPTS, SPECIALIST_CACHE_TTL_S

Handler = Callable[[str], Awaitable[str]]
tracer = trace.get_tracer("mesh.a2a")
logger = logging.getLogger(__name__)


class FnExecutor(AgentExecutor):
    """Runs a text-in/text-out async handler for each A2A request, inside a trace span."""

    def __init__(self, name: str, handler: Handler, cache_ttl_s: float = 0.0,
                 max_concurrency: int = MAX_CONCURRENCY,
                 retry_attempts: int = RETRY_ATTEMPTS):
        self.name = name
        self.handler = handler
        self.cache = TTLCache(cache_ttl_s)
        self.slots = asyncio.Semaphore(max_concurrency)
        self.retry_attempts = retry_attempts

    async def _answer(self, query: str, span: trace.Span) -> str:
        cached = self.cache.get(query)
        span.set_attribute("a2a.cache_hit", cached is not None)
        if cached is not None:
            return cached
        try:
            async with self.slots:
                # Transient errors (timeouts, resets) get jittered retries before giving up.
                reply = await retry_async(lambda: self.handler(query),
                                          attempts=self.retry_attempts)
        except Exception as exc:  # any framework failure becomes a readable reply
            logger.exception("%s failed", self.name)
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            # A reply (not a failed task) lets the orchestrator plan around the gap.
            return (f"{self.name} could not complete this request "
                    f"({type(exc).__name__}). Continue without it or try again.")
        self.cache.put(query, reply)  # only successful answers are cached
        return reply

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Continue the caller's trace if it sent W3C traceparent headers.
        call = getattr(context, "call_context", None)
        headers = getattr(call, "state", {}).get("headers", {}) if call else {}
        with tracer.start_as_current_span(
            f"a2a.{self.name}", context=propagate.extract(headers)
        ) as span:
            query = context.get_user_input()
            started = time.perf_counter()
            reply = await self._answer(query, span)
            span.set_attribute("a2a.agent", self.name)
            span.set_attribute("a2a.input_chars", len(query))
            span.set_attribute("a2a.output_chars", len(reply))
            span.set_attribute("a2a.latency_ms", round((time.perf_counter() - started) * 1000))
        await event_queue.enqueue_event(
            new_text_message(reply, context_id=context.context_id, task_id=context.task_id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel is not supported")


def build_card(name: str, description: str, url: str, skills: list[AgentSkill]) -> AgentCard:
    return AgentCard(
        name=name,
        description=description,
        version="0.1.0",
        supported_interfaces=[
            AgentInterface(url=url.rstrip("/"), protocol_binding="JSONRPC", protocol_version="1.0")
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=skills,
    )


def health_route(name: str) -> Route:
    """Liveness probe for Docker / Cloud Run that never touches the LLM."""

    async def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "agent": name})

    return Route("/healthz", healthz)


def build_app(card: AgentCard, handler: Handler,
              cache_ttl_s: float = SPECIALIST_CACHE_TTL_S,
              max_concurrency: int = MAX_CONCURRENCY) -> Starlette:
    request_handler = DefaultRequestHandler(
        agent_executor=FnExecutor(card.name, handler, cache_ttl_s=cache_ttl_s,
                                  max_concurrency=max_concurrency),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    return Starlette(
        routes=[
            *create_agent_card_routes(card, card_url=AGENT_CARD_WELL_KNOWN_PATH),
            # v0.3 compat keeps clients that still speak "message/send" working.
            *create_jsonrpc_routes(request_handler, "/", enable_v0_3_compat=True),
            health_route(card.name),
        ]
    )
