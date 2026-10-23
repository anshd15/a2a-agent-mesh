"""Activities specialist built natively with ADK, exposed via to_a2a."""
from urllib.parse import urlparse

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent

from mesh.common.a2a_server import health_route
from mesh.common.auth import protect
from mesh.config import ACTIVITIES_PORT, ACTIVITIES_URL, HOST, MESH_TOKEN, MODEL
from mesh.data.inventory import activity_options
from mesh.telemetry import setup_tracing


def find_activities(city: str, interests: str) -> dict:
    """Suggest priced activities in a city; best matches for the comma-separated interests
    come first, each with its duration in hours."""
    # Deterministic mock inventory; swap for Google Places / Search grounding.
    return {"city": city, "activities": activity_options(city, interests)}


root_agent = Agent(
    name="activities_agent",
    model=MODEL,
    description="Suggests things to do at a destination.",
    instruction="Use find_activities and return a short, day-by-day list of ideas.",
    tools=[find_activities],
)
# The card advertises the public URL (scheme, host, port) - e.g. https on Cloud Run -
# while uvicorn below still binds the local ACTIVITIES_PORT.
_public = urlparse(ACTIVITIES_URL)
app = to_a2a(
    root_agent,
    host=_public.hostname,
    port=_public.port or (443 if _public.scheme == "https" else 80),
    protocol=_public.scheme,
)
app.router.routes.append(health_route("activities_agent"))
protect(app, MESH_TOKEN)

if __name__ == "__main__":
    setup_tracing("activities_agent")
    uvicorn.run(app, host=HOST, port=ACTIVITIES_PORT)
