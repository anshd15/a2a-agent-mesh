"""Start every specialist agent as a subprocess (works on Windows, macOS and Linux)."""
import subprocess
import sys

AGENTS = ["mesh.agents.flights", "mesh.agents.hotels", "mesh.agents.activities"]


def main() -> None:
    procs = [subprocess.Popen([sys.executable, "-m", mod]) for mod in AGENTS]
    print(f"Started {len(procs)} agents on :8001-8003. Ctrl+C to stop.")
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    main()
