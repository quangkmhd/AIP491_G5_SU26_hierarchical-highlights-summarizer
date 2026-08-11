"""Deterministic, sequential audio timeline used by the Custom_10h demo."""

from __future__ import annotations

import hashlib
import json
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable

SAMPLE_RATE = 16_000
SAMPLE_WIDTH_BYTES = 2
_ZERO_CHUNK_SAMPLES = SAMPLE_RATE


@dataclass(frozen=True, slots=True)
class DemoTimelineItem:
    line_number: int
    recording_id: str
    relative_path: str
    wav_path: Path
    sample_count: int
    start_sample: int
    end_sample: int
    gap_samples: int
    sha256: str


@dataclass(frozen=True, slots=True)
class PlaybackPause:
    after_sample: int
    duration_samples: int


@dataclass(frozen=True, slots=True)
class Custom10hTimeline:
    data_dir: Path
    total_samples: int
    gap_samples: int
    padding_samples: int
    recordings_manifest_sha256: str
    items: tuple[DemoTimelineItem, ...]

    @classmethod
    def build(
        cls,
        data_dir: Path | str,
        duration_seconds: float,
        gap_seconds: float,
    ) -> Custom10hTimeline:
        root = Path(data_dir).expanduser().resolve()
        manifest_path = root / "recordings.jsonl"
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        if gap_seconds < 0:
            raise ValueError("gap_seconds must be non-negative")
        if not manifest_path.is_file():
            raise ValueError(f"recordings manifest does not exist: {manifest_path}")

        target_samples = round(duration_seconds * SAMPLE_RATE)
        configured_gap_samples = round(gap_seconds * SAMPLE_RATE)
        cursor = 0
        seen_ids: set[str] = set()
        items: list[DemoTimelineItem] = []

        with manifest_path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid JSON at recordings.jsonl line {line_number}"
                    ) from exc

                recording_id, relative_path, declared_samples = _parse_row(
                    row,
                    line_number=line_number,
                )
                if recording_id in seen_ids:
                    raise ValueError(f"duplicate recording id: {recording_id}")
                seen_ids.add(recording_id)

                wav_path = (root / relative_path).resolve()
                if not wav_path.is_relative_to(root):
                    raise ValueError(
                        f"audio path is outside Custom_10h: {relative_path}"
                    )
                sample_count = _validate_wav(wav_path)
                if declared_samples != sample_count:
                    raise ValueError(
                        f"num_samples mismatch for {recording_id}: "
                        f"manifest={declared_samples}, wav={sample_count}"
                    )

                end_sample = cursor + sample_count
                if end_sample > target_samples:
                    break

                available_gap = target_samples - end_sample
                item_gap_samples = min(configured_gap_samples, available_gap)
                items.append(
                    DemoTimelineItem(
                        line_number=line_number,
                        recording_id=recording_id,
                        relative_path=relative_path.as_posix(),
                        wav_path=wav_path,
                        sample_count=sample_count,
                        start_sample=cursor,
                        end_sample=end_sample,
                        gap_samples=item_gap_samples,
                        sha256=_sha256_file(wav_path),
                    )
                )
                cursor = end_sample + item_gap_samples
                if cursor == target_samples:
                    break

        return cls(
            data_dir=root,
            total_samples=target_samples,
            gap_samples=configured_gap_samples,
            padding_samples=target_samples - cursor,
            recordings_manifest_sha256=_sha256_file(manifest_path),
            items=tuple(items),
        )

    def manifest_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "sample_rate": SAMPLE_RATE,
            "duration_samples": self.total_samples,
            "gap_samples": self.gap_samples,
            "padding_samples": self.padding_samples,
            "recordings_manifest_sha256": self.recordings_manifest_sha256,
            "items": [
                {
                    "line_number": item.line_number,
                    "recording_id": item.recording_id,
                    "relative_path": item.relative_path,
                    "sample_count": item.sample_count,
                    "start_sample": item.start_sample,
                    "end_sample": item.end_sample,
                    "gap_samples": item.gap_samples,
                    "sha256": item.sha256,
                }
                for item in self.items
            ],
        }

    def resolve_audio(self, recording_id: str) -> Path:
        for item in self.items:
            if item.recording_id == recording_id:
                return item.wav_path
        raise KeyError(f"unknown recording id: {recording_id}")

    def write_wav(
        self,
        output: Path | str,
        pauses: Iterable[PlaybackPause] = (),
    ) -> Path:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ordered_pauses = _validate_pauses(pauses, self.total_samples)
        pause_index = 0
        source_cursor = 0

        with wave.open(str(output_path), "wb") as destination:
            destination.setnchannels(1)
            destination.setsampwidth(SAMPLE_WIDTH_BYTES)
            destination.setframerate(SAMPLE_RATE)

            for item in self.items:
                source_cursor, pause_index = _write_source_silence(
                    destination,
                    source_cursor,
                    item.start_sample,
                    ordered_pauses,
                    pause_index,
                )
                with wave.open(str(item.wav_path), "rb") as source:
                    source_cursor, pause_index = _copy_source_frames(
                        source,
                        destination,
                        source_cursor,
                        item.sample_count,
                        ordered_pauses,
                        pause_index,
                    )

            source_cursor, pause_index = _write_source_silence(
                destination,
                source_cursor,
                self.total_samples,
                ordered_pauses,
                pause_index,
            )
            while pause_index < len(ordered_pauses):
                _write_zeros(destination, ordered_pauses[pause_index].duration_samples)
                pause_index += 1

        return output_path


def _parse_row(row: object, *, line_number: int) -> tuple[str, Path, int]:
    if not isinstance(row, dict):
        raise ValueError(f"recordings.jsonl line {line_number} must be an object")
    recording_id = row.get("id")
    sources = row.get("sources")
    declared_samples = row.get("num_samples")
    if not isinstance(recording_id, str) or not recording_id:
        raise ValueError(f"missing recording id at line {line_number}")
    if not isinstance(declared_samples, int) or declared_samples < 0:
        raise ValueError(f"invalid num_samples for {recording_id}")
    if not isinstance(sources, list) or len(sources) != 1:
        raise ValueError(f"{recording_id} must have exactly one audio source")
    source = sources[0]
    if not isinstance(source, dict) or not isinstance(source.get("source"), str):
        raise ValueError(f"invalid audio source for {recording_id}")
    relative_path = Path(source["source"])
    if relative_path.is_absolute():
        raise ValueError(f"audio path is outside Custom_10h: {relative_path}")
    return recording_id, relative_path, declared_samples


def _validate_wav(path: Path) -> int:
    if not path.is_file():
        raise ValueError(f"audio file does not exist: {path}")
    with wave.open(str(path), "rb") as stream:
        if stream.getnchannels() != 1:
            raise ValueError(f"WAV must be mono: {path.name}")
        if stream.getframerate() != SAMPLE_RATE:
            raise ValueError(
                f"WAV sample rate expected {SAMPLE_RATE}, got {stream.getframerate()}: "
                f"{path.name}"
            )
        if stream.getsampwidth() != SAMPLE_WIDTH_BYTES:
            raise ValueError(f"WAV must use 16-bit PCM: {path.name}")
        if stream.getcomptype() != "NONE":
            raise ValueError(f"WAV must be uncompressed PCM: {path.name}")
        return stream.getnframes()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_pauses(
    pauses: Iterable[PlaybackPause],
    total_samples: int,
) -> tuple[PlaybackPause, ...]:
    result = tuple(sorted(pauses, key=lambda pause: pause.after_sample))
    for pause in result:
        if not 0 <= pause.after_sample <= total_samples:
            raise ValueError("pause position is outside the source timeline")
        if pause.duration_samples < 0:
            raise ValueError("pause duration must be non-negative")
    return result


def _write_source_silence(
    destination: wave.Wave_write,
    cursor: int,
    target: int,
    pauses: tuple[PlaybackPause, ...],
    pause_index: int,
) -> tuple[int, int]:
    while pause_index < len(pauses) and pauses[pause_index].after_sample <= target:
        pause = pauses[pause_index]
        if pause.after_sample < cursor:
            raise ValueError("pause positions cannot split an already-written source frame")
        _write_zeros(destination, pause.after_sample - cursor)
        cursor = pause.after_sample
        _write_zeros(destination, pause.duration_samples)
        pause_index += 1
    _write_zeros(destination, target - cursor)
    return target, pause_index


def _copy_source_frames(
    source: wave.Wave_read,
    destination: wave.Wave_write,
    cursor: int,
    sample_count: int,
    pauses: tuple[PlaybackPause, ...],
    pause_index: int,
) -> tuple[int, int]:
    end = cursor + sample_count
    while pause_index < len(pauses) and pauses[pause_index].after_sample <= end:
        pause = pauses[pause_index]
        frame_count = pause.after_sample - cursor
        destination.writeframesraw(source.readframes(frame_count))
        cursor += frame_count
        _write_zeros(destination, pause.duration_samples)
        pause_index += 1
    destination.writeframesraw(source.readframes(end - cursor))
    return end, pause_index


def _write_zeros(destination: BinaryIO | wave.Wave_write, sample_count: int) -> None:
    zero_chunk = b"\x00" * (_ZERO_CHUNK_SAMPLES * SAMPLE_WIDTH_BYTES)
    remaining = sample_count
    while remaining:
        current = min(remaining, _ZERO_CHUNK_SAMPLES)
        destination.writeframesraw(zero_chunk[: current * SAMPLE_WIDTH_BYTES])
        remaining -= current
