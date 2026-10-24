"""Prometheus metrics for a specialist: requests by outcome and handler latency.

Each specialist gets its own registry, so several apps in one process (tests, the demo)
never collide. /metrics is not a public route: when MESH_TOKEN is set, scrape it with
`authorization: Bearer <token>` (Prometheus `authorization` / `bearer_token` config).
"""
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

OUTCOMES = ("ok", "cache_hit", "degraded", "error")
# LLM-backed handlers are slow; buckets span 50 ms to 1 minute.
LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60)


class SpecialistMetrics:
    def __init__(self, agent: str):
        self.agent = agent
        self.registry = CollectorRegistry()
        self.requests = Counter("a2a_requests", "A2A requests handled, by outcome",
                                ["agent", "outcome"], registry=self.registry)
        self.latency = Histogram("a2a_request_seconds", "Time to answer one A2A request",
                                 ["agent"], buckets=LATENCY_BUCKETS, registry=self.registry)
        for outcome in OUTCOMES:  # export zeros so dashboards and alerts see every series
            self.requests.labels(agent, outcome)

    def observe(self, outcome: str, seconds: float) -> None:
        self.requests.labels(self.agent, outcome).inc()
        self.latency.labels(self.agent).observe(seconds)

    def render(self) -> bytes:
        return generate_latest(self.registry)


def metrics_route(metrics: SpecialistMetrics) -> Route:
    async def scrape(request: Request) -> Response:
        return Response(metrics.render(), media_type=CONTENT_TYPE_LATEST)

    return Route("/metrics", scrape)
