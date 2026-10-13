"""Talk to any A2A agent with raw JSON-RPC - no SDK, just the protocol.

    python scripts/a2a_ping.py http://localhost:8001 "Flights from Mumbai to Goa on 2026-12-20"
"""
import sys
import uuid

import httpx

CARD_PATH = "/.well-known/agent-card.json"


def texts(obj):
    """Yield every text part inside a Message/Task/Artifact payload."""
    if isinstance(obj, dict):
        if obj.get("kind") == "text":
            yield obj["text"]
        for value in obj.values():
            yield from texts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from texts(value)


def main(base_url: str, text: str) -> None:
    with httpx.Client(timeout=120) as client:
        card = client.get(base_url.rstrip("/") + CARD_PATH).raise_for_status().json()
        print(f"-> {card['name']}: {card['description']}")
        print("   skills:", ", ".join(s["id"] for s in card.get("skills", [])))
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "messageId": uuid.uuid4().hex,
                    "parts": [{"kind": "text", "text": text}],
                }
            },
        }
        # A2A 1.x lists endpoints under supportedInterfaces; 0.3 used a top-level url.
        rpc_url = card.get("url") or card["supportedInterfaces"][0]["url"]
        reply = client.post(rpc_url, json=payload).raise_for_status().json()
    if "error" in reply:
        sys.exit(f"A2A error: {reply['error']}")
    result = reply["result"]
    # A Task carries its answer in artifacts/status; a Message carries it in parts.
    source = result.get("artifacts") or result.get("status", {}).get("message") or result
    print("\n".join(texts(source)))


if __name__ == "__main__":
    main(sys.argv[1], " ".join(sys.argv[2:]) or "Hello")
