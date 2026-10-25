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

from mesh.common.auth import protect
from mesh.common.cache import TTLCache
from mesh.common.metrics import SpecialistMetrics, metrics_route
from mesh.common.retry import retry_async
from mesh.config import (
    HANDLER_TIMEOUT_S,
    MAX_CONCURRENCY,
    MESH_TOKEN,
    RETRY_ATTEMPTS,
    SPECIALIST_CACHE_TTL_S,
)

Handler = Callable[[str], Awaitable[str]]
tracer = trace.get_tracer("mesh.a2a")
logger = logging.getLogger(__name__)


class FnExecutor(AgentExecutor):
    """Runs a text-in/text-out async handler for each A2A request, inside a trace span."""

    def __init__(self, name: str, handler: Handler, cache_ttl_s: float = 0.0,
                 max_concurrency: int = MAX_CONCURRENCY,
                 retry_attempts: int = RETRY_ATTEMPTS,
                 fallback: Handler | None = None,
                 timeout_s: float | None = HANDLER_TIMEOUT_S):
        self.name = name
        self.handler = handler
        self.fallback = fallback
        self.timeout_s = timeout_s or None  # 0 / None: no per-request limit
        self.cache = TTLCache(cache_ttl_s)
        self.slots = asyncio.Semaphore(max_concurrency)
        self.retry_attempts = retry_attempts
        self.metrics = SpecialistMetrics(name)

    async def _answer(self, query: str, span: trace.Span) -> tuple[str, str]:
        """Return (reply, outcome) where outcome is ok / cache_hit / degraded / error."""
        cached = self.cache.get(query)
        span.set_attribute("a2a.cache_hit", cached is not None)
        if cached is not None:
            return cached, "cache_hit"
        try:
            async with self.slots:
                # A hung LLM call is cancelled at timeout_s; the TimeoutError is transient, so
                # it gets the same jittered retries as dropped connections, then the fallback.
                reply = await retry_async(
                    lambda: asyncio.wait_for(self.handler(query), self.timeout_s),
                    attempts=self.retry_attempts,
                )
        except Exception as exc:  # any framework failure becomes a readable reply
            logger.exception("%s failed", self.name)
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
            if self.fallback is not None:
                # Degraded mode: a rule-based answer beats no answer. Never cached, so
                # the full LLM path is tried again on the next request.
                try:
                    reply = await self.fallback(query)
                    span.set_attribute("a2a.fallback", True)
                    return f"[degraded mode] {reply}", "degraded"
                except Exception:
                    logger.exception("%s fallback failed", self.name)
            # A reply (not a failed task) lets the orchestrator plan around the gap.
            return (f"{self.name} could not complete this request "
                    f"({type(exc).__name__}). Continue without it or try again."), "error"
        self.cache.put(query, reply)  # only successful answers are cached
        return reply, "ok"

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Continue the caller's trace if it sent W3C traceparent headers.
        call = getattr(context, "call_context", None)
        headers = getattr(call, "state", {}).get("headers", {}) if call else {}
        with tracer.start_as_current_span(
            f"a2a.{self.name}", context=propagate.extract(headers)
        ) as span:
            query = context.get_user_input()
            started = time.perf_counter()
            reply, outcome = await self._answer(query, span)
            elapsed = time.perf_counter() - started
            self.metrics.observe(outcome, elapsed)
            span.set_attribute("a2a.agent", self.name)
            span.set_attribute("a2a.outcome", outcome)
            span.set_attribute("a2a.input_chars", len(query))
            span.set_attribute("a2a.output_chars", len(reply))
            span.set_attribute("a2a.latency_ms", round(elapsed * 1000))
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
              max_concurrency: int = MAX_CONCURRENCY,
              token: str | None = MESH_TOKEN,
              fallback: Handler | None = None,
              timeout_s: float | None = HANDLER_TIMEOUT_S) -> Starlette:
    executor = FnExecutor(card.name, handler, cache_ttl_s=cache_ttl_s,
                          max_concurrency=max_concurrency, fallback=fallback,
                          timeout_s=timeout_s)
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    app = Starlette(
        routes=[
            *create_agent_card_routes(card, card_url=AGENT_CARD_WELL_KNOWN_PATH),
            # v0.3 compat keeps clients that still speak "message/send" working.
            *create_jsonrpc_routes(request_handler, "/", enable_v0_3_compat=True),
            health_route(card.name),
            metrics_route(executor.metrics),
        ]
    )
    return protect(app, token)
