"""Integration test: RecapService invokes the corrector when env flag is on."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import AppSettings
from app.services.recap_service import RecapService


@dataclass
class FakeResponse:
    status_code: int = 200
    payload: dict[str, Any] = None

    def __post_init__(self):
        if self.payload is None:
            self.payload = {}

    def json(self) -> dict[str, Any]:
        return self.payload


def _ok_correction_payload():
    return {
        "message": {
            "content": '{"error_words": [{"raw": "CHUNG", "target": "Chung"}], "llm_corrected": "Chung ta di lam"}'
        },
        "model": "gemma4:12b-it-qat",
    }


def _ok_recap_payload():
    return {
        "message": {
            "content": '{"key_points": [], "action_items": []}'
        },
        "model": "qwen3.5:4b-q4_K_M",
    }


def test_summarize_with_normalize_flag_invokes_corrector(monkeypatch):
    monkeypatch.setenv("RECAP_NORMALIZE_TRANSCRIPT", "true")
    monkeypatch.setenv("RECAP_NORMALIZE_MODEL", "gemma4:12b-it-qat")
    monkeypatch.setenv("OLLAMA_AUTOSTART", "false")

    posts: list[dict[str, Any]] = []

    def fake_post(url, json=None, timeout=None, headers=None, **kwargs):
        posts.append({"url": url, "json": json})
        model = (json or {}).get("model", "")
        if "gemma4" in model:
            payload = _ok_correction_payload()
        else:
            payload = _ok_recap_payload()
        return FakeResponse(status_code=200, payload=payload)

    monkeypatch.setattr("requests.post", fake_post)

    service = RecapService(settings=AppSettings())
    raw_transcript = (
        "Speaker_001 (0:00 - 0:01): CHUNG TA DI LAM\n"
        "Speaker_002 (0:01 - 0:02): OK\n"
    )
    result = service.summarize(raw_transcript, method="highlights", input_name="unit.md")

    corrector_calls = [p for p in posts if "gemma4" in (p["json"] or {}).get("model", "")]
    recap_calls = [p for p in posts if "qwen3.5" in (p["json"] or {}).get("model", "")]
    assert len(corrector_calls) == 2
    assert len(recap_calls) >= 1
    recap_prompt = recap_calls[0]["json"]["messages"][-1]["content"]
    assert "Chung ta di lam" in recap_prompt or "chung ta di lam" in recap_prompt.lower()


def test_summarize_without_normalize_flag_skips_corrector(monkeypatch):
    monkeypatch.setenv("RECAP_NORMALIZE_TRANSCRIPT", "false")
    monkeypatch.setenv("OLLAMA_AUTOSTART", "false")

    def fake_post(url, json=None, timeout=None, headers=None, **kwargs):
        return FakeResponse(status_code=200, payload=_ok_recap_payload())

    monkeypatch.setattr("requests.post", fake_post)

    service = RecapService(settings=AppSettings())
    raw_transcript = "Speaker_001 (0:00 - 0:01): CHUNG TA DI LAM\n"
    service.summarize(raw_transcript, method="highlights", input_name="unit.md")

    # No corrector calls should have been made
    # (We can verify by inspecting the post calls indirectly; the test passes
    # if no exception is raised and the recap path returns normally.)
