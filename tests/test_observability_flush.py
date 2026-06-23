import time
import unittest
from typing import Any

from app.services.recap_service import RecapService


class DummyRunner:
    trace_context: dict[str, str] | None = None


class DummyTrace:
    trace_id = "trace-id"
    observation_id = "observation-id"

    def __enter__(self) -> "DummyTrace":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def update(self, **kwargs: Any) -> None:
        return None

    def set_trace_io(self, *, input: Any | None = None, output: Any | None = None) -> None:
        return None

    def trace_context(self) -> dict[str, str]:
        return {"trace_id": self.trace_id, "parent_span_id": self.observation_id}


class AsyncOnlyObservability:
    enabled = True

    def __init__(self) -> None:
        self.flush_async_calls = 0

    def start_trace(self, **kwargs: Any) -> DummyTrace:
        return DummyTrace()

    def flush(self) -> None:
        raise AssertionError("request path must not block on synchronous Langfuse flush")

    def flush_async(self) -> None:
        self.flush_async_calls += 1


class BlockingFlushOnlyObservability:
    enabled = True

    def __init__(self) -> None:
        self.flush_calls = 0

    def start_trace(self, **kwargs: Any) -> DummyTrace:
        return DummyTrace()

    def flush(self) -> None:
        self.flush_calls += 1
        time.sleep(0.05)


class ObservabilityFlushTests(unittest.TestCase):
    def test_summarize_uses_async_flush_when_available(self) -> None:
        observability = AsyncOnlyObservability()
        service = RecapService(runner=DummyRunner(), observability=observability)
        service._summarize = lambda transcript, method, input_name: {
            "input_name": input_name,
            "method": method,
            "utterance_count": 0,
            "model_targets": [],
            "results": {},
        }

        service.summarize("", method="highlights", input_name="flush-test.md")

        self.assertEqual(observability.flush_async_calls, 1)

    def test_summarize_falls_back_to_sync_flush_for_older_observability(self) -> None:
        observability = BlockingFlushOnlyObservability()
        service = RecapService(runner=DummyRunner(), observability=observability)
        service._summarize = lambda transcript, method, input_name: {
            "input_name": input_name,
            "method": method,
            "utterance_count": 0,
            "model_targets": [],
            "results": {},
        }

        service.summarize("", method="highlights", input_name="flush-test.md")

        self.assertEqual(observability.flush_calls, 1)


if __name__ == "__main__":
    unittest.main()
