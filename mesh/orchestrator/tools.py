"""Deterministic tools the trip planner uses alongside its remote specialists."""
from google.adk.tools.tool_context import ToolContext


def save_trip_preferences(
    origin: str,
    destination: str,
    start_date: str,
    end_date: str,
    budget_usd: float,
    interests: str,
    tool_context: ToolContext,
) -> dict:
    """Save the traveller's brief to session state so every step plans from the same facts.

    Dates are YYYY-MM-DD; interests is a comma-separated list.
    """
    trip = {
        "origin": origin,
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "budget_usd": budget_usd,
        "interests": interests,
    }
    tool_context.state["trip"] = trip
    return {"status": "saved", "trip": trip}


def check_budget(costs_usd: list[float], tool_context: ToolContext) -> dict:
    """Add up quoted costs and compare them with the saved budget (exact maths, no guessing)."""
    total = round(sum(costs_usd), 2)
    budget = (tool_context.state.get("trip") or {}).get("budget_usd")
    if budget is None:
        return {"total_usd": total, "status": "no budget saved"}
    return {
        "total_usd": total,
        "budget_usd": budget,
        "within_budget": total <= budget,
        "remaining_usd": round(budget - total, 2),
    }
