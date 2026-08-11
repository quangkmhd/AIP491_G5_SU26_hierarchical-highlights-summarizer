"""Record the Custom_10h browser demo and mux deterministic playback audio."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from src.config.asr import AsrConfig
from src.service.demo_timeline import Custom10hTimeline, PlaybackPause

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DATA_DIR = _PROJECT_ROOT / "training-eval-suite" / "data" / "Custom_10h"
_MIN_FREE_BYTES = 8 * 1024**3


class DemoRecordingError(RuntimeError):
    """Raised when a demo recording cannot satisfy its evidence gates."""


@dataclass(frozen=True, slots=True)
class RecorderConfig:
    data_dir: Path
    duration_seconds: float
    output: Path
    gap_seconds: float = 0.65
    width: int = 1920
    height: int = 1080
    finalization_timeout_seconds: float = 90.0


@dataclass(frozen=True, slots=True)
class DemoRunResult:
    run_dir: Path
    mp4: Path
    webm: Path
    wav: Path
    ffprobe: Path
    manifest: Path


def build_ffmpeg_command(
    *,
    webm: Path,
    wav: Path,
    audio_delay_ms: int,
    output: Path,
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(webm),
        "-i",
        str(wav),
        "-filter_complex",
        f"[1:a]adelay={max(0, audio_delay_ms)}:all=1,apad[a]",
        "-map",
        "0:v:0",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-shortest",
        str(output),
    ]


def validate_completion(trace: Mapping[str, object]) -> None:
    error = trace.get("error")
    if error:
        raise DemoRecordingError(f"browser demo failed: {error}")
    if trace.get("meetingCompleted") is not True:
        raise DemoRecordingError("browser trace is missing meeting-completed")
    if trace.get("sessionClosed") is not True:
        raise DemoRecordingError("browser trace is missing session_closed")


def validate_free_space(path: Path) -> None:
    probe_path = path if path.exists() else path.parent
    free = shutil.disk_usage(probe_path).free
    if free < _MIN_FREE_BYTES:
        raise DemoRecordingError(
            f"at least 8 GiB free space is required; found {free / 1024**3:.2f} GiB"
        )


def validate_ffprobe(payload: Mapping[str, object]) -> None:
    streams = payload.get("streams")
    if not isinstance(streams, list):
        raise DemoRecordingError("FFprobe output must contain audio and video streams")
    video = next(
        (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "video"),
        None,
    )
    audio = next(
        (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "audio"),
        None,
    )
    if video is None or audio is None:
        raise DemoRecordingError("MP4 must contain audio and video streams")
    if (
        video.get("codec_name") != "h264"
        or video.get("width") != 1920
        or video.get("height") != 1080
    ):
        raise DemoRecordingError("video stream must be H.264 1920x1080")
    if audio.get("codec_name") != "aac":
        raise DemoRecordingError("audio stream must use AAC")
    format_payload = payload.get("format")
    if not isinstance(format_payload, dict):
        raise DemoRecordingError("FFprobe output is missing format duration")
    try:
        duration = float(format_payload.get("duration", 0))
    except (TypeError, ValueError) as exc:
        raise DemoRecordingError("FFprobe duration is invalid") from exc
    if duration <= 0:
        raise DemoRecordingError("MP4 duration must be positive")


def playback_pauses_from_trace(
    pauses: Sequence[Mapping[str, object]],
    *,
    sample_rate: int,
) -> list[PlaybackPause]:
    result: list[PlaybackPause] = []
    for pause in pauses:
        try:
            after_sample = int(pause["after_sample"])
            duration_ms = float(pause["duration_ms"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DemoRecordingError("browser pause trace is invalid") from exc
        if after_sample < 0 or duration_ms < 0:
            raise DemoRecordingError("browser pause trace cannot contain negative values")
        result.append(
            PlaybackPause(
                after_sample=after_sample,
                duration_samples=round(duration_ms * sample_rate / 1000),
            )
        )
    return result


def preserve_partial_artifacts(run_dir: Path) -> tuple[Path, ...]:
    """Return existing evidence paths; recording failures never delete them."""
    if not run_dir.exists():
        return ()
    return tuple(sorted(path for path in run_dir.rglob("*") if path.is_file()))


def record_demo(config: RecorderConfig) -> DemoRunResult:
    output = config.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    validate_free_space(output.parent)
    _validate_preflight(config)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output.parent / f"{output.stem}-{timestamp}"
    run_dir.mkdir(parents=False, exist_ok=False)
    backend_log_path = run_dir / "backend.log"
    browser_log_path = run_dir / "browser.jsonl"
    manifest_path = run_dir / "manifest.json"
    trace_path = run_dir / "browser-trace.json"
    raw_webm = run_dir / "raw.webm"
    timeline_wav = run_dir / "timeline.wav"
    ffprobe_path = run_dir / "ffprobe.json"
    run_summary_path = run_dir / "run-summary.json"

    timeline = Custom10hTimeline.build(
        config.data_dir,
        duration_seconds=config.duration_seconds,
        gap_seconds=config.gap_seconds,
    )
    _write_json(manifest_path, timeline.manifest_payload())
    _run_checked(["pnpm", "--dir", "frontend", "build"], cwd=_PROJECT_ROOT)

    port = _find_free_port()
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(_PROJECT_ROOT),
            "DEMO_ENABLED": "true",
            "DEMO_DATA_DIR": str(config.data_dir.resolve()),
            "DEMO_DURATION_SECONDS": str(config.duration_seconds),
            "DEMO_GAP_SECONDS": str(config.gap_seconds),
        }
    )
    server: subprocess.Popen[str] | None = None
    trace: dict[str, Any] | None = None

    try:
        with backend_log_path.open("w", encoding="utf-8") as backend_log:
            server = subprocess.Popen(
                [
                    str(_PROJECT_ROOT / ".venv" / "bin" / "python"),
                    "-m",
                    "uvicorn",
                    "src.runtime.api:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=_PROJECT_ROOT,
                env=environment,
                stdout=backend_log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            _wait_for_health(port, server, timeout_seconds=180)
            trace = _record_browser(
                port=port,
                run_dir=run_dir,
                raw_webm=raw_webm,
                browser_log_path=browser_log_path,
                config=config,
            )
    except Exception as exc:
        preserve_partial_artifacts(run_dir)
        if isinstance(exc, DemoRecordingError):
            raise
        raise DemoRecordingError(f"demo recording failed: {exc}") from exc
    finally:
        if server is not None:
            _stop_server(server)

    if trace is None:
        raise DemoRecordingError("browser did not produce a demo trace")
    _write_json(trace_path, trace)
    validate_completion(trace)
    pauses_payload = trace.get("pauses", [])
    if not isinstance(pauses_payload, list):
        raise DemoRecordingError("browser pause trace must be a list")
    pauses = playback_pauses_from_trace(pauses_payload, sample_rate=16_000)
    timeline.write_wav(timeline_wav, pauses=pauses)

    playback_started = _required_number(trace, "playbackStartedEpochMs")
    video_started = _required_number(trace, "videoStartedEpochMs")
    audio_delay_ms = max(0, round(playback_started - video_started))
    _run_checked(
        build_ffmpeg_command(
            webm=raw_webm,
            wav=timeline_wav,
            audio_delay_ms=audio_delay_ms,
            output=output,
        ),
        cwd=_PROJECT_ROOT,
    )
    probe = _probe_media(output)
    validate_ffprobe(probe)
    _write_json(ffprobe_path, probe)
    _write_json(
        run_summary_path,
        {
            "schema_version": 1,
            "output": str(output),
            "duration_seconds_requested": config.duration_seconds,
            "audio_delay_ms": audio_delay_ms,
            "recording_count": len(timeline.items),
            "source_samples": timeline.total_samples,
            "pause_count": len(pauses),
            "utterance_count": trace.get("utteranceCount", 0),
            "recap_segment_count": trace.get("recapSegmentCount", 0),
            "recap_chunk_count": trace.get("recapChunkCount", 0),
            "trace": trace,
            "artifacts": {
                "mp4": _artifact_payload(output),
                "webm": _artifact_payload(raw_webm),
                "wav": _artifact_payload(timeline_wav),
                "manifest": _artifact_payload(manifest_path),
                "ffprobe": _artifact_payload(ffprobe_path),
                "browser_log": _artifact_payload(browser_log_path),
                "backend_log": _artifact_payload(backend_log_path),
            },
        },
    )
    return DemoRunResult(
        run_dir=run_dir,
        mp4=output,
        webm=raw_webm,
        wav=timeline_wav,
        ffprobe=ffprobe_path,
        manifest=manifest_path,
    )


def _record_browser(
    *,
    port: int,
    run_dir: Path,
    raw_webm: Path,
    browser_log_path: Path,
    config: RecorderConfig,
) -> dict[str, Any]:
    trace: dict[str, Any] | None = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": config.width, "height": config.height},
            record_video_dir=str(run_dir / "playwright"),
            record_video_size={"width": config.width, "height": config.height},
        )
        page = context.new_page()
        video = page.video
        if video is None:
            context.close()
            browser.close()
            raise DemoRecordingError("Playwright did not attach a video recorder")
        video_started_epoch_ms = time.time() * 1000
        with browser_log_path.open("w", encoding="utf-8") as browser_log:
            page.on(
                "console",
                lambda message: _write_jsonl(
                    browser_log,
                    {"type": message.type, "text": message.text},
                ),
            )
            page.on(
                "pageerror",
                lambda error: _write_jsonl(
                    browser_log,
                    {"type": "pageerror", "text": str(error)},
                ),
            )
            try:
                page.goto(f"http://127.0.0.1:{port}/?demo=custom10h")
                page.get_by_role("button", name="Bắt đầu demo").click(timeout=15_000)
                timeout_ms = int(
                    (
                        config.duration_seconds
                        + config.finalization_timeout_seconds
                        + 30
                    )
                    * 1000
                )
                page.wait_for_function(
                    "document.body.dataset.demoState === 'completed'",
                    timeout=timeout_ms,
                )
                evaluated = page.evaluate("window.__vietAsrDemoTrace")
                if not isinstance(evaluated, dict):
                    raise DemoRecordingError("browser did not expose a valid demo trace")
                trace = evaluated
                trace["videoStartedEpochMs"] = video_started_epoch_ms
            except PlaywrightError as exc:
                page.screenshot(path=str(run_dir / "failure.png"), full_page=True)
                raise DemoRecordingError(f"Playwright recording failed: {exc}") from exc
            finally:
                context.close()
            video.save_as(str(raw_webm))
        browser.close()
    if trace is None:
        raise DemoRecordingError("browser recording completed without a trace")
    return trace


def _validate_preflight(config: RecorderConfig) -> None:
    if config.duration_seconds <= 0 or config.duration_seconds > 3600:
        raise DemoRecordingError("duration_seconds must be in the range (0, 3600]")
    if config.width != 1920 or config.height != 1080:
        raise DemoRecordingError("demo evidence must be recorded at 1920x1080")
    for executable in ("pnpm", "ffmpeg", "ffprobe"):
        if shutil.which(executable) is None:
            raise DemoRecordingError(f"required executable is missing: {executable}")
    if not config.data_dir.is_dir():
        raise DemoRecordingError(f"Custom_10h data directory is missing: {config.data_dir}")
    asr = AsrConfig(_env_file=None)
    for model_path in (asr.encoder, asr.decoder, asr.joiner, asr.tokens, asr.silero_vad, asr.speaker_embed):
        if not Path(model_path).is_file():
            raise DemoRecordingError(f"required model file is missing: {model_path}")


def _wait_for_health(
    port: int,
    server: subprocess.Popen[str],
    *,
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise DemoRecordingError(f"backend exited before health check ({server.returncode})")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.25)
    raise DemoRecordingError("backend did not become healthy within 180 seconds")


def _stop_server(server: subprocess.Popen[str]) -> None:
    if server.poll() is not None:
        return
    server.terminate()
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=5)


def _run_checked(command: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        output = (exc.stdout or "").strip()
        raise DemoRecordingError(
            f"command failed ({' '.join(command)}): {output[-4000:]}"
        ) from exc


def _probe_media(path: Path) -> dict[str, Any]:
    completed = _run_checked(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        cwd=_PROJECT_ROOT,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DemoRecordingError("FFprobe returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise DemoRecordingError("FFprobe returned a non-object payload")
    return payload


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
        stream.bind(("127.0.0.1", 0))
        return int(stream.getsockname()[1])


def _required_number(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise DemoRecordingError(f"browser trace is missing numeric {key}")
    return float(value)


def _artifact_payload(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(stream: Any, payload: object) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    stream.flush()


def _parse_args(argv: Sequence[str] | None = None) -> RecorderConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    parser.add_argument("--duration-seconds", type=float, default=3600.0)
    parser.add_argument("--gap-seconds", type=float, default=0.65)
    parser.add_argument(
        "--output",
        type=Path,
        default=_PROJECT_ROOT / "outputs" / "demo" / "custom10h-realtime-1h.mp4",
    )
    args = parser.parse_args(argv)
    return RecorderConfig(
        data_dir=args.data_dir,
        duration_seconds=args.duration_seconds,
        gap_seconds=args.gap_seconds,
        output=args.output,
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = record_demo(_parse_args(argv))
    except DemoRecordingError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(result.mp4)
    print(result.run_dir)
    return 0


__all__ = [
    "DemoRecordingError",
    "DemoRunResult",
    "RecorderConfig",
    "build_ffmpeg_command",
    "main",
    "playback_pauses_from_trace",
    "preserve_partial_artifacts",
    "record_demo",
    "validate_completion",
    "validate_ffprobe",
    "validate_free_space",
]
