import os
import unittest
from typing import Any

import app.methods.highlights_recap as highlights
from app.methods.highlights_recap import HighlightsRecapMethod
from app.services.completion_client import complete_json_with_target_fallback
import app.services.completion_client as completion_client
from app.services.llm_output_schemas import response_schema_for_task
from app.services.model_targets import ModelTarget, model_stage_max_workers
from app.services.transcript_parser import Utterance


def make_utterances(count: int) -> list[Utterance]:
    return [
        Utterance(
            index=index,
            speaker=f"Speaker {index}",
            start_time=f"00:{index:02d}",
            end_time=f"00:{index + 1:02d}",
            text=f"Utterance {index} content.",
        )
        for index in range(1, count + 1)
    ]


class RecordingRunner:
    retry_attempts = 3

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def complete_json_for_all(
        self,
        task_name: str,
        prompt: str,
        *,
        targets: list[ModelTarget],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "task_name": task_name,
                "prompt": prompt,
                "targets": list(targets),
                "max_tokens": max_tokens,
                "response_schema": response_schema,
            }
        )
        return [
            {
                "task": task_name,
                "target": targets[0].model if targets else "",
                "model": targets[0].model if targets else "",
                "parsed": {"utterance_id": len(self.calls), "is_key_point": False, "is_action_item": False},
                "raw_preview": "{}",
                "error": "",
                "attempts": 1,
                "duration_seconds": 0,
            }
        ]


class FixedRawClient:
    def complete(
        self,
        target: ModelTarget,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float = 0.0,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        return '{"utterance_id": 1, "is_key_point": true, "is_action_item": false}'


class FixedTimingClient:
    def complete(
        self,
        target: ModelTarget,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float = 0.0,
        response_schema: dict[str, Any] | None = None,
    ) -> Any:
        return completion_client.CompletionResult(
            text='{"utterance_id": 1, "is_key_point": true, "is_action_item": false}',
            metadata={
                "prompt_processing_seconds": 0.5,
                "output_generation_seconds": 1.25,
                "server_wait_or_overhead_seconds": 0.25,
                "output_tokens": 8,
            },
            usage_details={"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        )


class CapturingGeneration:
    def __init__(self, sink: dict[str, Any]) -> None:
        self.sink = sink

    def __enter__(self) -> "CapturingGeneration":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def update(self, **kwargs: Any) -> None:
        self.sink.update(kwargs)

    def public_ids(self) -> dict[str, str]:
        return {"langfuse_trace_id": "trace", "langfuse_observation_id": "obs"}


class CapturingObservability:
    def __init__(self) -> None:
        self.start_payload: dict[str, Any] = {}
        self.start_payloads: list[dict[str, Any]] = []
        self.update_payload: dict[str, Any] = {}

    def start_generation(self, **kwargs: Any) -> CapturingGeneration:
        self.start_payload = kwargs
        self.start_payloads.append(kwargs)
        return CapturingGeneration(self.update_payload)


class InvalidThenValidRunner(RecordingRunner):
    def complete_json_for_all(
        self,
        task_name: str,
        prompt: str,
        *,
        targets: list[ModelTarget],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        super().complete_json_for_all(
            task_name,
            prompt,
            targets=targets,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
            response_schema=response_schema,
        )
        parsed = {"ok": len(self.calls) >= 2}
        return [
            {
                "task": task_name,
                "target": targets[0].model,
                "model": targets[0].model,
                "parsed": parsed,
                "raw_preview": "{}",
                "error": "",
                "attempts": 1,
                "duration_seconds": 0,
            }
        ]


class AlwaysInvalidRunner(RecordingRunner):
    retry_attempts = 2

    def complete_json_for_all(
        self,
        task_name: str,
        prompt: str,
        *,
        targets: list[ModelTarget],
        max_tokens: int = 4096,
        temperature: float = 0.0,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        super().complete_json_for_all(
            task_name,
            prompt,
            targets=targets,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=system_prompt,
            response_schema=response_schema,
        )
        return [
            {
                "task": task_name,
                "target": targets[0].model,
                "model": targets[0].model,
                "parsed": {"ok": False},
                "raw_preview": "{}",
                "error": "",
                "attempts": 1,
                "duration_seconds": 0,
            }
        ]


class PaperAlignmentTests(unittest.TestCase):
    def test_single_extractive_prompt_helper_exists(self) -> None:
        self.assertTrue(hasattr(highlights, "build_single_extractive_prompt"))

    def test_highlights_extractive_runs_one_prompt_per_utterance(self) -> None:
        utterances = make_utterances(6)
        runner = RecordingRunner()
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        runs = HighlightsRecapMethod()._run_extractive_stage(utterances, runner, [target], "meeting.md")

        self.assertEqual(len(runner.calls), len(utterances))
        self.assertEqual(len(runs), len(utterances))
        prompts = "\n".join(call["prompt"] for call in runner.calls)
        for utterance in utterances:
            self.assertIn(f"Candidate center utterance IDs to classify: {utterance.index}", prompts)
        self.assertEqual({call["max_tokens"] for call in runner.calls}, {highlights.EXTRACTIVE_MAX_TOKENS})

    def test_highlight_stage_token_budgets_are_small_for_json_outputs(self) -> None:
        self.assertLessEqual(highlights.EXTRACTIVE_MAX_TOKENS, 128)
        self.assertLessEqual(highlights.ABSTRACTIVE_MAX_TOKENS, 384)

    def test_single_extractive_prompt_instructs_single_candidate_contract(self) -> None:
        utterances = make_utterances(3)
        window = highlights.build_highlights_extractive_windows(utterances)[1]

        prompt = highlights.build_single_extractive_prompt("meeting.md", window)

        self.assertIn("một center utterance duy nhất", prompt)
        self.assertIn('"is_key_point": true', prompt)
        self.assertIn('"is_action_item": false', prompt)
        self.assertIn("Không trả về `key_points` hoặc `action_items` dạng mảng", prompt)

    def test_highlights_extractive_schema_uses_single_boolean_contract(self) -> None:
        schema = response_schema_for_task("highlights_extractive")

        self.assertEqual(schema["type"], "object")
        self.assertIn("utterance_id", schema["properties"])
        self.assertIn("is_key_point", schema["properties"])
        self.assertIn("is_action_item", schema["properties"])
        self.assertNotIn("key_points", schema["properties"])
        self.assertNotIn("action_items", schema["properties"])

    def test_completion_trace_output_is_model_json_object(self) -> None:
        observability = CapturingObservability()
        runner = completion_client.JsonCompletionRunner(FixedRawClient(), retry_attempts=1, observability=observability)
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        runner.complete_json_for_all("highlights_extractive", "prompt", targets=[target], max_tokens=64)

        output = observability.update_payload["output"]
        self.assertEqual(
            output,
            {"utterance_id": 1, "is_key_point": True, "is_action_item": False},
        )
        self.assertNotIn("raw", output)
        self.assertNotIn("parsed", output)
        self.assertNotIn("raw_text", output)
        self.assertNotIn("parsed_json", output)
        metadata = observability.update_payload["metadata"]
        self.assertIn("model_output_text_preview", metadata)
        self.assertNotIn("raw_text_preview", metadata)

    def test_completion_trace_generation_name_is_task_name(self) -> None:
        observability = CapturingObservability()
        runner = completion_client.JsonCompletionRunner(FixedRawClient(), retry_attempts=1, observability=observability)
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        runner.complete_json_for_all("highlights_extractive", "prompt", targets=[target], max_tokens=64)

        self.assertEqual(observability.start_payload["name"], "highlights_extractive")
        self.assertEqual(observability.start_payload["metadata"]["task"], "highlights_extractive")

    def test_completion_trace_generation_names_match_all_stage_tasks(self) -> None:
        observability = CapturingObservability()
        runner = completion_client.JsonCompletionRunner(FixedRawClient(), retry_attempts=1, observability=observability)
        target = ModelTarget(model="paper-model", base_url="http://example.local")
        task_names = [
            "highlights_extractive",
            "highlights_abstractive",
            "hierarchical_title",
            "hierarchical_abstractive",
        ]

        for task_name in task_names:
            runner.complete_json_for_all(task_name, "prompt", targets=[target], max_tokens=64)

        self.assertEqual([payload["name"] for payload in observability.start_payloads], task_names)
        self.assertEqual([payload["metadata"]["task"] for payload in observability.start_payloads], task_names)

    def test_model_timing_metadata_uses_readable_names(self) -> None:
        metadata = completion_client.extract_ollama_response_metadata(
            {
                "created_at": "2026-06-08T00:00:00Z",
                "done_reason": "stop",
                "total_duration": 2_000_000_000,
                "load_duration": 100_000_000,
                "prompt_eval_count": 12,
                "prompt_eval_duration": 500_000_000,
                "eval_count": 8,
                "eval_duration": 1_250_000_000,
                "message": {"thinking": "hidden reasoning sample", "content": "{}"},
            },
            http_wall_seconds=2.35,
        )

        self.assertEqual(metadata["model_load_seconds"], 0.1)
        self.assertEqual(metadata["prompt_processing_seconds"], 0.5)
        self.assertEqual(metadata["output_generation_seconds"], 1.25)
        self.assertEqual(metadata["active_model_compute_seconds"], 1.75)
        self.assertEqual(metadata["server_wait_or_overhead_seconds"], 0.15)
        self.assertEqual(metadata["input_tokens"], 12)
        self.assertEqual(metadata["output_tokens"], 8)
        self.assertEqual(metadata["finish_reason"], "stop")
        self.assertEqual(metadata["thinking_chars"], len("hidden reasoning sample"))
        self.assertNotIn("app_request_seconds", metadata)
        self.assertNotIn("prompt_to_output_seconds", metadata)
        self.assertNotIn("model_server_total_seconds", metadata)
        self.assertNotIn("app_network_overhead_seconds", metadata)
        self.assertFalse(any(key.startswith("ollama_") for key in metadata))

    def test_completion_trace_includes_model_timing_metadata_and_usage(self) -> None:
        observability = CapturingObservability()
        runner = completion_client.JsonCompletionRunner(FixedTimingClient(), retry_attempts=1, observability=observability)
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        runs = runner.complete_json_for_all("highlights_extractive", "prompt", targets=[target], max_tokens=64)

        metadata = observability.update_payload["metadata"]
        self.assertEqual(metadata["request_total_seconds"], runs[0]["duration_seconds"])
        self.assertEqual(metadata["prompt_processing_seconds"], 0.5)
        self.assertEqual(metadata["output_generation_seconds"], 1.25)
        self.assertNotIn("app_request_seconds", metadata)
        self.assertNotIn("prompt_to_output_seconds", metadata)
        self.assertNotIn("model_server_total_seconds", metadata)
        self.assertNotIn("app_network_overhead_seconds", metadata)
        self.assertFalse(any(key.startswith("ollama_") for key in metadata))
        self.assertEqual(observability.update_payload["usage_details"]["prompt_tokens"], 12)
        self.assertEqual(observability.update_payload["usage_details"]["completion_tokens"], 8)
        self.assertEqual(runs[0]["provider_metadata"]["output_tokens"], 8)

    def test_boolean_extractive_parser_selects_key_points_and_tasks(self) -> None:
        runs = [
            {"parsed": {"utterance_id": 2, "is_key_point": True, "is_action_item": False}},
            {"parsed": {"utterance_id": 3, "is_key_point": 0, "is_action_item": 1}},
            {"parsed": {"utterance_id": 99, "is_key_point": True, "is_action_item": True}},
        ]

        key_points, action_items = highlights.parse_extractive_candidates(runs, {1, 2, 3})

        self.assertEqual(key_points, [{"utterance_id": 2, "type": "key_point"}])
        self.assertEqual(action_items, [{"utterance_id": 3, "type": "action_item"}])

    def test_model_stage_default_parallelism_is_sequential_for_local_ollama(self) -> None:
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        existing = os.environ.pop("LLM_MAX_WORKERS", None)
        try:
            self.assertEqual(model_stage_max_workers([target]), 1)
        finally:
            if existing is not None:
                os.environ["LLM_MAX_WORKERS"] = existing

    def test_model_stage_parallelism_can_still_be_overridden_for_experiments(self) -> None:
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        existing = os.environ.get("LLM_MAX_WORKERS")
        os.environ["LLM_MAX_WORKERS"] = "4"
        try:
            self.assertEqual(model_stage_max_workers([target]), 4)
        finally:
            if existing is None:
                os.environ.pop("LLM_MAX_WORKERS", None)
            else:
                os.environ["LLM_MAX_WORKERS"] = existing

    def test_completion_retry_uses_same_single_target_and_original_prompt(self) -> None:
        runner = InvalidThenValidRunner()
        target = ModelTarget(model="paper-model", base_url="http://example.local")
        rotated_target = ModelTarget(model="rotated-model", base_url="http://example.local")

        runs = complete_json_with_target_fallback(
            runner,
            "paper_task",
            "original prompt",
            [target, rotated_target],
            start_offset=17,
            max_tokens=64,
            success_predicate=lambda parsed: bool(parsed.get("ok")),
        )

        self.assertEqual(len(runner.calls), 2)
        self.assertEqual([call["prompt"] for call in runner.calls], ["original prompt", "original prompt"])
        self.assertEqual([call["targets"] for call in runner.calls], [[target], [target]])
        self.assertTrue(runs[-1]["parsed"]["ok"])

    def test_completion_retry_returns_all_collected_runs_after_exhaustion(self) -> None:
        runner = AlwaysInvalidRunner()
        target = ModelTarget(model="paper-model", base_url="http://example.local")

        runs = complete_json_with_target_fallback(
            runner,
            "paper_task",
            "original prompt",
            [target],
            start_offset=0,
            max_tokens=64,
            success_predicate=lambda parsed: bool(parsed.get("ok")),
        )

        self.assertEqual(len(runner.calls), runner.retry_attempts)
        self.assertEqual(len(runs), runner.retry_attempts)
        self.assertEqual([run["parsed"] for run in runs], [{"ok": False}, {"ok": False}])
        self.assertEqual([run["target"] for run in runs], [target.model, target.model])


if __name__ == "__main__":
    unittest.main()
