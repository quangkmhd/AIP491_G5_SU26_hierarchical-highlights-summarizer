from collections import OrderedDict
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.config import AppSettings
from app.methods.highlights_recap import HighlightsRecapMethod
from app.methods.hierarchical_recap import HierarchicalRecapMethod
from app.methods.ssdst_recap import SsDstRecapMethod
from app.schemas import SummaryMethod
from app.services.completion_client import CompletionClient, JsonCompletionRunner
from app.services.model_targets import load_local_model_target, target_public_dict
from app.services.observability import get_observability
from app.services.ollama_lifecycle import OllamaLifecycle, get_ollama_lifecycle
from app.services.parallel import parallel_map_ordered
from app.services.text_utils import clean_text
from app.services.transcript_parser import parse_transcript


class RecapService:
    def __init__(
        self,
        settings: AppSettings | None = None,
        *,
        runner: JsonCompletionRunner | None = None,
        observability: Any | None = None,
        ollama_lifecycle: OllamaLifecycle | None = None,
    ):
        self.settings = settings or AppSettings()
        self.observability = observability or get_observability()
        self.ollama_lifecycle = ollama_lifecycle or get_ollama_lifecycle(self.settings)
        self.runner = runner or JsonCompletionRunner(
            CompletionClient(timeout_seconds=self.settings.request_timeout_seconds),
            retry_attempts=self.settings.retry_attempts,
            observability=self.observability,
        )
        self.methods = OrderedDict(
            [
                ("highlights", HighlightsRecapMethod()),
                ("hierarchical", HierarchicalRecapMethod()),
                ("ssdst", SsDstRecapMethod()),
            ]
        )

    def summarize(
        self,
        transcript: str,
        *,
        method: SummaryMethod = "both",
        input_name: str = "frontend-input.md",
    ) -> dict[str, Any]:
        trace_input = build_recap_trace_input(
            transcript,
            method=method,
            input_name=input_name,
        )
        with self.observability.start_trace(
            name="meeting recap",
            input=trace_input,
            metadata={"tool": "09-meeting-recap-webapp"},
        ) as trace:
            previous_trace_context = getattr(self.runner, "trace_context", None)
            if hasattr(self.runner, "trace_context"):
                self.runner.trace_context = trace.trace_context()
            try:
                result = self._summarize(transcript, method, input_name)
                result["langfuse_enabled"] = bool(getattr(self.observability, "enabled", False))
                result["langfuse_trace_id"] = trace.trace_id
                result["langfuse_observation_id"] = trace.observation_id
                trace_output = build_recap_trace_output(result)
                trace.update(output=trace_output)
                trace.set_trace_io(input=trace_input, output=trace_output)
                return result
            except Exception as error:
                trace.update(level="ERROR", status_message=clean_text(error))
                raise
            finally:
                if hasattr(self.runner, "trace_context"):
                    self.runner.trace_context = previous_trace_context
                if hasattr(self.observability, "flush_async"):
                    self.observability.flush_async()
                else:
                    self.observability.flush()

    def summarize_stream(
        self,
        transcript: str,
        *,
        method: SummaryMethod = "both",
        input_name: str = "frontend-input.md",
    ) -> Iterator[dict[str, Any]]:
        trace_input = build_recap_trace_input(
            transcript,
            method=method,
            input_name=input_name,
        )
        with self.observability.start_trace(
            name="meeting recap",
            input=trace_input,
            metadata={"tool": "09-meeting-recap-webapp", "streaming": True},
        ) as trace:
            previous_trace_context = getattr(self.runner, "trace_context", None)
            if hasattr(self.runner, "trace_context"):
                self.runner.trace_context = trace.trace_context()
            try:
                final_result: dict[str, Any] | None = None
                for event in self._summarize_stream(transcript, method, input_name):
                    if event.get("event") == "started":
                        event["data"].update(
                            {
                                "langfuse_enabled": bool(getattr(self.observability, "enabled", False)),
                                "langfuse_trace_id": trace.trace_id,
                                "langfuse_observation_id": trace.observation_id,
                            }
                        )
                    elif event.get("event") == "completed":
                        final_result = event["data"]
                        final_result["langfuse_enabled"] = bool(getattr(self.observability, "enabled", False))
                        final_result["langfuse_trace_id"] = trace.trace_id
                        final_result["langfuse_observation_id"] = trace.observation_id
                        trace_output = build_recap_trace_output(final_result)
                        trace.update(output=trace_output)
                        trace.set_trace_io(input=trace_input, output=trace_output)
                    yield event
                if final_result is None:
                    raise RuntimeError("Summary stream finished without a completed event")
            except Exception as error:
                message = clean_text(error)
                trace.update(level="ERROR", status_message=message)
                yield {"event": "error", "data": {"detail": message}}
            finally:
                if hasattr(self.runner, "trace_context"):
                    self.runner.trace_context = previous_trace_context
                if hasattr(self.observability, "flush_async"):
                    self.observability.flush_async()
                else:
                    self.observability.flush()

    def _maybe_normalize_transcript(self, transcript: str) -> tuple[str, list[dict[str, Any]]]:
        if not self.settings.recap_normalize_transcript:
            return transcript, []
        from app.services.lexnorm import TranscriptCorrector, TranscriptNormalizer
        from app.services.lexnorm.corrector import OllamaClient

        client = OllamaClient(
            base_url=self.settings.recap_normalize_base_url,
            timeout_seconds=self.settings.request_timeout_seconds,
        )
        corrector = TranscriptCorrector(
            ollama_client=client,
            model=self.settings.recap_normalize_model,
        )
        normalizer = TranscriptNormalizer(corrector=corrector)
        return normalizer.normalize_transcript_string(transcript)

    def _summarize(
        self,
        transcript: str,
        method: SummaryMethod,
        input_name: str,
    ) -> dict[str, Any]:
        transcript, _correction_log = self._maybe_normalize_transcript(transcript)
        utterances = parse_transcript(transcript)
        targets = [load_local_model_target()]
        results: OrderedDict[str, Any] = OrderedDict()
        method_names = self._selected_method_names(method)
        self.ollama_lifecycle.begin_run(targets)

        try:
            def run_method(method_name: str) -> tuple[str, Any]:
                return method_name, self.methods[method_name].summarize(utterances, self.runner, targets, input_name)

            for method_name, method_result in parallel_map_ordered(method_names, run_method):
                results[method_name] = method_result
            return {
                "input_name": input_name,
                "method": method,
                "utterance_count": len(utterances),
                "model_targets": [target_public_dict(target) for target in targets],
                "results": results,
            }
        finally:
            self.ollama_lifecycle.end_run(targets)

    def _summarize_stream(
        self,
        transcript: str,
        method: SummaryMethod,
        input_name: str,
    ) -> Iterator[dict[str, Any]]:
        transcript, _correction_log = self._maybe_normalize_transcript(transcript)
        utterances = parse_transcript(transcript)
        targets = [load_local_model_target()]
        method_names = self._selected_method_names(method)
        results: OrderedDict[str, Any] = OrderedDict()
        base_result = {
            "input_name": input_name,
            "method": method,
            "utterance_count": len(utterances),
            "model_targets": [target_public_dict(target) for target in targets],
            "langfuse_enabled": bool(getattr(self.observability, "enabled", False)),
            "langfuse_trace_id": "",
            "langfuse_observation_id": "",
            "results": results,
        }
        yield {"event": "started", "data": base_result}
        self.ollama_lifecycle.begin_run(targets)

        try:
            def run_method(method_name: str) -> tuple[str, Any]:
                return method_name, self.methods[method_name].summarize(utterances, self.runner, targets, input_name)

            for method_name in method_names:
                yield {"event": "method_started", "data": {"method": method_name}}

            if len(method_names) == 1:
                method_name, method_result = run_method(method_names[0])
                results[method_name] = method_result
                yield {"event": "method_completed", "data": {"method": method_name, "result": method_result}}
            elif method_names:
                with ThreadPoolExecutor(max_workers=len(method_names)) as executor:
                    future_to_method = {executor.submit(run_method, method_name): method_name for method_name in method_names}
                    for future in as_completed(future_to_method):
                        method_name, method_result = future.result()
                        results[method_name] = method_result
                        yield {"event": "method_completed", "data": {"method": method_name, "result": method_result}}

            ordered_results = OrderedDict((method_name, results[method_name]) for method_name in method_names if method_name in results)
            yield {
                "event": "completed",
                "data": {
                    "input_name": input_name,
                    "method": method,
                    "utterance_count": len(utterances),
                    "model_targets": [target_public_dict(target) for target in targets],
                    "langfuse_enabled": bool(getattr(self.observability, "enabled", False)),
                    "langfuse_trace_id": "",
                    "langfuse_observation_id": "",
                    "results": ordered_results,
                },
            }
        finally:
            self.ollama_lifecycle.end_run(targets)

    def _selected_method_names(self, method: SummaryMethod) -> list[str]:
        if method == "both":
            return list(self.methods.keys())
        return [method]


def build_recap_trace_input(
    transcript: str,
    *,
    method: SummaryMethod,
    input_name: str,
) -> dict[str, Any]:
    return {
        "input_name": input_name,
        "method": method,
        "transcript": transcript,
        "transcript_chars": len(transcript),
    }


def build_recap_trace_output(result: dict[str, Any]) -> dict[str, Any]:
    highlights = result.get("results", {}).get("highlights") or {}
    hierarchical = result.get("results", {}).get("hierarchical") or {}
    return {
        "input_name": result.get("input_name", ""),
        "method": result.get("method", ""),
        "utterance_count": result.get("utterance_count", 0),
        "notes": len(highlights.get("notes", [])),
        "tasks": len(highlights.get("tasks", [])),
        "chapters": len(hierarchical.get("chapters", [])),
        "model_run_count": len(highlights.get("model_runs", [])) + len(hierarchical.get("model_runs", [])),
    }
