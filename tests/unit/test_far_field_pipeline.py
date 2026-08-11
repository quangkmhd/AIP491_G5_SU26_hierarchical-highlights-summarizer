"""Tests for the composed accuracy-first per-session audio pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src.service.audio_preprocessor import ProcessedAudioChunk
from src.service.diarization_engine import DiarizationResult, DiarizedStream
from src.service.far_field_pipeline import FarFieldSession, VadSpeechSegment


class RecordingAudioSession:
    source_rate = 48000

    def __init__(self) -> None:
        self.closed = False

    def push(self, samples: np.ndarray) -> np.ndarray:
        return samples.copy()

    def flush(self) -> np.ndarray:
        return np.empty(0, dtype=np.float32)

    def close(self, *, retain: bool = True) -> Path:
        self.closed = True
        return Path("session.wav")


class OneChunkPreprocessor:
    def process(self, samples: np.ndarray) -> list[ProcessedAudioChunk]:
        if not len(samples):
            return []
        return [
            ProcessedAudioChunk(
                samples=samples.copy(),
                start_sample=0,
                end_sample=len(samples),
                rms=0.02,
                peak=0.1,
                clipped=False,
                preprocessing_ms=5.0,
            )
        ]

    def flush(self) -> list[ProcessedAudioChunk]:
        return []


class OneCompletedSegmentVad:
    def accept(self, chunk: ProcessedAudioChunk) -> list[VadSpeechSegment]:
        return [
            VadSpeechSegment(
                samples=chunk.samples.copy(),
                start_sample=chunk.start_sample,
                end_sample=chunk.end_sample,
                confidence=0.91,
            )
        ]

    def flush(self) -> list[VadSpeechSegment]:
        return []


class TailOnlyVad:
    def __init__(self) -> None:
        self._chunk: ProcessedAudioChunk | None = None

    def accept(self, chunk: ProcessedAudioChunk) -> list[VadSpeechSegment]:
        self._chunk = chunk
        return []

    def flush(self) -> list[VadSpeechSegment]:
        assert self._chunk is not None
        return [
            VadSpeechSegment(
                samples=self._chunk.samples.copy(),
                start_sample=0,
                end_sample=len(self._chunk.samples),
                confidence=0.9,
            )
        ]


class OneSpeakerDiarizer:
    def process(
        self,
        enhanced_audio: np.ndarray,
        speaker_audio: np.ndarray,
        *,
        speech_duration: float,
        vad_confidence: float,
    ) -> DiarizationResult:
        return DiarizationResult(
            streams=(DiarizedStream("Speaker 01", enhanced_audio.copy()),),
            has_overlap=False,
            latency_ms=7.0,
        )


class RecordingAsr:
    def __init__(self, text: str) -> None:
        self.text = text
        self.decode_calls = 0

    def decode_segment(self, samples: np.ndarray, sample_rate: int = 16000) -> str:
        self.decode_calls += 1
        return self.text


def _source() -> np.ndarray:
    return np.full(32000, 0.02, dtype=np.float32)


def test_completed_vad_segment_is_diarized_and_decoded_once() -> None:
    """Reintroducing partial decoding would waste compute and duplicate ASR work."""
    asr = RecordingAsr("xin chào")
    session = FarFieldSession(
        session_id="session-1",
        audio=RecordingAudioSession(),
        preprocessor=OneChunkPreprocessor(),
        vad=OneCompletedSegmentVad(),
        diarizer=OneSpeakerDiarizer(),
        asr=asr,
    )

    events = session.push(_source())

    assert [event.text for event in events] == ["xin chào"]
    assert [event.speaker for event in events] == ["Speaker 01"]
    assert asr.decode_calls == 1
    assert events[0].quality.rms == 0.02
    assert events[0].quality.vad_confidence == 0.91


def test_flush_processes_remaining_vad_tail_once() -> None:
    """Stopping a meeting must not truncate the final utterance."""
    asr = RecordingAsr("kết thúc")
    session = FarFieldSession(
        session_id="session-2",
        audio=RecordingAudioSession(),
        preprocessor=OneChunkPreprocessor(),
        vad=TailOnlyVad(),
        diarizer=OneSpeakerDiarizer(),
        asr=asr,
    )
    assert session.push(_source()) == ()

    events = session.flush()

    assert [event.text for event in events] == ["kết thúc"]
    assert asr.decode_calls == 1


def test_empty_asr_result_does_not_emit_blank_utterance() -> None:
    """Blank recognizer output must not create an invalid transcript row."""
    session = FarFieldSession(
        session_id="session-3",
        audio=RecordingAudioSession(),
        preprocessor=OneChunkPreprocessor(),
        vad=OneCompletedSegmentVad(),
        diarizer=OneSpeakerDiarizer(),
        asr=RecordingAsr(""),
    )

    assert session.push(_source()) == ()
