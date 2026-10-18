import importlib.util
from pathlib import Path

import httpx
from a2a.types import AgentSkill

from mesh.common.a2a_server import build_app, build_card

_spec = importlib.util.spec_from_file_location(
    "load_test", Path(__file__).parents[1] / "scripts" / "load_test.py"
)
load = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(load)


def test_percentile_is_nearest_rank():
    samples = [float(v) for v in range(1, 101)]
    assert load.percentile(samples, 50) == 50
    assert load.percentile(samples, 95) == 95
    assert load.percentile([7.0], 99) == 7


async def test_load_run_against_in_process_agent():
    async def echo(query: str) -> str:
        return query

    card = build_card("echo", "Echo", "http://test",
                      [AgentSkill(id="echo", name="Echo", description="Echo", tags=["test"])])
    transport = httpx.ASGITransport(app=build_app(card, echo))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        results = await load.run_load(client, "http://test/", requests=8, concurrency=4,
                                      text="hi", same=False)
    assert len(results) == 8 and all(ok for _, ok in results)
    assert load.report(results).startswith("requests=8 errors=0")
