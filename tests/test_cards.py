"""Agent cards are the contract other A2A clients read: version, docs, skills, examples."""
import importlib.metadata

import pytest
from starlette.testclient import TestClient

from mesh.agents import activities, flights, hotels

SPECIALISTS = [flights, hotels, activities]


@pytest.mark.parametrize("module", SPECIALISTS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_card_advertises_release_docs_and_examples(module):
    with TestClient(module.app) as client:
        card = client.get("/.well-known/agent-card.json").json()
    assert card["version"] == importlib.metadata.version("a2a-agent-mesh")
    assert card["documentationUrl"].startswith("https://github.com/anshd15/a2a-agent-mesh")
    assert card["provider"]["organization"] == "a2a-agent-mesh"
    assert all(skill["examples"] for skill in card["skills"])


@pytest.mark.parametrize("module", SPECIALISTS, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
async def test_every_advertised_example_is_answerable_even_in_degraded_mode(module):
    for example in module.card.skills[0].examples:
        reply = await module.fallback(example)
        assert " need " not in reply, (example, reply)
