from pathlib import Path
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.sessions import router
from backend.db.database import DatabaseManager


class FakeLiveOrchestrator:
    def __init__(self) -> None:
        self.finalize_calls: list[str] = []

    async def finalize_live_session(self, session_id: str, progress_callback=None) -> dict:
        self.finalize_calls.append(session_id)
        return {"segments": [{"title": "Done"}]}


def build_client(tmp_path: Path):
    db = DatabaseManager(tmp_path / "pipeline.db")
    orchestrator = FakeLiveOrchestrator()
    app = FastAPI()
    app.state.db = db
    app.state.orchestrator = orchestrator
    app.include_router(router)
    return TestClient(app), db, orchestrator


def test_online_session_starts_recording_and_transition_is_conditional(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "pipeline.db")
    session = db.create_session(title="Live", meeting_type="online_live")

    assert session["status"] == "recording"
    assert db.transition_session_status(session["session_id"], "recording", "finalizing", 95.0)
    assert not db.transition_session_status(session["session_id"], "recording", "finalizing", 95.0)


def test_existing_database_status_constraint_is_migrated(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                audio_source TEXT,
                meeting_type TEXT CHECK(meeting_type IN ('offline_upload', 'online_live')) DEFAULT 'offline_upload',
                status TEXT CHECK(status IN ('created', 'diarizing', 'transcribing', 'summarizing', 'completed', 'failed')) DEFAULT 'created',
                progress_percentage REAL DEFAULT 0.0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO sessions (session_id, meeting_type, status)
            VALUES ('legacy', 'online_live', 'created');
            """
        )

    db = DatabaseManager(db_path)
    db.update_session_status("legacy", "recording", 0.0)

    assert db.get_session("legacy")["status"] == "recording"


def test_audio_upload_is_rejected_after_finalization_begins(tmp_path: Path) -> None:
    client, db, _ = build_client(tmp_path)
    session = db.create_session(title="Live", meeting_type="online_live")
    db.transition_session_status(session["session_id"], "recording", "finalizing", 95.0)

    response = client.post(
        f"/api/v1/sessions/{session['session_id']}/audio",
        files={"file": ("chunk.webm", b"audio", "audio/webm")},
    )

    assert response.status_code == 409


def test_finalize_is_idempotent_and_returns_saved_summary(tmp_path: Path) -> None:
    client, db, orchestrator = build_client(tmp_path)
    session = db.create_session(title="Live", meeting_type="online_live")
    url = f"/api/v1/sessions/{session['session_id']}/finalize"

    first = client.post(url)
    second = client.post(url)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["summary"] == {"segments": [{"title": "Done"}]}
    assert second.json()["summary"] == first.json()["summary"]
    assert orchestrator.finalize_calls == [session["session_id"]]
    assert db.get_session(session["session_id"])["status"] == "completed"
