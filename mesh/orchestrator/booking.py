"""Mock booking that only runs after the traveller explicitly approves it (human in the loop)."""
import hashlib
import json

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext


def book_trip(tool_context: ToolContext) -> dict:
    """Book the finalised itinerary. The traveller is always asked to approve first."""
    itinerary = tool_context.state.get("itinerary")
    if not itinerary:
        return {"status": "error", "message": "Call finalize_itinerary before booking."}
    # Deterministic reference: re-approving the same itinerary never double-books it.
    digest = hashlib.sha256(json.dumps(itinerary, sort_keys=True).encode()).hexdigest()
    booking = {
        "reference": f"MESH-{digest[:8].upper()}",
        "destination": itinerary["destination"],
        "total_usd": round(sum(item["cost_usd"] for item in itinerary["items"]), 2),
    }
    tool_context.state["booking"] = booking
    return {"status": "booked", **booking}


# require_confirmation makes ADK pause the run and ask the traveller before the tool executes;
# declining means the tool never runs.
book_trip_tool = FunctionTool(book_trip, require_confirmation=True)
