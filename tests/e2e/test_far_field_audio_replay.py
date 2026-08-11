from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from src.runtime.api import create_app
from src.service import StreamingOrchestrator
from src.service.audio_capture import StreamingAudioSession
from src.service.audio_preprocessor import AudioPreprocessor
from src.service.diarization_engine import DiarizationResult, DiarizedStream
from src.service.far_field_pipeline import FarFieldSession, VadSpeechSegment


class _IdentityEnhancer:
    def enhance(self, samples: np.ndarray) -> np.ndarray:
        return samples


class _AllSpeechVad:
    def __init__(self) -> None:
        self._samples: list[np.ndarray] = []

    def accept(self, chunk) -> list[VadSpeechSegment]:
        self._samples.append(chunk.samples)
        return []

    def flush(self) -> list[VadSpeechSegment]:
        samples = np.concatenate(self._samples)
        return [VadSpeechSegment(samples, 0, len(samples), 1.0)]


class _OneSpeakerDiarizer:
    def process(self, enhanced_audio, speaker_audio, *, speech_duration, vad_confidence):
        return DiarizationResult(
            streams=(DiarizedStream("Speaker 01", enhanced_audio.copy()),),
            has_overlap=False,
            latency_ms=0.0,
        )


class _Recognizer:
    def decode_segment(self, samples: np.ndarray, sample_rate: int = 16_000) -> str:
        return "âm thanh đã phục hồi" if len(samples) else ""


class _Summarizer:
    def abstractive(self, chunk, chapter_number=1, chunk_index=0):
        return "Tóm tắt"

    def title(self, segment, chapter_number=1):
        return "Chủ đề"


class _RecoverableFactory:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.sessions: list[FarFieldSession] = []

    def create(self, start) -> FarFieldSession:
        session = FarFieldSession(
            session_id=f"session-{len(self.sessions) + 1}",
            audio=StreamingAudioSession(
                f"session-{len(self.sessions) + 1}",
                start.sample_rate,
                self.root,
            ),
            preprocessor=AudioPreprocessor(
                _IdentityEnhancer(),
                chunk_seconds=0.05,
                overlap_seconds=0.01,
            ),
            vad=_AllSpeechVad(),
            diarizer=_OneSpeakerDiarizer(),
            asr=_Recognizer(),
        )
        self.sessions.append(session)
        return session


def test_recorded_pcm_survives_disconnect_and_replay(tmp_path: Path) -> None:
    factory = _RecoverableFactory(tmp_path)
    app = create_app(
        StreamingOrchestrator(summarizer=_Summarizer()),
        audio_session_factory=factory,
    )
    source = np.linspace(-0.2, 0.2, 4_800, dtype=np.float32)

    with TestClient(app).websocket_connect("/ws") as websocket:
        websocket.send_json({
            "type": "session_start",
            "protocol_version": 1,
            "sample_rate": 48_000,
            "channels": 1,
            "settings": {},
        })
        assert websocket.receive_json()["type"] == "session_ready"
        websocket.send_bytes(source.tobytes())

    captured = factory.sessions[0]
    wav_path = captured.audio.path
    assert captured.audio.accepted_samples == len(source)
    assert wav_path.exists()
    persisted, sample_rate = sf.read(wav_path, dtype="float32")
    assert sample_rate == 48_000
    np.testing.assert_allclose(persisted, source)

    replay = factory.create(type("Start", (), {"sample_rate": sample_rate})())
    replay.push(np.ascontiguousarray(persisted, dtype=np.float32))
    events = replay.flush()
    replay.close(retain=False)

    assert events
    assert all(event.type == "utterance" for event in events)
    assert events[0].text == "âm thanh đã phục hồi"
