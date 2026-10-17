"""LLM-as-judge: run each scenario through the trip planner and score the itinerary.

    python eval/judge.py     # needs GOOGLE_API_KEY and the specialists running

Alongside the judge's 1-5 scores, a deterministic "delegation" metric records which
specialists the planner actually called. Writes eval/results.md.
"""
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from google import genai
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

from mesh.config import MODEL

HERE = Path(__file__).parent
CRITERIA = ("completeness", "budget_adherence", "coherence", "grounding")
SPECIALISTS = ("flights_agent", "hotels_agent", "activities_agent")
RUBRIC = """You are grading a travel itinerary produced by an AI trip planner.
Score each criterion from 1 (poor) to 5 (excellent):
- completeness: covers flights, hotel and activities for every day requested
- budget_adherence: total cost is stated and within budget, or overspend is clearly flagged
- coherence: dates, places and timings are consistent with each other
- grounding: prices and options look taken from tool results, not invented
Return JSON only."""


class Score(BaseModel):
    completeness: int = Field(ge=1, le=5)
    budget_adherence: int = Field(ge=1, le=5)
    coherence: int = Field(ge=1, le=5)
    grounding: int = Field(ge=1, le=5)
    rationale: str


@dataclass
class Result:
    scenario: str
    score: Score
    delegated: set[str]


def load_scenarios(path: Path = HERE / "scenarios.jsonl") -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def delegation_coverage(delegated: set[str], expected: tuple[str, ...] = SPECIALISTS) -> float:
    """Share of expected specialists the planner actually handed work to."""
    return len(set(expected) & delegated) / len(expected)


def _row(result: Result) -> list[float]:
    return [getattr(result.score, c) for c in CRITERIA] + [delegation_coverage(result.delegated)]


def _fmt(value: float) -> str:
    return str(value) if isinstance(value, int) else f"{value:.2f}"


def summarise(results: list[Result]) -> str:
    columns = [*CRITERIA, "delegation"]
    header = "| Scenario | " + " | ".join(columns) + " |\n|---|" + "---|" * len(columns)
    lines = [f"| {r.scenario} | " + " | ".join(_fmt(v) for v in _row(r)) + " |"
             for r in results]
    averages = [mean(col) for col in zip(*(_row(r) for r in results))]
    lines.append("| **average** | " + " | ".join(f"**{a:.2f}**" for a in averages) + " |")
    return "\n".join([header, *lines])


async def plan(runner: InMemoryRunner, prompt: str) -> tuple[str, set[str]]:
    """Run one request; return the final text and every agent that produced an event."""
    session = await runner.session_service.create_session(app_name=runner.app_name,
                                                          user_id="judge")
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    final, authors = "", set()
    async for event in runner.run_async(user_id="judge", session_id=session.id,
                                        new_message=message):
        authors.add(event.author)
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(p.text or "" for p in event.content.parts)
    return final, authors


async def judge(client: genai.Client, prompt: str, itinerary: str) -> Score:
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=f"{RUBRIC}\n\nTraveller request:\n{prompt}\n\nItinerary:\n{itinerary}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=Score, temperature=0
        ),
    )
    return Score.model_validate_json(response.text)


async def main() -> None:
    from mesh.orchestrator.agent import root_agent

    runner = InMemoryRunner(agent=root_agent)
    client = genai.Client()
    results = []
    for scenario in load_scenarios():
        itinerary, authors = await plan(runner, scenario["prompt"])
        score = await judge(client, scenario["prompt"], itinerary)
        results.append(Result(scenario["id"], score, authors))
        print(scenario["id"], score.model_dump(exclude={"rationale"}), sorted(authors))
    report = "# Itinerary quality (LLM-as-judge)\n\n" + summarise(results) + "\n"
    (HERE / "results.md").write_text(report)
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
