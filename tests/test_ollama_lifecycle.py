from collections import OrderedDict
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

    def public_ids(self) -> dict[str, str]:
        return {"langfuse_trace_id": self.trace_id, "langfuse_observation_id": self.observation_id}


class DummyObservability:
    enabled = False

    def start_trace(self, **kwargs: Any) -> DummyTrace:
        return DummyTrace()

    def flush_async(self) -> None:
        return None


class RecordingLifecycle:
    def __init__(self) -> None:
        self.begin_models: list[list[str]] = []
        self.end_models: list[list[str]] = []

    def begin_run(self, targets: list[Any]) -> None:
        self.begin_models.append([target.model for target in targets])

    def end_run(self, targets: list[Any]) -> None:
        self.end_models.append([target.model for target in targets])


class FakeHighlightsMethod:
    name = "highlights"

    def summarize(self, utterances: list[Any], runner: Any, targets: list[Any], input_name: str) -> dict[str, Any]:
        return {"method": self.name, "notes": [], "tasks": [], "model_runs": []}


def make_service(lifecycle: RecordingLifecycle) -> RecapService:
    service = RecapService(
        runner=DummyRunner(),
        observability=DummyObservability(),
        ollama_lifecycle=lifecycle,
    )
    service.methods = OrderedDict([("highlights", FakeHighlightsMethod())])
    return service


def test_summarize_starts_and_stops_ollama_lifecycle() -> None:
    lifecycle = RecordingLifecycle()
    service = make_service(lifecycle)

    service.summarize("Lan(09:00 - 09:01):\nChot viec.", method="highlights", input_name="lifecycle.md")

    assert lifecycle.begin_models == [["qwen3.5:4b-q4_K_M"]]
    assert lifecycle.end_models == [["qwen3.5:4b-q4_K_M"]]


def test_summarize_stream_stops_ollama_lifecycle_after_completed_event() -> None:
    lifecycle = RecordingLifecycle()
    service = make_service(lifecycle)

    events = list(service.summarize_stream("Lan(09:00 - 09:01):\nChot viec.", method="highlights", input_name="stream.md"))

    assert [event["event"] for event in events] == ["started", "method_started", "method_completed", "completed"]
    assert lifecycle.begin_models == [["qwen3.5:4b-q4_K_M"]]
    assert lifecycle.end_models == [["qwen3.5:4b-q4_K_M"]]
