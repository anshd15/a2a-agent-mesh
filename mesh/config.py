"""Shared settings for every agent in the mesh."""
import os

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL", "gemini-2.5-flash")
HOST = os.getenv("HOST", "127.0.0.1")
FLIGHTS_PORT = int(os.getenv("FLIGHTS_PORT", "8001"))
HOTELS_PORT = int(os.getenv("HOTELS_PORT", "8002"))
ACTIVITIES_PORT = int(os.getenv("ACTIVITIES_PORT", "8003"))

# Public base URLs: what each agent card advertises and what the orchestrator dials.
# Override for containers / Cloud Run, e.g. FLIGHTS_URL=http://flights:8001
FLIGHTS_URL = os.getenv("FLIGHTS_URL", f"http://localhost:{FLIGHTS_PORT}")
HOTELS_URL = os.getenv("HOTELS_URL", f"http://localhost:{HOTELS_PORT}")
ACTIVITIES_URL = os.getenv("ACTIVITIES_URL", f"http://localhost:{ACTIVITIES_PORT}")

# How long the orchestrator waits on a remote specialist before giving up.
A2A_TIMEOUT_S = float(os.getenv("A2A_TIMEOUT_S", "120"))

# Specialists reuse an answer to an identical query for this long (0 disables caching).
SPECIALIST_CACHE_TTL_S = float(os.getenv("SPECIALIST_CACHE_TTL_S", "300"))
