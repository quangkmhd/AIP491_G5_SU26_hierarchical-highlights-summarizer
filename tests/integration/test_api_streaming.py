"""Integration tests for the FastAPI streaming endpoint (runtime-001+002+streaming)."""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("MODEL_LOAD_LLM", "0")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from httpx import ASGITransport, AsyncClient

from src.runtime.api import create_app


class ApiProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()

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
        cls.app = create_app()

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
