"""Which remote A2A agents the orchestrator can delegate to.

Defaults to the three bundled specialists. Point MESH_REGISTRY at a JSON file to add or
replace agents (e.g. a partner's A2A endpoint) without touching code:

    [{"name": "visa_agent", "url": "https://visa.example.com", "description": "Visa rules"}]
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path

from mesh.config import ACTIVITIES_URL, FLIGHTS_URL, HOTELS_URL


@dataclass(frozen=True)
class AgentEntry:
    name: str
    url: str
    description: str


DEFAULTS = [
    AgentEntry("flights_agent", FLIGHTS_URL, "Finds and compares flights."),
    AgentEntry("hotels_agent", HOTELS_URL, "Finds best-value hotels."),
    AgentEntry("activities_agent", ACTIVITIES_URL, "Suggests things to do."),
]


def load_registry(path: str | None = None) -> list[AgentEntry]:
    """Bundled defaults, overridden or extended by entries from the registry file."""
    path = path or os.getenv("MESH_REGISTRY")
    entries = {e.name: e for e in DEFAULTS}
    if path:
        for raw in json.loads(Path(path).read_text()):
            entries[raw["name"]] = AgentEntry(raw["name"], raw["url"], raw.get("description", ""))
    return list(entries.values())
