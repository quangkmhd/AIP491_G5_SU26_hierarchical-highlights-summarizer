from pathlib import Path

from backend.db.database import DatabaseManager


def test_get_summary_returns_last_snapshot_when_writes_share_timestamp(
    tmp_path: Path,
) -> None:
    db = DatabaseManager(tmp_path / "pipeline.sqlite3")
    session = db.create_session(meeting_type="online_live")
    session_id = session["session_id"]

    db.save_summary(session_id, {"segments": [{"title": "old"}]})
    db.save_summary(session_id, {"segments": [{"title": "new"}]})

    assert db.get_summary(session_id)["hierarchical_json"] == {
        "segments": [{"title": "new"}]
    }
