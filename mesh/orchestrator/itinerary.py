"""Structured itinerary, so the final answer is validated data rather than free text."""
from typing import Literal

from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel, Field, ValidationError


class Item(BaseModel):
    day: int = Field(ge=1)
    kind: Literal["flight", "hotel", "activity", "other"]
    description: str = Field(min_length=1)
    cost_usd: float = Field(default=0, ge=0)


class Itinerary(BaseModel):
    destination: str
    items: list[Item] = Field(min_length=1)

    @property
    def total_usd(self) -> float:
        return round(sum(i.cost_usd for i in self.items), 2)


def render_markdown(itinerary: Itinerary, budget_usd: float | None = None) -> str:
    lines = [f"## Trip to {itinerary.destination}"]
    for day in sorted({i.day for i in itinerary.items}):
        lines.append(f"\n**Day {day}**")
        for item in (i for i in itinerary.items if i.day == day):
            cost = f" (${item.cost_usd:,.0f})" if item.cost_usd else ""
            lines.append(f"- {item.kind}: {item.description}{cost}")
    total = f"\n**Total: ${itinerary.total_usd:,.0f}**"
    if budget_usd is not None:
        gap = budget_usd - itinerary.total_usd
        total += f" - ${abs(gap):,.0f} {'under' if gap >= 0 else 'OVER'} budget"
    return "\n".join([*lines, total])


def finalize_itinerary(destination: str, items: list[dict], tool_context: ToolContext) -> dict:
    """Validate the final plan and return it as markdown.

    items: list of {"day": int, "kind": "flight"|"hotel"|"activity"|"other",
    "description": str, "cost_usd": float}. Present the returned markdown to the traveller.
    """
    try:
        itinerary = Itinerary.model_validate({"destination": destination, "items": items})
    except ValidationError as exc:
        return {"status": "error", "message": exc.errors(include_url=False)}
    budget = (tool_context.state.get("trip") or {}).get("budget_usd")
    tool_context.state["itinerary"] = itinerary.model_dump()
    return {"status": "ok", "total_usd": itinerary.total_usd,
            "markdown": render_markdown(itinerary, budget)}
