"""Shared settings for every agent in the mesh."""
import os

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("MODEL", "gemini-2.5-flash")
FLIGHTS_PORT = int(os.getenv("FLIGHTS_PORT", "8001"))
HOTELS_PORT = int(os.getenv("HOTELS_PORT", "8002"))
ACTIVITIES_PORT = int(os.getenv("ACTIVITIES_PORT", "8003"))
