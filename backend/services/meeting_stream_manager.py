"""Per-meeting WebSocket streams from the Gateway to the LLM module."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import inspect
import json
import logging
from typing import Any, Awaitable, Callable

from websockets.asyncio.client import connect

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], Any]
Connector = Callable[[str], Awaitable[Any]]


@dataclass
class _SessionStream:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    websocket: Any | None = None
    acknowledged_index: int | None = None
    final_summary: dict[str, Any] | None = None
    closed: bool = False


class MeetingStreamManager:
    """Hide connection, ordering, ACK, replay, and flush mechanics from callers."""

    def __init__(
        self,
        db_manager: Any,
        ws_url: str = "ws://localhost:8003/ws",
        connector: Connector | None = None,
        max_retries: int = 3,
        retry_delay: float = 0.25,
    ) -> None:
        self.db = db_manager
        self.ws_url = ws_url
        self._connector = connector or connect
        self.max_retries = max(1, max_retries)
        self.retry_delay = max(0.0, retry_delay)
        self._sessions: dict[str, _SessionStream] = {}

    async def publish(
        self,
        session_id: str,
        utterance: dict[str, Any],
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        state = self._sessions.setdefault(session_id, _SessionStream())
        async with state.lock:
            if state.closed:
                raise RuntimeError(f"Meeting stream {session_id} is already finalized")
            index = int(utterance["utterance_index"])
            if state.acknowledged_index is not None and index <= state.acknowledged_index:
                return
            await self._with_reconnect(session_id, state, progress_callback)
            if state.acknowledged_index is None or index > state.acknowledged_index:
                try:
                    await self._send_utterance(state, session_id, utterance, progress_callback)
                except Exception:
                    await self._close_socket(state)
                    await self._with_reconnect(session_id, state, progress_callback)

    async def finish(
        self,
        session_id: str,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any] | None:
        state = self._sessions.setdefault(session_id, _SessionStream())
        async with state.lock:
            if state.closed:
                return state.final_summary
            await self._with_reconnect(session_id, state, progress_callback)
            await state.websocket.send(json.dumps({"type": "flush", "session_id": session_id}))
            state.final_summary = await self._receive_until_completed(
                state, session_id, progress_callback
            )
            state.closed = True
            if state.final_summary is not None:
                self.db.save_summary(session_id, state.final_summary)
            await self._close_socket(state)
            return state.final_summary

    async def close_all(self) -> None:
        for state in self._sessions.values():
            async with state.lock:
                await self._close_socket(state)

    async def _with_reconnect(
        self,
        session_id: str,
        state: _SessionStream,
        progress_callback: ProgressCallback | None,
    ) -> None:
        if state.websocket is not None:
            return
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                await self._connect_and_replay(session_id, state, progress_callback)
                return
            except Exception as exc:
                last_error = exc
                await self._close_socket(state)
                if attempt + 1 < self.max_retries and self.retry_delay:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
        raise RuntimeError(f"Unable to establish LLM stream for {session_id}") from last_error

    async def _connect_and_replay(
        self,
        session_id: str,
        state: _SessionStream,
        progress_callback: ProgressCallback | None,
    ) -> None:
        state.websocket = await self._connector(self.ws_url)
        state.acknowledged_index = None
        session = self.db.get_session(session_id) or {}
        await state.websocket.send(json.dumps({
            "type": "start",
            "session_id": session_id,
            "meeting_title": session.get("title") or "Meeting Summary",
        }))
        for utterance in self.db.get_utterances(session_id):
            await self._send_utterance(state, session_id, utterance, progress_callback)

    async def _send_utterance(
        self,
        state: _SessionStream,
        session_id: str,
        utterance: dict[str, Any],
        progress_callback: ProgressCallback | None,
    ) -> None:
        index = int(utterance["utterance_index"])
        await state.websocket.send(json.dumps({
            "type": "utterance",
            "session_id": session_id,
            "index": index,
            "speaker": utterance["speaker_id"],
            "text": utterance["text"],
        }))
        while True:
            event = json.loads(await state.websocket.recv())
            await self._emit(event, progress_callback)
            if event.get("type") == "error":
                raise RuntimeError(event.get("message") or "LLM stream protocol error")
            if event.get("type") == "utterance-accepted" and int(event["index"]) == index:
                state.acknowledged_index = index
                return

    async def _receive_until_completed(
        self,
        state: _SessionStream,
        session_id: str,
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any] | None:
        while True:
            event = json.loads(await state.websocket.recv())
            await self._emit(event, progress_callback)
            if event.get("type") == "error":
                raise RuntimeError(event.get("message") or "LLM stream protocol error")
            if event.get("type") == "meeting-completed":
                return event.get("hierarchical_summary")

    async def _emit(
        self,
        event: dict[str, Any],
        progress_callback: ProgressCallback | None,
    ) -> None:
        if progress_callback is None:
            return
        result = progress_callback(event)
        if inspect.isawaitable(result):
            await result

    async def _close_socket(self, state: _SessionStream) -> None:
        websocket, state.websocket = state.websocket, None
        if websocket is not None:
            try:
                await websocket.close()
            except Exception:
                logger.debug("Failed to close LLM WebSocket cleanly", exc_info=True)
