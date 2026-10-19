import json

import httpx

from mesh.orchestrator.outbound import outbound_client


def capture():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    return httpx.MockTransport(handler), seen


async def test_pii_is_masked_in_delegated_messages():
    transport, seen = capture()
    body = {"params": {"message": {"parts": [
        {"kind": "text", "text": "Book for me@example.com, card 4111 1111 1111 1111"},
        {"kind": "data", "data": {"note": "untouched"}},
    ]}}}
    async with outbound_client(5, transport=transport) as client:
        await client.post("http://127.0.0.1:8001/", json=body)
    sent = json.loads(seen[0].content)
    parts = sent["params"]["message"]["parts"]
    assert parts[0]["text"] == "Book for [EMAIL], card [CARD]"
    assert parts[1]["data"] == {"note": "untouched"}
    assert int(seen[0].headers["content-length"]) == len(seen[0].content)


async def test_token_header_sent_only_when_configured():
    transport, seen = capture()
    async with outbound_client(5, token="s3cret", transport=transport) as client:
        await client.get("http://127.0.0.1:8001/.well-known/agent-card.json")
    async with outbound_client(5, transport=transport) as client:
        await client.get("http://127.0.0.1:8001/.well-known/agent-card.json")
    assert seen[0].headers["authorization"] == "Bearer s3cret"
    assert "authorization" not in seen[1].headers
