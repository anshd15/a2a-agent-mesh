"""LLM-as-judge: run each scenario through the trip planner and score the itinerary.

    python eval/judge.py --runs 3    # needs GOOGLE_API_KEY and the specialists running

Alongside the judge's 1-5 scores, a deterministic "delegation" metric records which
specialists the planner actually called. LLM runs are noisy, so --runs repeats every
scenario and the report shows the spread (stdev) next to the mean. Writes eval/results.md.
"""
import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

from google import genai
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

from mesh.config import MODEL
from mesh.orchestrator.prompts import load_prompt

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
    columns_values = list(zip(*(_row(r) for r in results)))
    lines.append("| **average** | "
                 + " | ".join(f"**{mean(c):.2f}**" for c in columns_values) + " |")
    if len(results) > 1:
        lines.append("| *stdev* | "
                     + " | ".join(f"*{pstdev(c):.2f}*" for c in columns_values) + " |")
    return "\n".join([header, *lines])


async def plan(runner: InMemoryRunner, prompt: str) -> tuple[str, set[str]]:
    """Run one request; return the final text and every agent it reached.

    Specialists are AgentTools, so they show up as tool calls named after the agent;
    event authors are kept too, for agents that answer as sub-agents.
    """
    session = await runner.session_service.create_session(app_name=runner.app_name,
                                                          user_id="judge")
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    final, reached = "", set()
    async for event in runner.run_async(user_id="judge", session_id=session.id,
                                        new_message=message):
        reached.add(event.author)
        parts = event.content.parts if event.content and event.content.parts else []
        reached.update(p.function_call.name for p in parts if p.function_call)
        if event.is_final_response() and parts:
            final = "".join(p.text or "" for p in parts)
    return final, reached


async def judge(client: genai.Client, prompt: str, itinerary: str) -> Score:
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=f"{RUBRIC}\n\nTraveller request:\n{prompt}\n\nItinerary:\n{itinerary}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=Score, temperature=0
        ),
    )
    return Score.model_validate_json(response.text)


async def main(runs: int) -> None:
    from mesh.orchestrator.agent import root_agent

    runner = InMemoryRunner(agent=root_agent)
    client = genai.Client()
    results = []
    for scenario in load_scenarios():
        for run in range(1, runs + 1):
            label = scenario["id"] if runs == 1 else f"{scenario['id']} #{run}"
            itinerary, authors = await plan(runner, scenario["prompt"])
            score = await judge(client, scenario["prompt"], itinerary)
            results.append(Result(label, score, authors))
            print(label, score.model_dump(exclude={"rationale"}), sorted(authors))
    report = (f"# Itinerary quality (LLM-as-judge, {MODEL}, prompt "
              f"{load_prompt('planner').tag}, {runs} run(s) per scenario)\n\n"
              + summarise(results) + "\n")
    (HERE / "results.md").write_text(report)
    print(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=1, help="repeats per scenario")
    asyncio.run(main(parser.parse_args().runs))
