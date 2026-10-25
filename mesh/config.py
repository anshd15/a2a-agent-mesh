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

# Max requests a specialist runs at once; extra requests queue (protects LLM quotas).
MAX_CONCURRENCY = int(os.getenv("MAX_CONCURRENCY", "4"))

# Attempts per request for transient errors (timeouts, dropped connections); 1 disables.
RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "2"))

# Per-request limit on a specialist handler (seconds, 0 disables); keep below A2A_TIMEOUT_S
# so a hung LLM call is retried or degraded before the planner gives up on the specialist.
HANDLER_TIMEOUT_S = float(os.getenv("HANDLER_TIMEOUT_S", "60"))

# Shared bearer token between planner and specialists; unset disables auth (local dev).
MESH_TOKEN = os.getenv("MESH_TOKEN") or None

# Per-session spend cap for the planner's model calls, in USD (0 disables).
MAX_SESSION_COST_USD = float(os.getenv("MAX_SESSION_COST_USD", "0.50"))
