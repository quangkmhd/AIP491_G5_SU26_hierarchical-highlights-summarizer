from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from src.service.demo_timeline import Custom10hTimeline


def _write_wav(
    path: Path,
    sample_count: int,
    *,
    channels: int = 1,
    sample_rate: int = 16_000,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(b"\x00\x00" * sample_count * channels)


def _write_manifest(data_dir: Path, rows: list[dict[str, object]]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest = data_dir / "recordings.jsonl"
    manifest.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _row(recording_id: str, source: str, sample_count: int) -> dict[str, object]:
    return {
        "id": recording_id,
        "sources": [{"type": "file", "channels": [0], "source": source}],
        "sampling_rate": 16_000,
        "num_samples": sample_count,
        "duration": sample_count / 16_000,
    }


def make_custom10h_fixture(
    tmp_path: Path,
    recordings: list[tuple[str, int]],
) -> Path:
    data_dir = tmp_path / "Custom_10h"
    rows: list[dict[str, object]] = []
    for recording_id, sample_count in recordings:
        relative_path = f"wavs/{recording_id}.wav"
        _write_wav(data_dir / relative_path, sample_count)
        rows.append(_row(recording_id, relative_path, sample_count))
    _write_manifest(data_dir, rows)
    return data_dir


def make_invalid_fixture(tmp_path: Path, fixture_kind: str) -> Path:
    data_dir = tmp_path / "Custom_10h"
    valid_path = data_dir / "wavs/valid.wav"
    _write_wav(valid_path, 1_600)

    if fixture_kind == "duplicate-id":
        second_path = data_dir / "wavs/duplicate.wav"
        _write_wav(second_path, 1_600)
        rows = [
            _row("same-id", "wavs/valid.wav", 1_600),
            _row("same-id", "wavs/duplicate.wav", 1_600),
        ]
    elif fixture_kind == "stereo":
        _write_wav(valid_path, 1_600, channels=2)
        rows = [_row("stereo", "wavs/valid.wav", 1_600)]
    elif fixture_kind == "wrong-rate":
        _write_wav(valid_path, 1_600, sample_rate=8_000)
        rows = [_row("wrong-rate", "wavs/valid.wav", 1_600)]
    elif fixture_kind == "escaping-path":
        outside = tmp_path / "outside.wav"
        _write_wav(outside, 1_600)
        rows = [_row("escaping", "../outside.wav", 1_600)]
    else:  # pragma: no cover - protects the test helper itself
        raise AssertionError(f"unknown fixture kind: {fixture_kind}")

    _write_manifest(data_dir, rows)
    return data_dir


def test_build_preserves_jsonl_order_and_never_overlaps(tmp_path: Path) -> None:
    data_dir = make_custom10h_fixture(
        tmp_path,
        [("z-first_00001", 1_600), ("a-second_00002", 3_200), ("m-third_00003", 1_600)],
    )

    timeline = Custom10hTimeline.build(
        data_dir=data_dir,
        duration_seconds=1.0,
        gap_seconds=0.1,
    )

    assert [item.recording_id for item in timeline.items] == [
        "z-first_00001",
        "a-second_00002",
        "m-third_00003",
    ]
    assert [(item.start_sample, item.end_sample) for item in timeline.items] == [
        (0, 1_600),
        (3_200, 6_400),
        (8_000, 9_600),
    ]
    assert timeline.total_samples == 16_000
    assert timeline.padding_samples == 4_800


@pytest.mark.parametrize(
    ("fixture_kind", "message"),
    [
        ("duplicate-id", "duplicate recording id"),
        ("stereo", "must be mono"),
        ("wrong-rate", "expected 16000"),
        ("escaping-path", "outside Custom_10h"),
    ],
)
def test_build_rejects_invalid_corpus_rows(
    tmp_path: Path,
    fixture_kind: str,
    message: str,
) -> None:
    data_dir = make_invalid_fixture(tmp_path, fixture_kind)
    with pytest.raises(ValueError, match=message):
        Custom10hTimeline.build(data_dir, duration_seconds=1.0, gap_seconds=0.1)


def test_build_skips_instead_of_truncating_the_first_wav_that_cannot_fit(
    tmp_path: Path,
) -> None:
    data_dir = make_custom10h_fixture(
        tmp_path,
        [("fits_00001", 8_000), ("too-long_00002", 12_000)],
    )

    timeline = Custom10hTimeline.build(
        data_dir,
        duration_seconds=1.0,
        gap_seconds=0.1,
    )

    assert [item.recording_id for item in timeline.items] == ["fits_00001"]
    assert timeline.items[0].sample_count == 8_000
    assert timeline.total_samples == 16_000


def test_resolve_and_write_are_limited_to_prepared_timeline(tmp_path: Path) -> None:
    data_dir = make_custom10h_fixture(tmp_path, [("only_00001", 8_000)])
    timeline = Custom10hTimeline.build(
        data_dir,
        duration_seconds=1.0,
        gap_seconds=0.1,
    )

    assert timeline.resolve_audio("only_00001").is_file()
    with pytest.raises(KeyError, match="unknown recording id"):
        timeline.resolve_audio("missing_00002")

    output = timeline.write_wav(tmp_path / "timeline.wav")
    with wave.open(str(output), "rb") as stream:
        assert stream.getnchannels() == 1
        assert stream.getframerate() == 16_000
        assert stream.getnframes() == 16_000


def test_manifest_uses_relative_paths_and_reproducible_hashes(tmp_path: Path) -> None:
    data_dir = make_custom10h_fixture(tmp_path, [("only_00001", 8_000)])
    timeline = Custom10hTimeline.build(
        data_dir,
        duration_seconds=1.0,
        gap_seconds=0.1,
    )

    payload = timeline.manifest_payload()

    assert payload["sample_rate"] == 16_000
    assert payload["duration_samples"] == 16_000
    assert payload["items"][0]["relative_path"] == "wavs/only_00001.wav"
    assert str(tmp_path) not in json.dumps(payload)
    assert len(payload["recordings_manifest_sha256"]) == 64
    assert len(payload["items"][0]["sha256"]) == 64
