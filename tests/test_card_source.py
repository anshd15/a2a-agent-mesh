from a2a.types import AgentCard

from mesh.orchestrator.agent import card_source
from mesh.registry import AgentEntry


def entry(url: str) -> AgentEntry:
    return AgentEntry("flights_agent", url, "Finds flights.")


def test_https_and_loopback_cards_are_fetched_live():
    for url in ("https://flights.run.app", "http://localhost:8001", "http://127.0.0.1:8001",
                "http://flights.localhost:8001"):
        assert card_source(entry(url)) == f"{url}/.well-known/agent-card.json"


def test_private_network_http_gets_a_pinned_card():
    card = card_source(entry("http://flights:8001"))
    assert isinstance(card, AgentCard)
    assert card.name == "flights_agent"
    assert card.supported_interfaces[0].url == "http://flights:8001"
