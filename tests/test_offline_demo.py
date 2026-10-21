"""Smoke test: the zero-setup demo keeps working as the code evolves."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "offline_demo", Path(__file__).parents[1] / "scripts" / "offline_demo.py"
)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


async def test_demo_shows_every_scene_working():
    output = await demo.run_demo()
    assert "model calls: 0" in output
    assert "[EMAIL]" in output and "me@example.com" not in output
    assert "Flights Mumbai -> Goa on 2026-12-20:" in output
    assert "approval requested; booked yet? False" in output
    assert "traveller approved -> booking MESH-" in output
    assert "in the planner's instructions: True" in output
