from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.runtime.demo_recorder import (
    DemoRecordingError,
    build_ffmpeg_command,
    playback_pauses_from_trace,
    preserve_partial_artifacts,
    validate_completion,
    validate_ffprobe,
    validate_free_space,
)
from src.service.demo_timeline import PlaybackPause


def test_ffmpeg_command_delays_audio_and_keeps_video_postroll(tmp_path: Path) -> None:
    command = build_ffmpeg_command(
        webm=tmp_path / "raw.webm",
        wav=tmp_path / "timeline.wav",
        audio_delay_ms=2_300,
        output=tmp_path / "demo.mp4",
    )

    assert command[:2] == ["ffmpeg", "-y"]
    assert any("adelay=2300:all=1,apad" in part for part in command)
    assert command[command.index("-c:v"):command.index("-c:v") + 2] == [
        "-c:v",
        "libx264",
    ]
    assert command[command.index("-c:a"):command.index("-c:a") + 2] == [
        "-c:a",
        "aac",
    ]
    assert command[-1] == str(tmp_path / "demo.mp4")


@pytest.mark.parametrize(
    ("completion", "message"),
    [
        ({"sessionClosed": True, "meetingCompleted": False}, "meeting-completed"),
        ({"sessionClosed": False, "meetingCompleted": True}, "session_closed"),
        ({"sessionClosed": True, "meetingCompleted": True, "error": "boom"}, "boom"),
    ],
)
def test_run_requires_both_completion_events_and_no_trace_error(
    completion: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(DemoRecordingError, match=message):
        validate_completion(completion)


def test_validate_free_space_requires_eight_gib(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        shutil,
        "disk_usage",
        lambda _: SimpleNamespace(free=7 * 1024**3),
    )
    with pytest.raises(DemoRecordingError, match="8 GiB"):
        validate_free_space(tmp_path)


@pytest.mark.parametrize(
    "streams",
    [[], [{"codec_type": "video"}], [{"codec_type": "audio"}]],
)
def test_validate_probe_requires_audio_and_video(streams: list[dict[str, object]]) -> None:
    with pytest.raises(DemoRecordingError, match="audio and video"):
        validate_ffprobe({"streams": streams, "format": {"duration": "5.0"}})


def test_validate_probe_requires_expected_codecs_and_dimensions() -> None:
    probe = {
        "streams": [
            {"codec_type": "video", "codec_name": "vp9", "width": 1280, "height": 720},
            {"codec_type": "audio", "codec_name": "opus"},
        ],
        "format": {"duration": "5.0"},
    }

    with pytest.raises(DemoRecordingError, match="H.264 1920x1080"):
        validate_ffprobe(probe)


def test_trace_pauses_are_converted_to_sample_offsets() -> None:
    pauses = playback_pauses_from_trace(
        [{"after_sample": 3_200, "duration_ms": 250}],
        sample_rate=16_000,
    )

    assert pauses == [PlaybackPause(after_sample=3_200, duration_samples=4_000)]


def test_failed_run_keeps_existing_evidence(tmp_path: Path) -> None:
    partial = tmp_path / "raw.webm"
    partial.write_bytes(b"partial-video")

    preserve_partial_artifacts(tmp_path)

    assert partial.read_bytes() == b"partial-video"
