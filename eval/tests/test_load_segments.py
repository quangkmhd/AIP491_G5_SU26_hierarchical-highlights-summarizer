"""Tests for the Sherpa/Soniox segment loader."""

import json
from pathlib import Path

import pytest

from eval.load_segments import PairedSegment, pair_sherpa_soniox


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_segment(video_id: str, segment_number: int, provider: str, transcript: str, duration: float = 1.0) -> dict:
    return {
        "metadata": {
            "file_id": f"{video_id}_{segment_number:03d}",
            "source_file": f"segment_{segment_number:03d}.wav",
            "duration_sec": duration,
            "model": provider,
        },
        "transcript": transcript,
    }


def test_loader_pairs_by_video_and_segment(tmp_path: Path):
    sherpa_dir = tmp_path / "sherpa"
    soniox_dir = tmp_path / "soniox"
    for video in ("vid01", "vid02"):
        for seg in (0, 1, 2):
            _write_json(sherpa_dir / video / f"segment_{seg:03d}_sherpa.json",
                        _make_segment(video, seg, "sherpa", f"raw {seg}"))
            _write_json(soniox_dir / video / f"segment_{seg:03d}_soniox.json",
                        _make_segment(video, seg, "soniox", f"truth {seg}"))

    pairs = pair_sherpa_soniox(sherpa_dir, soniox_dir)
    assert len(pairs) == 6
    keys = {(p.video_id, p.segment_number) for p in pairs}
    assert keys == {("vid01", 0), ("vid01", 1), ("vid01", 2),
                    ("vid02", 0), ("vid02", 1), ("vid02", 2)}


def test_loader_raises_on_count_mismatch(tmp_path: Path):
    sherpa_dir = tmp_path / "sherpa"
    soniox_dir = tmp_path / "soniox"
    _write_json(sherpa_dir / "vid01" / "segment_000_sherpa.json",
                _make_segment("vid01", 0, "sherpa", "raw 0"))
    _write_json(sherpa_dir / "vid01" / "segment_001_sherpa.json",
                _make_segment("vid01", 1, "sherpa", "raw 1"))
    _write_json(soniox_dir / "vid01" / "segment_000_soniox.json",
                _make_segment("vid01", 0, "soniox", "truth 0"))

    with pytest.raises(ValueError, match="mismatch"):
        pair_sherpa_soniox(sherpa_dir, soniox_dir)


def test_loader_sorts_within_video(tmp_path: Path):
    sherpa_dir = tmp_path / "sherpa"
    soniox_dir = tmp_path / "soniox"
    for seg in (2, 0, 1):
        _write_json(sherpa_dir / "vid01" / f"segment_{seg:03d}_sherpa.json",
                    _make_segment("vid01", seg, "sherpa", f"raw {seg}"))
        _write_json(soniox_dir / "vid01" / f"segment_{seg:03d}_soniox.json",
                    _make_segment("vid01", seg, "soniox", f"truth {seg}"))

    pairs = pair_sherpa_soniox(sherpa_dir, soniox_dir)
    segment_numbers = [p.segment_number for p in pairs]
    assert segment_numbers == [0, 1, 2]


def test_paired_segment_dataclass_carries_both_transcripts():
    p = PairedSegment(
        video_id="vid01",
        segment_number=0,
        sherpa_transcript="raw",
        soniox_transcript="truth",
        duration_sec=1.5,
    )
    assert p.sherpa_transcript == "raw"
    assert p.soniox_transcript == "truth"
    assert p.duration_sec == 1.5
