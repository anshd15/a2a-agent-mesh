from mesh.agents import flights, hotels


def test_a2a_cards_advertise_skills():
    for mod in (flights, hotels):
        assert mod.card.skills
        assert mod.card.supported_interfaces[0].url.startswith("http://localhost:")


def test_orchestrator_wires_all_specialists():
    from google.adk.tools.agent_tool import AgentTool

    from mesh.orchestrator.agent import root_agent

    names = {t.name for t in root_agent.tools if isinstance(t, AgentTool)}
    assert names == {"flights_agent", "hotels_agent", "activities_agent"}
