"""Integration tests for the FastAPI streaming endpoint (runtime-001+002+streaming)."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from httpx import ASGITransport, AsyncClient  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.runtime.api import _decode_pcm_float32, create_app  # noqa: E402
from src.service import Custom10hTimeline, StreamingOrchestrator  # noqa: E402


class FakeSummarizer:
    def abstractive(self, chunk, chapter_number=1, chunk_index=0):
        return f"Tóm tắt {chunk.utterances[0].index}"
    def title(self, segment, chapter_number=1):
        return f"Chủ đề {chapter_number}"


class FakeAudioSession:
    session_id = "audio-session-1"

    def __init__(self) -> None:
        self.closed = False

    def push(self, samples):
        return (
            {
                "type": "utterance",
                "id": 1,
                "session_id": self.session_id,
                "speaker": "Speaker 01",
                "text": "xin chào",
                "start_sec": 0.0,
                "end_sec": 1.0,
                "source_sample_rate": 48000,
                "sample_rate": 16000,
                "quality": {
                    "rms": 0.02,
                    "peak": 0.1,
                    "clipped": False,
                    "vad_confidence": 0.9,
                    "speech_duration": 1.0,
                },
                "preprocessing_ms": 1.0,
                "diarization_ms": 2.0,
                "asr_ms": 3.0,
                "total_ms": 6.0,
                "degraded": False,
                "fallback": False,
            },
        )

    def flush(self):
        return ()

    def close(self, *, retain=True):
        self.closed = True


class FakeAudioSessionFactory:
    def __init__(self) -> None:
        self.session = FakeAudioSession()
        self.starts = []

    def create(self, start):
        self.starts.append(start)
        return self.session


def build_test_app(audio_session_factory=None, demo_timeline=None):
    factory = audio_session_factory or FakeAudioSessionFactory()
    return create_app(
        StreamingOrchestrator(summarizer=FakeSummarizer()),
        audio_session_factory=factory,
        demo_timeline=demo_timeline,
    )


def _build_demo_timeline(tmp_path: Path) -> Custom10hTimeline:
    data_dir = tmp_path / "Custom_10h"
    wav_dir = data_dir / "wavs"
    wav_dir.mkdir(parents=True)
    rows = []
    for recording_id in ("b_00001", "a_00002"):
        relative_path = f"wavs/{recording_id}.wav"
        with wave.open(str(data_dir / relative_path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(16_000)
            stream.writeframes(b"\x00\x00" * 1_600)
        rows.append(
            {
                "id": recording_id,
                "sources": [{"type": "file", "channels": [0], "source": relative_path}],
                "sampling_rate": 16_000,
                "num_samples": 1_600,
                "duration": 0.1,
            }
        )
    (data_dir / "recordings.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    return Custom10hTimeline.build(data_dir, duration_seconds=1.0, gap_seconds=0.1)


def test_demo_routes_are_not_registered_without_demo_timeline() -> None:
    app = build_test_app()
    with TestClient(app) as client:
        assert client.get("/api/v1/demo/custom10h/status").status_code == 404


def test_demo_audio_route_serves_only_manifest_ids(tmp_path: Path) -> None:
    timeline = _build_demo_timeline(tmp_path)
    app = build_test_app(demo_timeline=timeline)
    with TestClient(app) as client:
        status = client.get("/api/v1/demo/custom10h/status")
        assert status.status_code == 200
        assert status.json() == {"enabled": True, "recording_count": 2}

        manifest = client.get("/api/v1/demo/custom10h/manifest")
        assert manifest.status_code == 200
        assert [row["recording_id"] for row in manifest.json()["items"]] == [
            "b_00001",
            "a_00002",
        ]
        assert client.get("/api/v1/demo/custom10h/audio/b_00001").status_code == 200
        assert client.get("/api/v1/demo/custom10h/audio/missing").status_code == 404


class ApiProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = build_test_app()

    def test_process_endpoint_returns_recap(self) -> None:
        async def _run() -> None:
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/meetings/process",
                    json={"flat_texts": ["Xin chào.", "Bắt đầu họp.", "Mục tiêu hôm nay."]},
                )
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertIn("segments", data)
                self.assertIn("meeting_id", data)
                self.assertGreaterEqual(len(data["segments"]), 1)
                # No highlights keys
                self.assertNotIn("highlights_notes", data)
                self.assertNotIn("highlights_tasks", data)
        asyncio.run(_run())

    def test_process_empty_payload_returns_422(self) -> None:
        async def _run() -> None:
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/meetings/process",
                    json={"flat_texts": [], "utterances": []},
                )
                self.assertEqual(resp.status_code, 422)
                data = resp.json()
                self.assertIn("fix", data)
                self.assertIn("utterances", data["fix"])
                self.assertIn("X-Request-Id", resp.headers)
        asyncio.run(_run())

    def test_process_echoes_request_id_header(self) -> None:
        async def _run() -> None:
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/meetings/process",
                    headers={"X-Request-Id": "test-rid-123"},
                    json={"flat_texts": ["Xin chào.", "Bắt đầu họp."]},
                )
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.headers["X-Request-Id"], "test-rid-123")
        asyncio.run(_run())


class ApiStreamingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = build_test_app()

    def test_stream_endpoint_returns_sse(self) -> None:
        async def _run() -> None:
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/meetings/stream",
                    json={"flat_texts": ["Xin chào.", "Bắt đầu họp.", "Mục tiêu hôm nay.", "Kết thúc."]},
                )
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.headers["content-type"], "text/event-stream; charset=utf-8")
                body = resp.text
                # SSE format: "event: <type>\ndata: <json>\n\n"
                self.assertIn("event:", body)
                self.assertIn("data:", body)
                # Should have at least one segment-closed
                self.assertIn("segment-closed", body)
                # Last event should be 'end'
                self.assertIn("event: end", body)
        asyncio.run(_run())

    def test_stream_empty_payload_returns_422(self) -> None:
        async def _run() -> None:
            transport = ASGITransport(app=self.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/meetings/stream",
                    json={"flat_texts": []},
                )
                self.assertEqual(resp.status_code, 422)
                data = resp.json()
                self.assertIn("fix", data)
                self.assertIn("utterances", data["fix"])
        asyncio.run(_run())


class PcmValidationTests(unittest.TestCase):
    def test_decode_pcm_float32_rejects_non_float32_byte_length(self) -> None:
        with self.assertRaisesRegex(ValueError, "multiple of 4"):
            _decode_pcm_float32(b"x")

    def test_decode_pcm_float32_rejects_non_finite_samples(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite"):
            _decode_pcm_float32(np.array([np.nan], dtype=np.float32).tobytes())


class AudioWebSocketProtocolTests(unittest.TestCase):
    def test_websocket_requires_session_start_before_pcm(self) -> None:
        app = build_test_app()

        with TestClient(app).websocket_connect("/ws") as websocket:
            websocket.send_bytes(np.zeros(128, dtype=np.float32).tobytes())
            message = websocket.receive_json()

        self.assertEqual(message["type"], "pipeline_error")
        self.assertEqual(message["stage"], "protocol")

    def test_websocket_acknowledges_config_and_emits_only_final_text(self) -> None:
        factory = FakeAudioSessionFactory()
        app = build_test_app(factory)

        with TestClient(app).websocket_connect("/ws") as websocket:
            websocket.send_json({
                "type": "session_start",
                "protocol_version": 1,
                "sample_rate": 48000,
                "channels": 1,
                "settings": {
                    "echo_cancellation": True,
                    "noise_suppression": True,
                    "auto_gain_control": True,
                },
            })
            ready = websocket.receive_json()
            websocket.send_bytes(np.ones(4096, dtype=np.float32).tobytes())
            event = websocket.receive_json()
            websocket.send_json({"type": "session_end", "retain": True})
            final_messages = []
            while True:
                message = websocket.receive_json()
                final_messages.append(message)
                if message["type"] == "session_closed":
                    break

        self.assertEqual(ready["type"], "session_ready")
        self.assertEqual(ready["session_id"], "audio-session-1")
        self.assertEqual(event["type"], "utterance")
        self.assertEqual(event["text"], "xin chào")
        self.assertGreater(event["quality"]["rms"], 0)
        self.assertEqual(final_messages[-1]["type"], "session_closed")
        self.assertNotIn("partial_utterance", [message["type"] for message in final_messages])
        self.assertEqual(len(factory.starts), 1)
        self.assertTrue(factory.session.closed)
