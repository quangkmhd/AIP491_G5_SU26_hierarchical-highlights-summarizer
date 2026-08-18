from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def inspect_diagnostics(path: Path) -> dict[str, Any]:
    """Summarize one JSONL session without loading its audio samples."""
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)

    starts = [row for row in rows if row.get("event") == "session_start"]
    source = [row for row in rows if row.get("event") == "source_frame"]
    processed = [row for row in rows if row.get("event") == "processed_chunk"]
    vad = [row for row in rows if row.get("event") == "vad_segment"]
    asr = [row for row in rows if row.get("event") == "asr_result"]
    ends = [row for row in rows if row.get("event") == "session_end"]
    source_p90 = _percentile([float(row.get("rms", 0.0)) for row in source], 0.9)
    processed_p90 = _percentile([float(row.get("rms", 0.0)) for row in processed], 0.9)
    empty_count = sum(bool(row.get("empty")) for row in asr)
    empty_rate = empty_count / len(asr) if asr else 0.0
    attenuation_ratio = processed_p90 / source_p90 if source_p90 > 0 else 0.0

    if not source:
        suspected_stage = "capture_or_transport"
    elif source_p90 < 0.003:
        suspected_stage = "capture"
    elif processed and attenuation_ratio < 0.5:
        suspected_stage = "preprocessing"
    elif not vad:
        suspected_stage = "vad"
    elif not asr or empty_rate >= 0.5:
        suspected_stage = "asr"
    else:
        suspected_stage = "healthy_or_reference_needed"

    start = starts[-1] if starts else {}
    end = ends[-1] if ends else {}
    return {
        "path": str(path.resolve()),
        "session_id": start.get("session_id", rows[0].get("session_id") if rows else None),
        "suspected_stage": suspected_stage,
        "microphone_settings": start.get("microphone_settings", {}),
        "denoiser": start.get("denoiser"),
        "vad_config": start.get("vad", {}),
        "source_frames": len(source),
        "source_rms_p90": source_p90,
        "source_peak_max": max((float(row.get("peak", 0.0)) for row in source), default=0.0),
        "source_clipped_frames": sum(bool(row.get("clipped")) for row in source),
        "processed_chunks": len(processed),
        "processed_rms_p90": processed_p90,
        "preprocessing_rms_ratio": attenuation_ratio,
        "vad_segments": len(vad),
        "vad_speech_seconds": sum(float(row.get("duration_seconds", 0.0)) for row in vad),
        "asr_attempts": len(asr),
        "asr_empty_decodes": empty_count,
        "asr_empty_rate": empty_rate,
        "utterances": int(end.get("utterances", len(asr) - empty_count)),
        "accepted_samples": int(end.get("accepted_samples", 0)),
        "closed_cleanly": bool(ends),
    }


def latest_diagnostics(root: Path) -> Path:
    candidates = list(root.glob("*.diagnostics.jsonl"))
    if not candidates:
        raise FileNotFoundError(f"no diagnostics found in {root}")
    return max(candidates, key=lambda item: item.stat().st_mtime)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--recordings-root", type=Path, default=Path("data/recordings"))
    args = parser.parse_args(argv)
    path = args.path or latest_diagnostics(args.recordings_root)
    print(json.dumps(inspect_diagnostics(path), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
