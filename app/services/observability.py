import logging
import os
import threading
from typing import Any

from app.services.text_utils import clean_text


LOGGER = logging.getLogger("meeting_recap_webapp.observability")

_LANGFUSE_CLIENT: Any | None = None
_LANGFUSE_CLIENT_LOCK = threading.Lock()


class NoopObservation:
    trace_id: str = ""
    observation_id: str = ""

    def __enter__(self) -> "NoopObservation":
        return self

    def __exit__(self, exc_type: Any, exc: BaseException | None, traceback: Any) -> None:
        return None

    def update(self, **kwargs: Any) -> None:
        return None

    def set_trace_io(self, *, input: Any | None = None, output: Any | None = None) -> None:
        return None

    def trace_context(self) -> dict[str, str] | None:
        return None

    def public_ids(self) -> dict[str, str]:
        return {"langfuse_trace_id": "", "langfuse_observation_id": ""}


class LangfuseObservation:
    def __init__(self, context_manager: Any):
        self.context_manager = context_manager
        self.observation: Any | None = None
        self.trace_id = ""
        self.observation_id = ""

    def __enter__(self) -> "LangfuseObservation":
        self.observation = self.context_manager.__enter__()
        self.trace_id = str(getattr(self.observation, "trace_id", "") or "")
        self.observation_id = str(getattr(self.observation, "id", "") or "")
        return self

    def __exit__(self, exc_type: Any, exc: BaseException | None, traceback: Any) -> None:
        if exc is not None:
            self.update(level="ERROR", status_message=clean_text(exc))
        return self.context_manager.__exit__(exc_type, exc, traceback)

    def update(self, **kwargs: Any) -> None:
        if self.observation is None:
            return
        clean_kwargs = {key: value for key, value in kwargs.items() if value is not None}
        if not clean_kwargs:
            return
        self.observation.update(**clean_kwargs)

    def set_trace_io(self, *, input: Any | None = None, output: Any | None = None) -> None:
        if self.observation is None or not hasattr(self.observation, "set_trace_io"):
            return
        self.observation.set_trace_io(input=input, output=output)

    def trace_context(self) -> dict[str, str] | None:
        if not self.trace_id:
            return None
        context = {"trace_id": self.trace_id}
        if self.observation_id:
            context["parent_span_id"] = self.observation_id
        return context

    def public_ids(self) -> dict[str, str]:
        return {
            "langfuse_trace_id": self.trace_id,
            "langfuse_observation_id": self.observation_id,
        }


class NoopObservability:
    enabled = False

    def __init__(self, reason: str = ""):
        self.reason = reason

    def start_trace(self, **kwargs: Any) -> NoopObservation:
        return NoopObservation()

    def start_generation(self, **kwargs: Any) -> NoopObservation:
        return NoopObservation()

    def flush(self) -> None:
        return None

    def flush_async(self) -> None:
        return None


class LangfuseObservability:
    enabled = True

    def __init__(self, client: Any):
        self.client = client
        self._flush_lock = threading.Lock()
        self._flush_running = False

    def start_trace(self, *, name: str, input: Any, metadata: dict[str, Any] | None = None) -> LangfuseObservation:
        return LangfuseObservation(
            self.client.start_as_current_observation(
                as_type="span",
                name=name,
                input=input,
                metadata=metadata,
            )
        )

    def start_generation(
        self,
        *,
        name: str,
        input: Any,
        model: str,
        model_parameters: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        trace_context: dict[str, str] | None = None,
    ) -> LangfuseObservation:
        kwargs = {
            "as_type": "generation",
            "name": name,
            "input": input,
            "model": model,
            "model_parameters": model_parameters,
            "metadata": metadata,
        }
        if trace_context:
            kwargs["trace_context"] = trace_context
        return LangfuseObservation(self.client.start_as_current_observation(**kwargs))

    def flush(self) -> None:
        try:
            self.client.flush()
        except Exception as error:
            LOGGER.warning("Langfuse flush failed: %s", clean_text(error))

    def flush_async(self) -> None:
        if request_flush_should_block():
            self.flush()
            return
        with self._flush_lock:
            if self._flush_running:
                return
            self._flush_running = True
        thread = threading.Thread(target=self._flush_in_background, name="langfuse-flush", daemon=True)
        thread.start()

    def _flush_in_background(self) -> None:
        try:
            self.flush()
        finally:
            with self._flush_lock:
                self._flush_running = False


def get_observability() -> LangfuseObservability | NoopObservability:
    if not tracing_enabled():
        return NoopObservability("LANGFUSE_TRACING_ENABLED=false")
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return NoopObservability("missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY")

    client = get_langfuse_client()
    if client is None:
        return NoopObservability("Langfuse SDK unavailable or failed to initialize")
    return LangfuseObservability(client)


def tracing_enabled() -> bool:
    value = os.getenv("LANGFUSE_TRACING_ENABLED", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def request_flush_should_block() -> bool:
    value = os.getenv("LANGFUSE_FLUSH_ON_REQUEST", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_langfuse_client() -> Any | None:
    global _LANGFUSE_CLIENT
    with _LANGFUSE_CLIENT_LOCK:
        if _LANGFUSE_CLIENT is not None:
            return _LANGFUSE_CLIENT
        try:
            from langfuse import Langfuse

            _LANGFUSE_CLIENT = Langfuse()
        except Exception as error:
            LOGGER.warning("Langfuse initialization failed: %s", clean_text(error))
            _LANGFUSE_CLIENT = None
        return _LANGFUSE_CLIENT
