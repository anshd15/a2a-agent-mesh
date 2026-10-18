"""Fire concurrent A2A requests at one specialist and report latency percentiles.

    python scripts/load_test.py http://localhost:8001 --requests 50 --concurrency 10
    python scripts/load_test.py http://localhost:8001 --same   # one repeated query: cache hits
"""
import argparse
import asyncio
import math
import time
import uuid

import httpx


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile, pct in 0-100."""
    if not values:
        raise ValueError("no samples")
    ordered = sorted(values)
    return ordered[max(1, math.ceil(pct / 100 * len(ordered))) - 1]


def payload(text: str) -> dict:
    return {
        "jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "message/send",
        "params": {"message": {"role": "user", "messageId": uuid.uuid4().hex,
                               "parts": [{"kind": "text", "text": text}]}},
    }


async def run_load(client: httpx.AsyncClient, url: str, requests: int, concurrency: int,
                   text: str, same: bool) -> list[tuple[float, bool]]:
    slots = asyncio.Semaphore(concurrency)

    async def one(i: int) -> tuple[float, bool]:
        async with slots:
            started = time.perf_counter()
            try:
                resp = await client.post(url, json=payload(text if same else f"{text} #{i}"))
                ok = resp.status_code == 200 and "error" not in resp.json()
            except httpx.HTTPError:
                ok = False
            return (time.perf_counter() - started) * 1000, ok

    return await asyncio.gather(*(one(i) for i in range(requests)))


def report(results: list[tuple[float, bool]]) -> str:
    latencies = [ms for ms, ok in results if ok]
    errors = len(results) - len(latencies)
    if not latencies:
        return f"all {len(results)} requests failed"
    stats = " ".join(f"p{p}={percentile(latencies, p):.0f}ms" for p in (50, 95, 99))
    return (f"requests={len(results)} errors={errors} ({errors / len(results):.0%}) "
            f"{stats} max={max(latencies):.0f}ms")


async def main(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(timeout=120) as client:
        results = await run_load(client, args.url.rstrip("/") + "/", args.requests,
                                 args.concurrency, args.text, args.same)
    print(report(results))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--text", default="Flights from Mumbai to Goa on 2026-12-20")
    parser.add_argument("--same", action="store_true", help="repeat one query (cache hits)")
    asyncio.run(main(parser.parse_args()))
