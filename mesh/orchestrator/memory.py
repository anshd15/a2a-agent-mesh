"""Traveller preferences that outlive a single trip, via ADK's `user:`-scoped state.

Keys prefixed `user:` are shared by every session of the same user, so a preference
saved while planning Goa is already in the planner's instruction when planning Tokyo.
"""
from google.adk.tools.tool_context import ToolContext

KEY = "user:preferences"
MAX_PREFERENCES = 20


def remember_preference(preference: str, tool_context: ToolContext) -> dict:
    """Remember a lasting traveller preference for future trips, e.g. 'aisle seat',
    'vegetarian meals' or 'boutique hotels'. Do not use it for one-off trip details."""
    text = " ".join(preference.split())
    if not text:
        return {"status": "error", "message": "preference is empty"}
    kept = [p for p in tool_context.state.get(KEY) or [] if p.lower() != text.lower()]
    preferences = [*kept, text][-MAX_PREFERENCES:]  # newest wins, bounded
    tool_context.state[KEY] = preferences
    return {"status": "saved", "preferences": preferences}


def forget_preferences(tool_context: ToolContext) -> dict:
    """Forget every saved preference for this traveller (when they ask to be forgotten)."""
    tool_context.state[KEY] = []
    return {"status": "cleared"}
