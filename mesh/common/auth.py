"""Shared-token auth for specialist A2A endpoints.

The agent card and /healthz stay public (discovery and probes); every other route needs
`Authorization: Bearer <MESH_TOKEN>`. With no token configured, auth is off for local dev.
"""
import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

PUBLIC_PREFIXES = ("/.well-known/", "/healthz")


class BearerTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, token: str):
        super().__init__(app)
        self.expected = f"Bearer {token}"

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)
        supplied = request.headers.get("authorization", "")
        # Constant-time compare so the token can't be guessed byte by byte.
        if not hmac.compare_digest(supplied.encode(), self.expected.encode()):
            return JSONResponse({"error": "unauthorized"}, status_code=401,
                                headers={"WWW-Authenticate": "Bearer"})
        return await call_next(request)


def protect(app, token: str | None):
    """Require the shared token on non-public routes; a no-op when token is unset."""
    if token:
        app.add_middleware(BearerTokenMiddleware, token=token)
    return app
