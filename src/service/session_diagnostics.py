from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("src.service.session_diagnostics")


class SessionDiagnostics:
    """Append inspectable records without becoming part of the audio critical path."""

    def __init__(self, path: Path, session_id: str) -> None:
        self.path = path
        self.session_id = session_id
        self._lock = threading.Lock()
        self._closed = False
        self._stream = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._stream = path.open("a", encoding="utf-8")
        except OSError as exc:
            logger.warning("Session diagnostics unavailable at %s: %s", path, exc)

    def record(self, event: str, **fields: Any) -> None:
        if self._closed or self._stream is None:
            return
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": self.session_id,
            "event": event,
            **fields,
        }
        try:
            encoded = json.dumps(payload, ensure_ascii=False, default=str, allow_nan=False)
            with self._lock:
                self._stream.write(encoded + "\n")
                self._stream.flush()
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("Could not write %s diagnostics for %s: %s", event, self.session_id, exc)

    def close(self, *, retain: bool = True, **fields: Any) -> None:
        if self._closed:
            return
        self.record("session_end", retained=retain, **fields)
        self._closed = True
        if self._stream is not None:
            try:
                self._stream.close()
            except OSError as exc:
                logger.warning("Could not close diagnostics for %s: %s", self.session_id, exc)
            self._stream = None
        if not retain:
            self.path.unlink(missing_ok=True)


class NullSessionDiagnostics:
    """No-op diagnostics used by focused unit tests and custom compositions."""

    def record(self, event: str, **fields: Any) -> None:
        return None

    def close(self, *, retain: bool = True, **fields: Any) -> None:
        return None


__all__ = ["NullSessionDiagnostics", "SessionDiagnostics"]
