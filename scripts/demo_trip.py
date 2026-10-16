"""Run one trip request end to end from the terminal and show what it cost.

    python scripts/demo_trip.py "Mumbai to Goa, 2026-12-20 to 2026-12-23, 600 USD, beaches"
"""
import asyncio
import sys

from google.adk.runners import InMemoryRunner
from google.genai import types

from mesh.orchestrator.agent import root_agent


async def main(prompt: str) -> None:
    runner = InMemoryRunner(agent=root_agent)
    session = await runner.session_service.create_session(app_name=runner.app_name,
                                                          user_id="demo")
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    async for event in runner.run_async(user_id="demo", session_id=session.id,
                                        new_message=message):
        text = "".join(p.text or "" for p in (event.content.parts if event.content else []))
        if text:
            print(f"[{event.author}] {text}\n")
    session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id="demo", session_id=session.id
    )
    print("usage:", session.state.get("usage"))


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "Plan 3 days in Goa from Mumbai, 600 USD"))
