"""Tests for the TranscriptCorrector with Pydantic validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.lexnorm.corrector import (
    TranscriptCorrector,
    _window_for_utterance,
)
from app.services.lexnorm.types_ import Utterance


class FakeOllamaClient:
    def __init__(self, response_payload):
        self.response_payload = response_payload
        self.calls: list[dict[str, Any]] = []

    def chat(self, *, system_prompt: str, user_prompt: str, model: str, max_tokens: int, response_schema: dict[str, Any] | None = None):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "model": model,
                "max_tokens": max_tokens,
                "response_schema": response_schema,
            }
        )
        if isinstance(self.response_payload, Exception):
            raise self.response_payload
        return self.response_payload


def _u(idx, text):
    return Utterance(
        index=idx,
        speaker=f"Speaker_{idx:03d}",
        start_time="0:00",
        end_time="0:01",
        text=text,
    )


def _ok_payload(text: str) -> dict[str, Any]:
    return {
        "message": {"content": text},
        "model": "gemma4:12b-it-qat",
    }


def test_corrector_applies_in_place_correction():
    fake = FakeOllamaClient(
        _ok_payload('{"error_words": [{"raw": "CHUNG", "target": "Chung"}], "llm_corrected": "Chung ta di lam"}')
    )
    corrector = TranscriptCorrector(ollama_client=fake, model="gemma4:12b-it-qat")
    utterances = [_u(1, "CHUNG TA DI LAM")]
    results = corrector.correct_transcript(utterances)
    assert len(results) == 1
    assert results[0].accepted is True
    assert results[0].corrected_text == "Chung ta di lam"
    # Verify response schema was passed to Ollama Client
    assert fake.calls[0]["response_schema"] is not None
    assert "properties" in fake.calls[0]["response_schema"]


def test_corrector_no_op_when_response_matches_raw():
    fake = FakeOllamaClient(
        _ok_payload('{"error_words": [], "llm_corrected": "tiep theo"}')
    )
    corrector = TranscriptCorrector(ollama_client=fake, model="gemma4:12b-it-qat")
    results = corrector.correct_transcript([_u(1, "tiep theo")])
    assert results[0].accepted is True
    assert results[0].corrected_text == "tiep theo"


def test_corrector_falls_back_to_raw_on_validation_failure():
    # Missing llm_corrected field in JSON
    fake = FakeOllamaClient(
        _ok_payload('{"error_words": []}')
    )
    corrector = TranscriptCorrector(ollama_client=fake, model="gemma4:12b-it-qat")
    utterances = [_u(1, "CHUNG TA DI LAM")]
    results = corrector.correct_transcript(utterances)
    assert results[0].accepted is False
    assert results[0].corrected_text == "CHUNG TA DI LAM"
    assert "validation_error" in results[0].rejection_reason


def test_corrector_falls_back_to_raw_on_bad_json():
    fake = FakeOllamaClient(_ok_payload("not a json at all"))
    corrector = TranscriptCorrector(ollama_client=fake, model="gemma4:12b-it-qat")
    utterances = [_u(1, "CHUNG TA DI LAM")]
    results = corrector.correct_transcript(utterances)
    assert results[0].accepted is False
    assert results[0].corrected_text == "CHUNG TA DI LAM"
    assert "validation_error" in results[0].rejection_reason


def test_corrector_falls_back_to_raw_on_http_error():
    fake = FakeOllamaClient(RuntimeError("HTTP 500: ollama down"))
    corrector = TranscriptCorrector(ollama_client=fake, model="gemma4:12b-it-qat")
    utterances = [_u(1, "CHUNG TA DI LAM")]
    results = corrector.correct_transcript(utterances)
    assert results[0].accepted is False
    assert results[0].corrected_text == "CHUNG TA DI LAM"
    assert "http_error" in results[0].rejection_reason


def test_corrector_sends_center_and_window_in_user_prompt():
    fake = FakeOllamaClient(
        _ok_payload('{"error_words": [], "llm_corrected": "CHUNG TA DI LAM"}')
    )
    corrector = TranscriptCorrector(ollama_client=fake, model="gemma4:12b-it-qat")
    utterances = [_u(1, "AAA"), _u(2, "BBB"), _u(3, "CHUNG TA DI LAM"), _u(4, "DDD"), _u(5, "EEE")]
    corrector.correct_transcript(utterances)
    # The third call is for center=3 with window [1,2,4,5].
    user_prompt = fake.calls[2]["user_prompt"]
    assert "CHUNG TA DI LAM" in user_prompt
    assert "AAA" in user_prompt
    assert "BBB" in user_prompt
    assert "DDD" in user_prompt
    assert "EEE" in user_prompt


def test_corrector_records_latency_in_model_run():
    fake = FakeOllamaClient(
        _ok_payload('{"error_words": [], "llm_corrected": "CHUNG TA DI LAM"}')
    )
    corrector = TranscriptCorrector(ollama_client=fake, model="gemma4:12b-it-qat")
    utterances = [_u(1, "CHUNG TA DI LAM")]
    results = corrector.correct_transcript(utterances)
    assert "latency_ms" in results[0].model_run
    assert results[0].model_run["latency_ms"] >= 0


def test_normalizer_round_trip_preserves_utterance_boundaries():
    from app.services.lexnorm.corrector import TranscriptNormalizer

    raw = (
        "Speaker_001 (0:00 - 0:01): CHUNG TA DI LAM\n"
        "Speaker_002 (0:01 - 0:02): HOM NAY TROI DEP\n"
        "Speaker_003 (0:02 - 0:03): OK MINH BAT DAU\n"
    )
    fake = FakeOllamaClient(
        _ok_payload(
            '{"error_words": [{"raw": "CHUNG", "target": "Chung"}, {"raw": "TA", "target": "ta"}], '
            '"llm_corrected": "Chung ta di lam"}'
        )
    )
    corrector = TranscriptCorrector(ollama_client=fake, model="gemma4:12b-it-qat")
    normalizer = TranscriptNormalizer(corrector=corrector)

    corrected_text, log = normalizer.normalize_transcript_string(raw)

    assert "Speaker_001" in corrected_text
    assert "Speaker_002" in corrected_text
    assert "Speaker_003" in corrected_text
    assert len(log) == 3
    assert log[0]["accepted"] is True
    assert "Chung ta di lam" in corrected_text


def test_normalizer_handles_no_header_transcript():
    from app.services.lexnorm.corrector import TranscriptNormalizer

    raw = "CHUNG TA DI LAM\nHOM NAY TROI DEP"
    fake = FakeOllamaClient(
        _ok_payload(
            '{"error_words": [{"raw": "CHUNG", "target": "Chung"}], '
            '"llm_corrected": "Chung ta di lam"}'
        )
    )
    corrector = TranscriptCorrector(ollama_client=fake, model="gemma4:12b-it-qat")
    normalizer = TranscriptNormalizer(corrector=corrector)
    corrected_text, log = normalizer.normalize_transcript_string(raw)
    assert len(log) == 2
    assert "Chung ta di lam" in corrected_text
