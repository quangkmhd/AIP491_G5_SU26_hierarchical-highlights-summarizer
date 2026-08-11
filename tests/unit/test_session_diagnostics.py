from __future__ import annotations

import json
from pathlib import Path

from src.service.session_diagnostics import SessionDiagnostics


def test_session_diagnostics_writes_recoverable_json_lines(tmp_path: Path) -> None:
    path = tmp_path / "session-1.diagnostics.jsonl"
    diagnostics = SessionDiagnostics(path, "session-1")

    diagnostics.record("session_start", source_sample_rate=48_000, denoiser="passthrough")
    diagnostics.record("asr_result", text="", empty=True, asr_ms=12.5)
    diagnostics.close(retain=True, accepted_samples=4_800, utterances=0, empty_decodes=1)

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["event"] for row in rows] == ["session_start", "asr_result", "session_end"]
    assert all(row["session_id"] == "session-1" for row in rows)
    assert rows[1]["empty"] is True
    assert rows[-1]["accepted_samples"] == 4_800


def test_session_diagnostics_delete_file_when_recording_is_not_retained(tmp_path: Path) -> None:
    path = tmp_path / "session-2.diagnostics.jsonl"
    diagnostics = SessionDiagnostics(path, "session-2")
    diagnostics.record("session_start")

    diagnostics.close(retain=False)

    assert not path.exists()
