def test_planner_exposes_deterministic_tools():
    from mesh.orchestrator.agent import root_agent

    names = {getattr(t, "__name__", getattr(t, "name", "")) for t in root_agent.tools}
    assert {"save_trip_preferences", "check_budget", "convert_currency",
            "finalize_itinerary", "remember_preference", "book_trip"} <= names
    assert "finalize_itinerary" in root_agent.instruction
