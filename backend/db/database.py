"""SQLite Database Manager for Session State & Persistence."""

import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "pipeline.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


class DatabaseManager:
    """Synchronous & Async-compatible SQLite manager for pipeline state management."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create a sqlite3 connection with Row factory enabled."""
        conn = sqlite3.connect(self.db_path, timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Initialize database schema from schema.sql DDL."""
        if not SCHEMA_PATH.is_file():
            logger.error(f"Schema file not found at {SCHEMA_PATH}")
            return

        with self.get_connection() as conn:
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    # -------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------
    def create_session(
        self,
        title: Optional[str] = None,
        audio_source: Optional[str] = None,
        session_id: Optional[str] = None,
        meeting_type: str = "offline_upload",
    ) -> dict[str, Any]:
        """Create a new processing session."""
        sid = session_id or str(uuid4())
        session_title = title or f"Meeting Session {sid[:8]}"
        source = audio_source or "upload"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (session_id, title, audio_source, meeting_type, status, progress_percentage)
                VALUES (?, ?, ?, ?, 'created', 0.0)
                """,
                (sid, session_title, source, meeting_type),
            )
            conn.commit()

        return self.get_session(sid)

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Query a session by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_all_sessions(self) -> list[dict[str, Any]]:
        """List all meeting sessions ordered by creation date."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_session_status(
        self, session_id: str, status: str, progress: float
    ) -> None:
        """Update session execution status and progress percentage."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET status = ?, progress_percentage = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (status, progress, session_id),
            )
            conn.commit()

    def fail_session(self, session_id: str, error_message: str) -> None:
        """Mark a session as failed with an error message."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET status = 'failed', error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (error_message, session_id),
            )
            conn.commit()

    # -------------------------------------------------------------
    # Utterance & Summary Management
    # -------------------------------------------------------------
    def add_utterance(
        self,
        session_id: str,
        speaker_id: str,
        text: str,
        utterance_index: int,
        start_time: float,
        end_time: float,
        has_overlap: bool = False,
    ) -> dict[str, Any]:
        """Record a single transcribed utterance."""
        uid = str(uuid4())
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO utterances (utterance_id, session_id, speaker_id, text, utterance_index, start_time, end_time, has_overlap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    session_id,
                    speaker_id,
                    text,
                    utterance_index,
                    start_time,
                    end_time,
                    1 if has_overlap else 0,
                ),
            )
            conn.commit()

        return {
            "utterance_id": uid,
            "session_id": session_id,
            "speaker_id": speaker_id,
            "text": text,
            "utterance_index": utterance_index,
            "start_time": start_time,
            "end_time": end_time,
            "has_overlap": has_overlap,
        }

    def get_utterances(self, session_id: str) -> list[dict[str, Any]]:
        """Retrieve all transcribed utterances for a session in order."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM utterances
                WHERE session_id = ?
                ORDER BY utterance_index ASC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def save_summary(
        self,
        session_id: str,
        hierarchical_summary: dict[str, Any],
        processing_time_ms: Optional[int] = None,
    ) -> str:
        """Store final LLM hierarchical summary JSON."""
        summary_id = str(uuid4())
        json_str = json.dumps(hierarchical_summary, ensure_ascii=False)

        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO summaries (summary_id, session_id, hierarchical_json, processing_time_ms)
                VALUES (?, ?, ?, ?)
                """,
                (summary_id, session_id, json_str, processing_time_ms),
            )
            conn.commit()

        return summary_id

    def get_summary(self, session_id: str) -> Optional[dict[str, Any]]:
        """Fetch final LLM summary JSON for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM summaries WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            )
            row = cursor.fetchone()
            if row:
                res = dict(row)
                res["hierarchical_json"] = json.loads(res["hierarchical_json"])
                return res
        return None
