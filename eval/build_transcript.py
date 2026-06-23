"""Build a header-prefixed transcript from a list of PairedSegment records.

The synthesized format is `Speaker_NNN (MM:SS.t - MM:SS.t): text` and is
identical to what tool 09's `parse_transcript` already accepts. Cumulative
timestamps come from each segment's `duration_sec` field.
"""

from __future__ import annotations

from typing import Literal

from eval.load_segments import PairedSegment


def _fmt_time(seconds: float) -> str:
    total = max(0.0, seconds)
    minutes = int(total // 60)
    secs = int(total - minutes * 60)
    return f"{minutes}:{secs:02d}"


def synthesize_transcript(
    pairs: list[PairedSegment],
    *,
    provider: Literal["sherpa", "soniox"],
) -> str:
    if not pairs:
        return ""
    lines: list[str] = []
    for pair in pairs:
        text = pair.sherpa_transcript if provider == "sherpa" else pair.soniox_transcript
        lines.append(text)
    return "\n".join(lines)
