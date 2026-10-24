"""Smoke test: the zero-setup demo keeps working as the code evolves."""
import importlib
import tomllib
from pathlib import Path

from mesh import demo


async def test_demo_shows_every_scene_working():
    output = await demo.run_demo()
    assert "model calls: 0" in output
    assert "ran in parallel" in output
    assert "[EMAIL]" in output and "me@example.com" not in output
    assert "Flights Mumbai -> Goa on 2026-12-20:" in output
    assert "within budget: True" in output and "under budget" in output
    assert "approval requested; booked yet? False" in output
    assert "traveller approved -> booking MESH-" in output
    assert "[degraded mode]" in output and "'degraded': 1" in output
    assert "reply was withheld" in output
    assert "booked anything? False; quarantined: 1" in output
    assert "in the planner's instructions: True" in output


def test_console_scripts_point_at_real_callables():
    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    scripts = pyproject["project"]["scripts"]
    assert set(scripts) == {"mesh-demo", "mesh-agents"}
    for target in scripts.values():
        module, attr = target.split(":")
        assert callable(getattr(importlib.import_module(module), attr))
