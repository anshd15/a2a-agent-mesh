"""End-to-end check of the A2A wrapper over real HTTP routes, no LLM needed."""
import uuid

from a2a.types import AgentSkill
from starlette.testclient import TestClient

from mesh.common.a2a_server import build_app, build_card


async def shout(text: str) -> str:
    return text.upper()


def client() -> TestClient:
    card = build_card(
        "echo_agent", "Echoes in caps.", "http://testserver",
        [AgentSkill(id="echo", name="Echo", description="Shout back", tags=["test"])],
    )
    return TestClient(build_app(card, shout))


def test_agent_card_is_served():
    card = client().get("/.well-known/agent-card.json").json()
    assert card["name"] == "echo_agent"
    assert card["skills"][0]["id"] == "echo"


def test_message_send_round_trip():
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "messageId": uuid.uuid4().hex,
                "parts": [{"kind": "text", "text": "hello mesh"}],
            }
        },
    }
    reply = client().post("/", json=payload).json()
    assert "error" not in reply, reply
    assert "HELLO MESH" in str(reply["result"])


def test_healthz_reports_agent_name():
    assert client().get("/healthz").json() == {"status": "ok", "agent": "echo_agent"}


def test_adk_specialist_also_exposes_healthz():
    from mesh.agents import activities

    with TestClient(activities.app) as c:
        assert c.get("/healthz").json()["agent"] == "activities_agent"
