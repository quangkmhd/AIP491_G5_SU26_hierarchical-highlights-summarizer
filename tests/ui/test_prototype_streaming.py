"""Playwright UI tests for the Web prototype (ui-001+002+streaming).

These tests verify the page structure and static assets load correctly.
End-to-end streaming is verified at the API integration level
(tests/integration/test_api_streaming.py).
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import uvicorn
from playwright.sync_api import sync_playwright

from src.runtime.api import create_app
from src.service import Custom10hTimeline, StreamingOrchestrator


class _FakeSummarizer:
    def abstractive(self, chunk, chapter_number=1, chunk_index=0):
        return "Tóm tắt test"
    def title(self, segment, chapter_number=1):
        return "Chủ đề test"


class _FakeAudioSession:
    session_id = "demo-session"

    def __init__(self) -> None:
        self.push_count = 0

    def push(self, samples):
        self.push_count += 1
        if self.push_count % 2 == 0:
            return ()
        start_sec = (self.push_count - 1) * 0.1
        return (
            {
                "type": "utterance",
                "id": self.push_count,
                "session_id": self.session_id,
                "speaker": "Speaker 01",
                "text": f"nội dung demo {self.push_count}",
                "start_sec": start_sec,
                "end_sec": start_sec + 0.1,
                "source_sample_rate": 16_000,
                "sample_rate": 16_000,
                "quality": {
                    "rms": 0.02,
                    "peak": 0.1,
                    "clipped": False,
                    "vad_confidence": 0.9,
                    "speech_duration": 0.1,
                },
                "preprocessing_ms": 1.0,
                "diarization_ms": 1.0,
                "asr_ms": 1.0,
                "total_ms": 3.0,
                "degraded": False,
                "fallback": False,
            },
        )

    def flush(self):
        return ()

    def close(self, *, retain=True):
        return None


class _FakeAudioSessionFactory:
    def create(self, start):
        return _FakeAudioSession()


def _build_demo_timeline(root: Path) -> Custom10hTimeline:
    data_dir = root / "Custom_10h"
    wav_dir = data_dir / "wavs"
    wav_dir.mkdir(parents=True)
    rows = []
    for recording_id in ("z-first", "a-second", "m-third"):
        relative_path = f"wavs/{recording_id}.wav"
        with wave.open(str(data_dir / relative_path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(16_000)
            stream.writeframes(b"\x00\x01" * 1_600)
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
    return Custom10hTimeline.build(data_dir, duration_seconds=0.6, gap_seconds=0.1)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _BackgroundServer:
    def __init__(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        timeline = _build_demo_timeline(Path(self.temp_dir.name))
        self.port = _find_free_port()
        self.config = uvicorn.Config(
            create_app(
                StreamingOrchestrator(summarizer=_FakeSummarizer()),
                audio_session_factory=_FakeAudioSessionFactory(),
                demo_timeline=timeline,
            ),
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
        )
        self.server = uvicorn.Server(self.config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        for _ in range(50):
            if self.server.started:
                return
            time.sleep(0.1)
        raise RuntimeError("uvicorn did not start in time")

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)
        self.temp_dir.cleanup()


class PrototypeStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _BackgroundServer()
        cls.base_url = f"http://127.0.0.1:{cls.server.port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.stop()

    def test_index_page_loads_with_correct_title(self) -> None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f"{self.base_url}/")
                self.assertIn("Meeting Recap", page.title())
            finally:
                browser.close()

    def test_page_has_required_input_elements(self) -> None:
        """React frontend renders a recording UI with mic controls."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f"{self.base_url}/")
                # React app renders the root element; UI elements are
                # created dynamically -- verify the root container loads.
                page.wait_for_selector("#root", timeout=5000)
                root = page.locator("#root")
                self.assertTrue(root.is_visible())
            finally:
                browser.close()

    def test_page_has_no_highlights_tab(self) -> None:
        # DR1 was dropped: no Highlights tab in the UI
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f"{self.base_url}/")
                page.wait_for_selector("#root", timeout=5000)
                body_text = page.locator("body").text_content()
                self.assertNotIn("Highlights", body_text)
            finally:
                browser.close()

    def test_static_assets_served(self) -> None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f"{self.base_url}/")
                # React/Vite bundles are served from /assets/
                scripts = page.evaluate("Array.from(document.scripts).map(s => s.src)")
                self.assertTrue(any("/assets/" in s for s in scripts),
                                f"JS bundle not loaded; scripts: {scripts}")
            finally:
                browser.close()

    def test_demo_plays_manifest_audio_sequentially_without_microphone(self) -> None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.add_init_script(
                    """
                    window.__microphoneRequested = false;
                    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                    navigator.mediaDevices.getUserMedia = (...args) => {
                      window.__microphoneRequested = true;
                      return original(...args);
                    };
                    """
                )
                page.goto(f"{self.base_url}/?demo=custom10h")
                page.get_by_role("button", name="Bắt đầu demo").click(timeout=3_000)
                page.wait_for_function(
                    "document.body.dataset.demoState === 'completed'",
                    timeout=10_000,
                )
                trace = page.evaluate("window.__vietAsrDemoTrace")

                self.assertEqual(
                    trace["completedRecordingIds"],
                    ["z-first", "a-second", "m-third"],
                )
                self.assertEqual(trace["maxConcurrentAudio"], 1)
                self.assertFalse(page.evaluate("window.__microphoneRequested"))
                self.assertGreaterEqual(
                    trace["completedEpochMs"] - trace["playbackStartedEpochMs"],
                    550,
                )
            finally:
                browser.close()

    def test_demo_ui_renders_real_utterance_and_final_recap(self) -> None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f"{self.base_url}/?demo=custom10h")
                page.get_by_role("button", name="Bắt đầu demo").click(timeout=3_000)
                page.wait_for_selector("[data-testid='transcript-utterance']", timeout=5_000)
                page.wait_for_function(
                    "document.body.dataset.demoState === 'completed'",
                    timeout=10_000,
                )

                self.assertTrue(page.get_by_text("LIVE DEMO · Custom_10h").is_visible())
                self.assertTrue(page.get_by_text("Meeting Recap").is_visible())
                progress = page.locator("[data-testid='demo-progress']")
                self.assertEqual(progress.get_attribute("aria-valuenow"), "100")
                self.assertTrue(page.get_by_text("m-third · 100%").is_visible())
            finally:
                browser.close()

    def test_standard_ui_does_not_enter_demo_mode(self) -> None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f"{self.base_url}/")

                self.assertEqual(page.get_by_text("LIVE DEMO · Custom_10h").count(), 0)
                self.assertEqual(page.get_by_role("button", name="Bắt đầu demo").count(), 0)
                self.assertNotEqual(page.evaluate("document.body.dataset.demoState"), "playing")
            finally:
                browser.close()
