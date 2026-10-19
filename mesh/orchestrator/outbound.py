"""The planner's outbound A2A HTTP client: tracing, auth and PII masking in one place.

before_model guardrails only cover what goes to Gemini. Delegated A2A messages carry the
conversation to *other services*, so every JSON text field is masked on the way out too.
"""
import json

import httpx

from mesh.orchestrator.guardrails import redact
from mesh.telemetry import inject_traceparent


def _mask(value):
    if isinstance(value, dict):
        return {k: redact(v) if k == "text" and isinstance(v, str) else _mask(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [_mask(v) for v in value]
    return value


class RedactingTransport(httpx.AsyncBaseTransport):
    """Masks card numbers, emails and phones in outgoing JSON bodies, then forwards."""

    def __init__(self, inner: httpx.AsyncBaseTransport):
        self.inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if "json" in request.headers.get("content-type", ""):
            body = await request.aread()
            try:
                masked = json.dumps(_mask(json.loads(body))).encode()
            except ValueError:
                masked = body
            headers = [(k, v) for k, v in request.headers.multi_items()
                       if k.lower() != "content-length"]
            request = httpx.Request(request.method, request.url, headers=headers,
                                    content=masked, extensions=request.extensions)
        return await self.inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self.inner.aclose()


def outbound_client(timeout: float, token: str | None = None,
                    transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    """httpx client for calls to specialists: masked bodies, bearer token, traceparent."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        transport=RedactingTransport(transport or httpx.AsyncHTTPTransport()),
        event_hooks={"request": [inject_traceparent]},
    )
