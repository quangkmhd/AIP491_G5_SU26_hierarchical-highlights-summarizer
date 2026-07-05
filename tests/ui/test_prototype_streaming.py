"""Playwright UI tests for the Web prototype (ui-001+002+streaming).

These tests verify the page structure and static assets load correctly.
End-to-end streaming is verified at the API integration level
(tests/integration/test_api_streaming.py).
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import unittest
from pathlib import Path

os.environ.setdefault("MODEL_LOAD_LLM", "0")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import uvicorn
from playwright.sync_api import sync_playwright

from src.runtime.api import create_app


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _BackgroundServer:
    def __init__(self) -> None:
        self.port = _find_free_port()
        self.config = uvicorn.Config(
            create_app(),
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
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f"{self.base_url}/")
                self.assertTrue(page.locator("#transcript-input").is_visible())
                self.assertTrue(page.locator("#process-btn").is_visible())
            finally:
                browser.close()

    def test_page_has_no_highlights_tab(self) -> None:
        # DR1 was dropped: no Highlights tab in the UI
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f"{self.base_url}/")
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
                # Verify the script tag is present and loads
                scripts = page.evaluate("Array.from(document.scripts).map(s => s.src)")
                self.assertTrue(any("/static/app.js" in s for s in scripts),
                                f"app.js not loaded; scripts: {scripts}")
                # Verify CSS is loaded
                links = page.evaluate("Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(l => l.href)")
                self.assertTrue(any("/static/styles.css" in l for l in links),
                                f"styles.css not loaded; links: {links}")
            finally:
                browser.close()
