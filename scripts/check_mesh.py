"""Health check: confirm every specialist publishes a valid A2A agent card."""
import sys

import httpx

from mesh.config import ACTIVITIES_URL, FLIGHTS_URL, HOTELS_URL

CARD_PATH = "/.well-known/agent-card.json"


def main() -> int:
    failures = 0
    for base in (FLIGHTS_URL, HOTELS_URL, ACTIVITIES_URL):
        try:
            card = httpx.get(base.rstrip("/") + CARD_PATH, timeout=5).raise_for_status().json()
            print(f"OK   {card['name']:<18} {base}  skills={len(card.get('skills', []))}")
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            failures += 1
            print(f"FAIL {base}  {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
