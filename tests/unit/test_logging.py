"""Unit tests for src.logging."""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.logging import (
    HumanFormatter,
    JsonFormatter,
    LoggableError,
    get_logger,
    log_error_with_fix,
    request_context,
)


class _CaptureHandler(logging.Handler):
    """Test handler that captures formatted log records and supports `with`."""

    def __init__(self, formatter: logging.Formatter) -> None:
        super().__init__()
        self.formatter = formatter
        self.records: list[str] = []
        self._logger: logging.Logger | None = None

    def attach(self, logger: logging.Logger) -> "_CaptureHandler":
        self._logger = logger
        logger.addHandler(self)
        return self

    def detach(self) -> None:
        if self._logger is not None:
            self._logger.removeHandler(self)

    def __enter__(self) -> "_CaptureHandler":
        return self

    def __exit__(self, *args: object) -> None:
        self.detach()

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.formatter.format(record))

def _capture(logger: logging.Logger, formatter: logging.Formatter) -> _CaptureHandler:
    """Module-level helper: attach a capture handler to `logger` and return it."""
    h = _CaptureHandler(formatter)
    h.attach(logger)
    return h



class LoggableErrorTests(unittest.TestCase):
    def test_carries_fix_and_hint(self) -> None:
        e = LoggableError("boom", fix="check the config", hint="see docs/QUALITY_SCORE.md")
        self.assertEqual(str(e), "boom")
        self.assertEqual(e.fix, "check the config")
        self.assertEqual(e.hint, "see docs/QUALITY_SCORE.md")

    def test_subclass_preserves_fields(self) -> None:
        class MyDomainError(LoggableError):
            pass

        e = MyDomainError("custom", fix="retry")
        self.assertIsInstance(e, LoggableError)
        self.assertEqual(e.fix, "retry")


class RequestContextTests(unittest.TestCase):
    def test_yields_request_id_when_not_given(self) -> None:
        with request_context(event="test") as rid:
            self.assertEqual(len(rid), 12)
        # Outside the context, the request_id should be reset
        logger = get_logger("src.test")
        with _capture(logger, HumanFormatter()) as h:
            logger.info("outside")
        self.assertIn("outside", h.records[0])
        self.assertNotIn(rid, h.records[0])  # the previous rid is gone

    def test_uses_provided_request_id(self) -> None:
        with request_context(request_id="my-custom-id", event="test") as rid:
            self.assertEqual(rid, "my-custom-id")
            logger = get_logger("src.test")
            with _capture(logger, HumanFormatter()) as h:
                logger.info("inside")
            self.assertIn("my-custom-id", h.records[0])
            self.assertIn("test", h.records[0])

    def test_resets_after_exception(self) -> None:
        logger = get_logger("src.test")
        try:
            with request_context(request_id="rid-A", event="evt-A"):
                raise ValueError("boom")
        except ValueError:
            pass
        with _capture(logger, HumanFormatter()) as h:
            logger.info("after")
        self.assertNotIn("rid-A", h.records[0])
        self.assertNotIn("evt-A", h.records[0])


class JsonFormatterTests(unittest.TestCase):
    def test_emits_valid_json_with_required_fields(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="src.test", level=logging.INFO, pathname="x.py", lineno=1,
            msg="hello %s", args=("world",), exc_info=None,
        )
        with request_context(request_id="abc123", event="evt"):
            line = formatter.format(record)
        obj = json.loads(line)
        self.assertEqual(obj["level"], "INFO")
        self.assertEqual(obj["logger"], "src.test")
        self.assertEqual(obj["message"], "hello world")
        self.assertEqual(obj["request_id"], "abc123")
        self.assertEqual(obj["event"], "evt")
        self.assertIn("ts", obj)

    def test_forwards_extra_fields(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="src.test", level=logging.INFO, pathname="x.py", lineno=1,
            msg="m", args=(), exc_info=None,
        )
        record.meeting_id = "m-123"
        record.fix = "retry"
        line = formatter.format(record)
        obj = json.loads(line)
        self.assertEqual(obj["meeting_id"], "m-123")
        self.assertEqual(obj["fix"], "retry")

    def test_silently_handles_non_serializable_extra(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="src.test", level=logging.INFO, pathname="x.py", lineno=1,
            msg="m", args=(), exc_info=None,
        )
        class Weird:
            def __repr__(self) -> str:
                return "<weird>"
        record.weird_obj = Weird()
        line = formatter.format(record)
        obj = json.loads(line)
        self.assertEqual(obj["weird_obj"], "<weird>")


class HumanFormatterTests(unittest.TestCase):
    def test_includes_logger_name(self) -> None:
        formatter = HumanFormatter()
        record = logging.LogRecord(
            name="src.svc.foo", level=logging.INFO, pathname="x.py", lineno=1,
            msg="hello", args=(), exc_info=None,
        )
        line = formatter.format(record)
        self.assertIn("[src.svc.foo]", line)
        self.assertIn("hello", line)
        self.assertIn("INFO", line)

    def test_omits_request_id_marker_when_no_context(self) -> None:
        formatter = HumanFormatter()
        record = logging.LogRecord(
            name="src.test", level=logging.INFO, pathname="x.py", lineno=1,
            msg="hi", args=(), exc_info=None,
        )
        line = formatter.format(record)
        # No request_id because no context was set
        self.assertNotIn("[rid-", line)


class LogErrorWithFixTests(unittest.TestCase):
    def test_uses_loggable_error_fix(self) -> None:
        logger = get_logger("src.test.fix")
        with _capture(logger, JsonFormatter()) as h:
            try:
                raise LoggableError("oops", fix="the fix")
            except LoggableError as e:
                log_error_with_fix(logger, e)
        obj = json.loads(h.records[0])
        self.assertEqual(obj["fix"], "the fix")
        self.assertEqual(obj["error_type"], "LoggableError")

    def test_accepts_explicit_fix_kwarg(self) -> None:
        logger = get_logger("src.test.fix2")
        with _capture(logger, JsonFormatter()) as h:
            try:
                raise ValueError("generic")
            except ValueError as e:
                log_error_with_fix(logger, e, fix="check input", hint="see docs")
        obj = json.loads(h.records[0])
        self.assertEqual(obj["fix"], "check input")
        self.assertEqual(obj["hint"], "see docs")
        self.assertEqual(obj["error_type"], "ValueError")

    def test_includes_request_id_in_log(self) -> None:
        logger = get_logger("src.test.fix3")
        with _capture(logger, JsonFormatter()) as h:
            with request_context(request_id="rid-fix", event="fix-test"):
                try:
                    raise LoggableError("e", fix="f")
                except LoggableError as e:
                    log_error_with_fix(logger, e)
        obj = json.loads(h.records[0])
        self.assertEqual(obj["request_id"], "rid-fix")
        self.assertEqual(obj["event"], "fix-test")


class GetLoggerTests(unittest.TestCase):
    def test_returns_named_logger(self) -> None:
        logger = get_logger("src.foo")
        self.assertEqual(logger.name, "src.foo")
