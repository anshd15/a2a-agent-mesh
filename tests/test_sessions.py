"""Sessions written through the SQLite URI used by `make web` survive a restart."""
from google.adk.sessions import DatabaseSessionService


async def test_trip_brief_survives_service_restart(tmp_path):
    uri = f"sqlite+aiosqlite:///{(tmp_path / 'sessions.db').as_posix()}"
    first = DatabaseSessionService(db_url=uri)
    session = await first.create_session(
        app_name="orchestrator", user_id="u1", state={"trip": {"destination": "Goa"}}
    )
    second = DatabaseSessionService(db_url=uri)  # fresh process, same file
    restored = await second.get_session(app_name="orchestrator", user_id="u1",
                                        session_id=session.id)
    assert restored is not None and restored.state["trip"]["destination"] == "Goa"
