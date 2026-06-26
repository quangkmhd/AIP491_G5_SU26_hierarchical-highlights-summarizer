"""Pair Sherpa (raw ASR) JSON segments with Soniox (truth) JSON segments.

The pairing is by `(video_id, segment_number)`. Both directories are walked
recursively, files are sorted, and the two lists are zipped. Any mismatch
in count per video aborts the run with a `ValueError`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


_SEGMENT_FILE_RE = re.compile(r"^segment_(\d{3})_(sherpa|soniox)\.json$")


@dataclass(frozen=True)
class PairedSegment:
    video_id: str
    segment_number: int
    sherpa_transcript: str
    soniox_transcript: str
    duration_sec: float
    sherpa_tokens: list[str] = None
    sherpa_confidences: list[float] = None


def _scan_provider_dir(root: Path, provider: str) -> dict[tuple[str, int], dict]:
    if not root.exists():
        raise FileNotFoundError(f"Provider dir does not exist: {root}")
    out: dict[tuple[str, int], dict] = {}
    for json_path in sorted(root.rglob("*.json")):
        match = _SEGMENT_FILE_RE.match(json_path.name)
        if not match:
            continue
        seg_num = int(match.group(1))
        if match.group(2) != provider:
            continue
        video_id = json_path.parent.name
        out[(video_id, seg_num)] = json.loads(json_path.read_text(encoding="utf-8"))
    return out


def pair_sherpa_soniox(
    sherpa_dir: Path | str,
    soniox_dir: Path | str,
) -> list[PairedSegment]:
    sherpa_dir = Path(sherpa_dir)
    soniox_dir = Path(soniox_dir)
    sherpa_index = _scan_provider_dir(sherpa_dir, "sherpa")
    soniox_index = _scan_provider_dir(soniox_dir, "soniox")

    if set(sherpa_index.keys()) != set(soniox_index.keys()):
        only_sherpa = sorted(set(sherpa_index.keys()) - set(soniox_index.keys()))
        only_soniox = sorted(set(soniox_index.keys()) - set(sherpa_index.keys()))
        raise ValueError(
            f"Sherpa/Soniox segment mismatch: "
            f"only_sherpa={only_sherpa[:5]} only_soniox={only_soniox[:5]} "
            f"total_sherpa={len(sherpa_index)} total_soniox={len(soniox_index)}"
        )

    pairs: list[PairedSegment] = []
    for key in sorted(sherpa_index.keys()):
        video_id, seg_num = key
        sherpa_payload = sherpa_index[key]
        soniox_payload = soniox_index[key]
        pairs.append(
            PairedSegment(
                video_id=video_id,
                segment_number=seg_num,
                sherpa_transcript=str(sherpa_payload.get("transcript", "")),
                soniox_transcript=str(soniox_payload.get("transcript", "")),
                duration_sec=float(
                    (sherpa_payload.get("metadata", {}) or {}).get("duration_sec", 0.0)
                ),
                sherpa_tokens=sherpa_payload.get("tokens", []),
                sherpa_confidences=sherpa_payload.get("confidences", []),
            )
        )
    return pairs
