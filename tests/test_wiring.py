from mesh.agents import flights, hotels


def test_a2a_cards_advertise_skills():
    for mod in (flights, hotels):
        assert mod.card.skills
        assert mod.card.url.startswith("http://localhost:")


def test_orchestrator_wires_all_specialists():
    from mesh.orchestrator.agent import root_agent

    names = {a.name for a in root_agent.sub_agents}
    assert names == {"flights_agent", "hotels_agent", "activities_agent"}
