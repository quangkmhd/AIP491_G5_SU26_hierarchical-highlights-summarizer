"""Centralized logging for the meeting-recap project.

Design goals:
  1. **Structured**: every log record is a JSON object (one per line)
     with stable fields: timestamp, level, logger, message, request_id,
     event, plus arbitrary `extra` fields.
  2. **Bounded verbosity**: by default INFO; opt-in to DEBUG via
     `MEETING_RECAP_LOG_LEVEL=DEBUG` or per-logger override
     `MEETING_RECAP_LOG_<LOGGER>_LEVEL=DEBUG`.
  3. **Useful by default**: the human-readable formatter includes the
     request_id and event tag. The JSON formatter is for log aggregators.
  4. **Fix suggestions on errors**: when raising a `LoggableError`, the
     `fix` field is logged and surfaced in API responses.
  5. **Request tracing**: `with request_context(...)` sets a
     `request_id` ContextVar that every log call within the block tags.
     CLI invocations get a synthetic id; FastAPI middleware sets one per
     request.

Public API:
  - get_logger(name): return a configured logger
  - request_context(request_id=None, event=""): context manager that
    tags every log call within its block
  - log_error_with_fix(logger, error, *, fix, hint=""): convenience for
    the common pattern "log an error and include a fix suggestion"
  - LoggableError: base class for errors that carry a `fix` field
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4 as _uuid4
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Iterator

# ContextVar holds the current request_id and event. Default is "no-context".
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_event: ContextVar[str] = ContextVar("event", default="-")


class LoggableError(Exception):
    """Base class for errors that carry a `fix` suggestion.

    Subclasses set `fix` (a short human-readable fix) and optionally
    `hint` (additional context). The FastAPI exception handler surfaces
    these in the JSON error response so the client sees not just "what
    went wrong" but also "what to do about it".
    """

    def __init__(self, message: str, *, fix: str, hint: str = "") -> None:
        super().__init__(message)
        self.fix = fix
        self.hint = hint


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object.

    Field set (stable, machine-readable):
      - ts: ISO-8601 UTC timestamp
      - level: INFO / WARNING / ERROR / DEBUG
      - logger: logger name
      - message: the formatted message
      - request_id: from request_context (or "-" if none)
      - event: from request_context (or "-" if none)
      - any extra fields passed via `logger.info("...", extra={...})`
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
            "event": _event.get(),
        }
        # Forward any extras the caller attached via extra=...
        for key, value in record.__dict__.items():
            if key in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "asctime",
            ):
                continue
            if key.startswith("_"):
                continue
            if key == "taskName":
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__
            payload["exc_message"] = str(record.exc_info[1])
        return json.dumps(payload, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Emit log records as a single line, human-readable.

    Format: `ts level [logger] [request_id] [event] message`
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%H:%M:%S")
        rid = _request_id.get()
        evt = _event.get()
        parts = [
            ts,
            f"{record.levelname:<5}",
            f"[{record.name}]",
        ]
        if rid != "-":
            parts.append(f"[{rid}]")
        if evt != "-":
            parts.append(f"[{evt}]")
        parts.append(record.getMessage())
        line = " ".join(parts)
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger under the `src.*` namespace.

    Idempotent: calling twice with the same name returns the same logger.
    The first call configures the root logger with our handlers; later
    calls only fetch the named logger.
    """
    logger = logging.getLogger(name)
    if not _root_configured:
        _configure_root()
    return logger


_root_configured = False


def _configure_root() -> None:
    """Configure the root logger with console + file handlers.

    Level can be overridden via env var `MEETING_RECAP_LOG_LEVEL`
    (e.g. DEBUG, INFO, WARNING). Format defaults to human; set
    `MEETING_RECAP_LOG_FORMAT=json` for machine-readable output.

    Logs are written to both stderr and ``logs/run.log`` (relative to
    the current working directory). The file handler always uses DEBUG
    level so full detail is captured on disk even when the console
    shows only INFO.
    """
    global _root_configured
    if _root_configured:
        return
    _root_configured = True

    level_name = os.environ.get("MEETING_RECAP_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    format_name = os.environ.get("MEETING_RECAP_LOG_FORMAT", "human").lower()
    if format_name == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = HumanFormatter()

    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # File handler (logs/run.log) — always DEBUG for full detail
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "run.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.handlers.clear()  # avoid duplicate handlers on re-import
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root.setLevel(logging.DEBUG)  # root DEBUG; handlers filter independently

    # Quiet down noisy third-party loggers. We set them to ERROR so
    # only actionable errors appear; the user can override per-logger
    # via MEETING_RECAP_LOG_<LOGGER>_LEVEL.
    for noisy in (
        "transformers", "urllib3", "asyncio", "httpx", "httpcore",
        "huggingface_hub", "filelock", "numexpr", "torchao",
        "faker", "matplotlib", "PIL",
    ):
        noisy_logger = logging.getLogger(noisy)
        # Honor explicit per-logger override
        env_key = f"MEETING_RECAP_LOG_{noisy.upper()}_LEVEL"
        if env_key in os.environ:
            override = os.environ[env_key].upper()
            noisy_logger.setLevel(getattr(logging, override, logging.ERROR))
        else:
            noisy_logger.setLevel(logging.ERROR)


@contextmanager
def request_context(
    request_id: str | None = None, event: str = ""
) -> Iterator[str]:
    """Set the current request_id + event for the duration of a block.

    Usage:
        with request_context(event="process") as rid:
            logger.info("starting")
            # ... do work ...
            logger.info("done")

    If `request_id` is None, a uuid4 hex is generated. The yielded value
    is the request_id (whether generated or supplied) so callers can
    include it in API responses for log correlation.
    """
    rid = request_id or _uuid4().hex[:12]
    rid_token = _request_id.set(rid)
    evt_token = _event.set(event or "-")
    try:
        yield rid
    finally:
        _request_id.reset(rid_token)
        _event.reset(evt_token)


def log_error_with_fix(
    logger: logging.Logger,
    error: BaseException,
    *,
    fix: str | None = None,
    hint: str = "",
    level: int = logging.ERROR,
) -> None:
    """Log an error with a `fix` field attached for log aggregation.

    This is the canonical pattern for service-layer error paths. The
    `fix` field shows up in the JSON log so operators can search
    `fix:*` in their log aggregator.
    """
    extra: dict[str, Any] = {"fix": fix}
    if hint:
        extra["hint"] = hint
    # If the error is a LoggableError, prefer its own fix/hint
    if isinstance(error, LoggableError):
        extra["fix"] = error.fix
        if error.hint:
            extra["hint"] = error.hint
    extra["error_type"] = type(error).__name__
    logger.log(level, str(error) or type(error).__name__, exc_info=error, extra=extra)
