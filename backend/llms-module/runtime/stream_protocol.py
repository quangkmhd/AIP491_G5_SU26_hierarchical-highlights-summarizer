from __future__ import annotations

from typing import Any

from service.summarization_orchestrator import StreamingOrchestrator


class StreamProtocolSession:
    """Validate one meeting stream and adapt orchestrator events to wire messages."""

    def __init__(self, orchestrator: StreamingOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.session_id: str | None = None
        self.accepted_indexes: set[int] = set()
        self.next_index: int | None = None
        self.closed = False

    def handle(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        message_type = payload.get("type")
        if message_type == "start":
            return self._start(payload)
        if self.session_id is None:
            return [self._error("session-not-started", "Send start before streaming utterances")]
        if payload.get("session_id") != self.session_id:
            return [self._error("session-mismatch", "Message session_id doesn't match this stream")]
        if message_type == "utterance":
            return self._accept_utterance(payload)
        if message_type in {"flush", "session_end", "complete"}:
            return self._flush()
        return [self._error("unknown-message-type", f"Unsupported message type: {message_type}")]

    def _start(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        session_id = str(payload.get("session_id", "")).strip()
        if not session_id:
            return [self._error("missing-session-id", "start requires session_id")]
        if self.session_id is not None and self.session_id != session_id:
            return [self._error("session-already-started", "This stream already owns another session")]
        self.session_id = session_id
        return []

    def _accept_utterance(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if self.closed:
            return [self._error("session-finalized", "The meeting stream is already finalized")]
        try:
            index = int(payload["index"])
        except (KeyError, TypeError, ValueError):
            return [self._error("invalid-index", "utterance index must be an integer")]

        if index in self.accepted_indexes:
            return [{
                "type": "utterance-accepted",
                "session_id": self.session_id,
                "index": index,
                "duplicate": True,
            }]
        if self.next_index is not None and index != self.next_index:
            return [self._error(
                "out-of-order-index",
                f"Expected utterance index {self.next_index}, received {index}",
            )]

        text = str(payload.get("text", "")).strip()
        if not text:
            return [self._error("empty-text", "utterance text cannot be empty")]
        speaker = str(payload.get("speaker", "Speaker 01")).strip() or "Speaker 01"

        messages = self._event_messages(
            self.orchestrator.accept_utterance(text=text, speaker=speaker, index=index)
        )
        self.accepted_indexes.add(index)
        self.next_index = index + 1
        return messages

    def _flush(self) -> list[dict[str, Any]]:
        if self.closed:
            return []
        self.closed = True
        return self._event_messages(self.orchestrator.flush_and_finalize())

    def _event_messages(self, events) -> list[dict[str, Any]]:
        return [
            {"type": event.type.value, "session_id": self.session_id, **event.data}
            for event in events
        ]

    def _error(self, code: str, message: str) -> dict[str, Any]:
        return {
            "type": "error",
            "session_id": self.session_id,
            "code": code,
            "message": message,
        }
