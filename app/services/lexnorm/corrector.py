"""Per-utterance lexical corrector and transcript-level normalizer.

Public API:

    OllamaClient                -- thin HTTP wrapper around /api/chat.
    TranscriptCorrector         -- per-utterance corrector using OllamaClient.
    TranscriptNormalizer        -- full-transcript orchestrator (parse, run
                                   corrector, render).
    ModelUnavailableError       -- raised by TranscriptNormalizer when the
                                   configured model is not on the Ollama server.

The corrector is intentionally synchronous and one-call-per-utterance to
keep the integration simple and the correction log auditable.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from app.services.lexnorm.prompt import SYSTEM_PROMPT, build_user_prompt
from app.services.lexnorm.types_ import CorrectionResult, Utterance, CorrectionResponse


class ModelUnavailableError(RuntimeError):
    """Raised when the corrector model is not available on the Ollama server."""


class _OllamaLike(Protocol):
    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


@dataclass
class OllamaClient:
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 90.0
    connect_timeout_seconds: float = 10.0

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "think": False,
            "format": response_schema,
            "options": {
                "temperature": 0.0,
                "num_predict": max_tokens,
                "num_ctx": 2048,
            },
        }
        response = requests.post(
            url,
            json=payload,
            timeout=(self.connect_timeout_seconds, self.timeout_seconds),
        )
        if response.status_code == 404:
            raise ModelUnavailableError(
                f"Ollama at {self.base_url} returned 404 for model {model!r}. "
                f"Run `ollama pull {model}`."
            )
        if response.status_code >= 400:
            raise RuntimeError(
                f"HTTP {response.status_code} from {url}: {response.text[:500]}"
            )
        return response.json()


def _window_for_utterance(
    utterances: list[Utterance],
    utterance_id: int,
    *,
    before: int,
    after: int,
) -> list[Utterance]:
    index = max(0, utterance_id - 1)
    if index >= len(utterances):
        return []
    start = max(0, index - before)
    end = min(len(utterances), index + after + 1)
    return [u for u in utterances[start:end] if u.index != utterance_id]


@dataclass
class TranscriptCorrector:
    ollama_client: _OllamaLike
    model: str
    max_tokens: int = 512
    before: int = 3
    after: int = 3

    def correct_utterance(
        self, center: Utterance, context_utterances: list[Utterance]
    ) -> CorrectionResult:
        model_run: dict[str, Any] = {
            "target": self.model,
            "latency_ms": 0,
            "error": "",
        }
        if not center.text.strip():
            return CorrectionResult(
                utterance_id=center.index,
                raw_text=center.text,
                corrected_text="",
                accepted=True,
                rejection_reason="",
                model_run=model_run,
            )
        user_prompt = build_user_prompt(center, context_utterances)
        schema = CorrectionResponse.model_json_schema()
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                started = time.time()
                payload = self.ollama_client.chat(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    response_schema=schema,
                )
                latency = int((time.time() - started) * 1000)
                model_run["latency_ms"] += latency
            except ModelUnavailableError as exc:
                model_run["error"] = str(exc)
                return CorrectionResult(
                    utterance_id=center.index,
                    raw_text=center.text,
                    corrected_text=center.text,
                    accepted=False,
                    rejection_reason=f"model_unavailable:{exc}",
                    model_run=model_run,
                )
            except Exception as exc:
                model_run["error"] = f"attempt_{attempt}_http_error:{exc}"
                if attempt == max_attempts:
                    return CorrectionResult(
                        utterance_id=center.index,
                        raw_text=center.text,
                        corrected_text=center.text,
                        accepted=False,
                        rejection_reason=f"http_error:{exc}",
                        model_run=model_run,
                    )
                time.sleep(0.5 * attempt)
                continue

            message = payload.get("message", {}) if isinstance(payload, dict) else {}
            text = message.get("content", "") if isinstance(message, dict) else ""

            # Clean markdown code fences if present
            cleaned_text = text.strip()
            if cleaned_text.startswith("```"):
                cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

            try:
                parsed = CorrectionResponse.model_validate_json(cleaned_text)
                return CorrectionResult(
                    utterance_id=center.index,
                    raw_text=center.text,
                    corrected_text=parsed.llm_corrected,
                    accepted=True,
                    rejection_reason="",
                    model_run=model_run,
                )
            except Exception as exc:
                model_run["error"] = f"attempt_{attempt}_validation_error:{exc}"
                print(f"[WARNING] Attempt {attempt} validation failed for utterance U{center.index}: {exc}. Raw response: {cleaned_text!r}. Full payload: {payload}")
                import sys
                sys.stdout.flush()
                if attempt == max_attempts:
                    return CorrectionResult(
                        utterance_id=center.index,
                        raw_text=center.text,
                        corrected_text=center.text,
                        accepted=False,
                        rejection_reason=f"validation_error:{exc}",
                        model_run=model_run,
                    )
                time.sleep(0.5 * attempt)
                continue

    def correct_transcript(
        self,
        utterances: list[Utterance],
        *,
        max_workers: int = 4,
        on_result: Any | None = None,
        skipped_indices: set[int] | None = None,
    ) -> list[CorrectionResult]:
        """Run the corrector over all utterances.

        Results are returned in the same order as `utterances`. With
        `max_workers > 1` the corrector issues Ollama calls in parallel
        via a thread pool, but the final ordering is preserved.

        `on_result(result)` is invoked as soon as each utterance is
        corrected, allowing the caller to flush results to disk for
        crash-safety on long runs.
        """
        from concurrent.futures import ThreadPoolExecutor
        import threading

        results_by_id: dict[int, CorrectionResult] = {}
        index_lock = threading.Lock()

        # Pre-populate skipped results
        if skipped_indices:
            for u in utterances:
                if u.index in skipped_indices:
                    results_by_id[u.index] = CorrectionResult(
                        utterance_id=u.index,
                        raw_text=u.text,
                        corrected_text=u.text,
                        accepted=False,
                        rejection_reason="skipped",
                        model_run={"target": self.model, "latency_ms": 0, "error": ""},
                    )

        def run_one(center: Utterance) -> CorrectionResult:
            window = _window_for_utterance(
                utterances, center.index, before=self.before, after=self.after
            )
            res = self.correct_utterance(center, window)
            finalize(res)
            return res

        def finalize(result: CorrectionResult) -> None:
            with index_lock:
                results_by_id[result.utterance_id] = result
            if on_result is not None:
                try:
                    on_result(result)
                except Exception:
                    pass

        if max_workers <= 1:
            for u in utterances:
                if skipped_indices and u.index in skipped_indices:
                    continue
                run_one(u)
            return [results_by_id[u.index] for u in utterances]

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(run_one, u) for u in utterances 
                if not (skipped_indices and u.index in skipped_indices)
            ]
            for fut in futures:
                fut.result()
        return [results_by_id[u.index] for u in utterances]


@dataclass
class TranscriptNormalizer:
    corrector: TranscriptCorrector
    max_workers: int = 1

    def normalize_transcript_string(
        self,
        transcript: str,
        *,
        on_correction: Any | None = None,
        skipped_indices: set[int] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Run the corrector over each utterance in the transcript.

        Returns the corrected transcript (same header format, with each
        utterance's text replaced by its normalized version) and a
        per-utterance correction log. If parsing the transcript produces no
        utterances, the raw text is returned unchanged and the log is empty.

        `on_correction(correction_dict)` is invoked for each result as soon
        as the corrector finishes that utterance, allowing the caller to
        flush results to disk for crash-safety on long runs.
        """
        from app.services.lexnorm.types_ import Utterance as _LexUtterance
        from app.services.transcript_parser import (
            Utterance as _T9Utterance,
            parse_transcript as _parse_tool09,
        )

        t9_utterances: list[_T9Utterance] = _parse_tool09(transcript)
        if not t9_utterances:
            return transcript, []

        lex_utterances: list[_LexUtterance] = [
            _LexUtterance(
                index=u.index,
                speaker=u.speaker,
                start_time=u.start_time,
                end_time=u.end_time,
                text=u.text,
            )
            for u in t9_utterances
        ]

        def to_dict(r) -> dict[str, Any]:
            return {
                "utterance_id": r.utterance_id,
                "raw": r.raw_text,
                "corrected": r.corrected_text,
                "accepted": r.accepted,
                "rejection_reason": r.rejection_reason,
                "model_run": r.model_run,
            }

        log: list[dict[str, Any]] = []

        def on_result(r) -> None:
            entry = to_dict(r)
            log.append(entry)
            if on_correction is not None:
                try:
                    on_correction(entry)
                except Exception as exc:
                    import logging
                    logging.getLogger("lexnorm").warning(
                        "on_correction callback failed for utterance %s: %s",
                        entry["utterance_id"], exc,
                    )

        results = self.corrector.correct_transcript(
            lex_utterances,
            max_workers=self.max_workers,
            on_result=on_result,
            skipped_indices=skipped_indices,
        )

        corrected_text_by_id: dict[int, str] = {
            r.utterance_id: r.corrected_text for r in results
        }
        rendered_lines: list[str] = []
        for u in t9_utterances:
            corrected_text = corrected_text_by_id.get(u.index, u.text)
            if u.start_time and u.end_time:
                rendered_lines.append(f"{u.speaker} ({u.start_time} - {u.end_time}): {corrected_text}")
            elif u.speaker and u.speaker != "Unknown":
                rendered_lines.append(f"{u.speaker}: {corrected_text}")
            else:
                rendered_lines.append(corrected_text)
        return "\n".join(rendered_lines), log
