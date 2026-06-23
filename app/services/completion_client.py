import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

import requests

from app.services.json_response import parse_json_response
from app.services.llm_output_schemas import response_schema_for_task
from app.services.model_targets import ModelTarget, target_label
from app.services.observability import get_observability
from app.services.prompt_loader import PromptLoader
from app.services.text_utils import clean_text


LOGGER = logging.getLogger("meeting_recap_webapp.completion")


@dataclass(frozen=True)
class CompletionResult:
    text: str
    metadata: dict[str, Any]
    usage_details: dict[str, int]


class CompletionClient:
    def __init__(self, timeout_seconds: float = 90.0):
        self.timeout_seconds = timeout_seconds

    def complete(
        self,
        target: ModelTarget,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float = 0.0,
        response_schema: dict[str, Any] | None = None,
    ) -> CompletionResult:
        url, headers, payload = build_completion_request(target, prompt, system_prompt, max_tokens, temperature, response_schema)
        started = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=(10, self.timeout_seconds))
        http_wall_seconds = time.time() - started
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
        response_payload = response.json()
        return CompletionResult(
            text=extract_completion_text(response_payload),
            metadata=extract_ollama_response_metadata(response_payload, http_wall_seconds=http_wall_seconds),
            usage_details=extract_ollama_usage_details(response_payload),
        )


class JsonCompletionRunner:
    def __init__(
        self,
        client: CompletionClient,
        retry_attempts: int = 2,
        retry_sleep: float = 1.0,
        observability: Any | None = None,
    ):
        self.client = client
        self.retry_attempts = retry_attempts
        self.retry_sleep = retry_sleep
        self.observability = observability or get_observability()
        self.trace_context: dict[str, str] | None = None

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
        runs: list[dict[str, Any]] = []
        system = system_prompt or PromptLoader.get_prompt("system_prompt")
        schema = response_schema if response_schema is not None else response_schema_for_task(task_name)
        for target in targets:
            label = target_label(target)
            started = time.time()
            last_error = ""
            for attempt in range(1, self.retry_attempts + 1):
                generation_input = build_generation_input(system, prompt, schema)
                generation_metadata = build_generation_metadata(target, task_name, attempt, max_tokens, temperature)
                try:
                    with self.observability.start_generation(
                        name=task_name,
                        input=generation_input,
                        model=target.model,
                        model_parameters={"temperature": temperature, "max_tokens": max_tokens},
                        metadata=generation_metadata,
                        trace_context=self.trace_context,
                    ) as generation:
                        try:
                            completion = normalize_completion_result(
                                self.client.complete(
                                    target,
                                    prompt,
                                    system,
                                    max_tokens,
                                    temperature,
                                    response_schema=schema,
                                )
                            )
                            raw = completion.text
                            parsed = parse_json_response(raw)
                            duration_seconds = round(time.time() - started, 2)
                            update_payload: dict[str, Any] = {
                                "output": parsed,
                                "metadata": {
                                    **generation_metadata,
                                    "request_total_seconds": duration_seconds,
                                    "model_output_text_preview": raw[:1000],
                                    **completion.metadata,
                                },
                            }
                            if completion.usage_details:
                                update_payload["usage_details"] = completion.usage_details
                            generation.update(**update_payload)
                            run = {
                                "task": task_name,
                                "target": label,
                                "model": target.model,
                                "parsed": parsed,
                                "raw_preview": raw[:1000],
                                "error": "",
                                "attempts": attempt,
                                "duration_seconds": duration_seconds,
                                "provider_metadata": completion.metadata,
                                "usage_details": completion.usage_details,
                            }
                            run.update(generation.public_ids())
                            runs.append(run)
                        except Exception as error:
                            last_error = clean_text(error)
                            generation.update(
                                level="ERROR",
                                status_message=last_error,
                                metadata={**generation_metadata, "request_total_seconds": round(time.time() - started, 2)},
                            )
                            raise
                    LOGGER.info("%s completed by %s", task_name, label)
                    break
                except Exception as error:
                    if not last_error:
                        last_error = clean_text(error)
                    LOGGER.warning("%s failed on %s attempt %s: %s", task_name, label, attempt, last_error)
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_sleep * attempt)
            else:
                run = empty_run(task_name, target, last_error)
                run["attempts"] = self.retry_attempts
                run["duration_seconds"] = round(time.time() - started, 2)
                runs.append(run)
        return runs


def normalize_completion_result(value: Any) -> CompletionResult:
    if isinstance(value, CompletionResult):
        return value
    return CompletionResult(text=str(value), metadata={}, usage_details={})


def extract_ollama_response_metadata(payload: dict[str, Any], *, http_wall_seconds: float) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    duration_fields = {
        "load_duration": "model_load_seconds",
        "prompt_eval_duration": "prompt_processing_seconds",
        "eval_duration": "output_generation_seconds",
    }
    for source_field, metadata_field in duration_fields.items():
        if source_field in payload:
            metadata[metadata_field] = nanoseconds_to_seconds(payload.get(source_field))

    prompt_processing_seconds = float(metadata.get("prompt_processing_seconds", 0.0) or 0.0)
    output_generation_seconds = float(metadata.get("output_generation_seconds", 0.0) or 0.0)
    if "prompt_processing_seconds" in metadata or "output_generation_seconds" in metadata:
        metadata["active_model_compute_seconds"] = round(prompt_processing_seconds + output_generation_seconds, 3)

    model_server_total_seconds = nanoseconds_to_seconds(payload.get("total_duration")) if "total_duration" in payload else None
    if isinstance(model_server_total_seconds, (int, float)):
        load_seconds = float(metadata.get("model_load_seconds", 0.0) or 0.0)
        accounted_seconds = load_seconds + prompt_processing_seconds + output_generation_seconds
        metadata["server_wait_or_overhead_seconds"] = round(max(0.0, float(model_server_total_seconds) - accounted_seconds), 3)

    if "prompt_eval_count" in payload:
        metadata["input_tokens"] = payload.get("prompt_eval_count")
    if "eval_count" in payload:
        metadata["output_tokens"] = payload.get("eval_count")
    if payload.get("created_at"):
        metadata["response_created_at"] = payload.get("created_at")
    if payload.get("done_reason"):
        metadata["finish_reason"] = payload.get("done_reason")
    if "done" in payload:
        metadata["completed"] = bool(payload.get("done"))

    message = payload.get("message")
    if isinstance(message, dict):
        content = str(message.get("content") or "")
        thinking = str(message.get("thinking") or "")
        metadata["output_chars"] = len(content)
        if thinking:
            metadata["thinking_chars"] = len(thinking)

    return metadata


def extract_ollama_usage_details(payload: dict[str, Any]) -> dict[str, int]:
    usage: dict[str, int] = {}
    prompt_tokens = int_value(payload.get("prompt_eval_count"))
    completion_tokens = int_value(payload.get("eval_count"))
    if prompt_tokens is not None:
        usage["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        usage["completion_tokens"] = completion_tokens
    if prompt_tokens is not None and completion_tokens is not None:
        usage["total_tokens"] = prompt_tokens + completion_tokens
    return usage


def nanoseconds_to_seconds(value: Any) -> float:
    try:
        return round(float(value) / 1_000_000_000, 3)
    except (TypeError, ValueError):
        return 0.0


def int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def empty_run(task_name: str, target: ModelTarget, error: str) -> dict[str, Any]:
    return {
        "task": task_name,
        "target": target_label(target),
        "model": target.model,
        "parsed": None,
        "raw_preview": "",
        "error": clean_text(error),
        "attempts": 0,
        "duration_seconds": 0,
        "langfuse_trace_id": "",
        "langfuse_observation_id": "",
    }


def build_generation_input(system_prompt: str, prompt: str, response_schema: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "response_schema": response_schema,
    }


def build_generation_metadata(
    target: ModelTarget,
    task_name: str,
    attempt: int,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    return {
        "task": task_name,
        "attempt": attempt,
        "target": target_label(target),
        "base_url": target.base_url or "",
        "max_tokens": max_tokens,
        "temperature": temperature,
    }


def build_completion_request(
    target: ModelTarget,
    prompt: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float,
    response_schema: dict[str, Any] | None = None,
) -> tuple[str, dict[str, str], dict[str, Any]]:
    base_url = (target.base_url or "").rstrip("/")
    if not base_url:
        raise RuntimeError("Local Ollama target has no base_url")
    url = f"{base_url}/api/chat"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": target.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "format": response_schema or "json",
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    return url, headers, payload


def extract_completion_text(payload: dict[str, Any]) -> str:
    if "message" in payload:
        return payload["message"]["content"]
    raise ValueError("Completion response did not include text content")


def complete_json_with_target_fallback(
    runner: JsonCompletionRunner,
    task_name: str,
    prompt: str,
    targets: list[ModelTarget],
    start_offset: int,
    max_tokens: int,
    success_predicate: Callable[[Any], bool] | None = None,
    response_schema: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not targets:
        return runner.complete_json_for_all(task_name, prompt, targets=[], max_tokens=max_tokens, response_schema=response_schema)
    target = targets[0]
    all_runs: list[dict[str, Any]] = []
    max_attempts = max(1, getattr(runner, "retry_attempts", 1))
    for _ in range(max_attempts):
        runs = runner.complete_json_for_all(task_name, prompt, targets=[target], max_tokens=max_tokens, response_schema=response_schema)
        all_runs.extend(runs)
        parsed = first_successful_parsed(runs)
        if parsed is not None and (success_predicate is None or success_predicate(parsed)):
            break
    return all_runs


def first_successful_parsed(runs: list[dict[str, Any]]) -> Any:
    for run in runs:
        if run.get("parsed") is not None and not run.get("error"):
            return run["parsed"]
    return None


def normalized_model_runs(task_name: str, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for run in runs:
        normalized.append(
            {
                "task": run.get("task") or task_name,
                "target": run.get("target", ""),
                "model": run.get("model", ""),
                "error": clean_text(run.get("error", "")),
                "attempts": run.get("attempts", 1),
                "duration_seconds": run.get("duration_seconds", 0),
                "provider_metadata": run.get("provider_metadata", {}),
                "usage_details": run.get("usage_details", {}),
                "raw_preview": run.get("raw_preview", ""),
                "langfuse_trace_id": run.get("langfuse_trace_id", ""),
                "langfuse_observation_id": run.get("langfuse_observation_id", ""),
            }
        )
    return normalized
