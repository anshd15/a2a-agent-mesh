import uuid

from a2a.types import AgentSkill
from starlette.testclient import TestClient

from mesh.common.a2a_server import build_app, build_card

TOKEN = "s3cret-token"


async def echo(text: str) -> str:
    return text


def client(token: str | None = TOKEN) -> TestClient:
    card = build_card("echo_agent", "Echo", "http://127.0.0.1:9000",
                      [AgentSkill(id="echo", name="Echo", description="Echo", tags=["t"])])
    return TestClient(build_app(card, echo, token=token))


def send(c: TestClient, headers: dict | None = None):
    payload = {"jsonrpc": "2.0", "id": "1", "method": "message/send",
               "params": {"message": {"role": "user", "messageId": uuid.uuid4().hex,
                                      "parts": [{"kind": "text", "text": "hi"}]}}}
    return c.post("/", json=payload, headers=headers or {})


def test_card_and_health_stay_public():
    c = client()
    assert c.get("/.well-known/agent-card.json").status_code == 200
    assert c.get("/healthz").status_code == 200


def test_rpc_requires_the_shared_token():
    c = client()
    assert send(c).status_code == 401
    assert send(c, {"Authorization": "Bearer wrong"}).status_code == 401
    ok = send(c, {"Authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200 and "error" not in ok.json()


def test_auth_is_off_without_a_token():
    assert send(client(token=None)).status_code == 200
