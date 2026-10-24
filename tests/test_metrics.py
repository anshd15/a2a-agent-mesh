import uuid
from types import SimpleNamespace

from a2a.types import AgentSkill
from starlette.testclient import TestClient

from mesh.common.a2a_server import FnExecutor, build_app, build_card

TOKEN = "metrics-token"


class Queue:
    async def enqueue_event(self, event):
        pass


async def ask(executor: FnExecutor, text: str) -> None:
    ctx = SimpleNamespace(get_user_input=lambda: text, call_context=None,
                          context_id="c", task_id="t")
    await executor.execute(ctx, Queue())


def count(metrics_text: str, outcome: str, agent: str = "x") -> float:
    line = next(l for l in metrics_text.splitlines()
                if l.startswith(f'a2a_requests_total{{agent="{agent}",outcome="{outcome}"}}'))
    return float(line.rsplit(" ", 1)[1])


async def test_every_outcome_is_counted():
    async def ok(query: str) -> str:
        if query == "boom":
            raise RuntimeError("down")
        return "fine"

    async def rules(query: str) -> str:
        return "rule answer"

    plain = FnExecutor("x", ok, cache_ttl_s=60, retry_attempts=1)
    for text in ("q", "q", "boom"):  # ok, cache hit, error
        await ask(plain, text)
    text = plain.metrics.render().decode()
    assert count(text, "ok") == 1 and count(text, "cache_hit") == 1
    assert count(text, "error") == 1 and count(text, "degraded") == 0
    assert 'a2a_request_seconds_count{agent="x"} 3.0' in text

    with_fallback = FnExecutor("x", ok, fallback=rules, retry_attempts=1)
    await ask(with_fallback, "boom")
    assert count(with_fallback.metrics.render().decode(), "degraded") == 1


def test_metrics_endpoint_is_scrapeable_with_the_mesh_token():
    async def echo(text: str) -> str:
        return text

    card = build_card("echo_agent", "Echo", "http://127.0.0.1:9000",
                      [AgentSkill(id="echo", name="Echo", description="Echo", tags=["t"])])
    client = TestClient(build_app(card, echo, token=TOKEN, cache_ttl_s=60))
    auth = {"Authorization": f"Bearer {TOKEN}"}
    payload = {"jsonrpc": "2.0", "id": "1", "method": "message/send",
               "params": {"message": {"role": "user", "messageId": uuid.uuid4().hex,
                                      "parts": [{"kind": "text", "text": "hi"}]}}}
    for _ in range(2):
        client.post("/", json=payload, headers=auth)

    assert client.get("/metrics").status_code == 401  # not public, unlike /healthz
    scraped = client.get("/metrics", headers=auth)
    assert scraped.status_code == 200 and scraped.headers["content-type"].startswith("text/plain")
    assert count(scraped.text, "ok", "echo_agent") == 1
    assert count(scraped.text, "cache_hit", "echo_agent") == 1
