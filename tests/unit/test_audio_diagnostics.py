from __future__ import annotations

import json
from pathlib import Path

from src.runtime.audio_diagnostics import inspect_diagnostics


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_inspector_attributes_strong_audio_without_segments_to_vad(tmp_path: Path) -> None:
    path = tmp_path / "session.diagnostics.jsonl"
    _write(path, [
        {"event": "session_start", "session_id": "s1", "microphone_settings": {"noise_suppression": True}},
        {"event": "source_frame", "rms": 0.02, "peak": 0.2, "clipped": False},
        {"event": "processed_chunk", "rms": 0.02, "peak": 0.2, "clipped": False},
        {"event": "session_end", "utterances": 0, "empty_decodes": 0},
    ])

    report = inspect_diagnostics(path)

    assert report["suspected_stage"] == "vad"
    assert report["source_rms_p90"] == 0.02
    assert report["vad_segments"] == 0


def test_inspector_attributes_most_empty_decodes_to_asr(tmp_path: Path) -> None:
    path = tmp_path / "session.diagnostics.jsonl"
    rows = [{"event": "source_frame", "rms": 0.03, "peak": 0.2, "clipped": False}]
    rows += [{"event": "vad_segment", "duration_seconds": 1.0}] * 4
    rows += [{"event": "asr_result", "empty": value} for value in (True, True, True, False)]
    _write(path, rows)

    report = inspect_diagnostics(path)

    assert report["suspected_stage"] == "asr"
    assert report["asr_empty_rate"] == 0.75
