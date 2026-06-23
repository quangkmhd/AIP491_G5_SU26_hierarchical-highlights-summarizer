"""Tests for the lexnorm types module."""

from app.services.lexnorm.types_ import CorrectionResult, Utterance


def test_utterance_construction():
    u = Utterance(index=1, speaker="Speaker_001", start_time="0:00", end_time="0:16", text="Xin chao")
    assert u.index == 1
    assert u.speaker == "Speaker_001"
    assert u.text == "Xin chao"


def test_utterance_is_frozen():
    u = Utterance(index=1, speaker="S", start_time="", end_time="", text="x")
    try:
        u.text = "y"  # type: ignore[misc]
    except Exception as exc:
        assert "frozen" in str(exc).lower() or "FrozenInstanceError" in type(exc).__name__
    else:
        raise AssertionError("Utterance should be frozen")


def test_correction_result_construction():
    cr = CorrectionResult(
        utterance_id=1,
        raw_text="CHUNG TA",
        corrected_text="Chung ta",
        accepted=True,
        rejection_reason="",
        model_run={"target": "gemma4:12b-it-qat", "latency_ms": 1234, "error": ""},
    )
    assert cr.utterance_id == 1
    assert cr.accepted is True
    assert cr.model_run["latency_ms"] == 1234


def test_correction_result_rejected_has_reason():
    cr = CorrectionResult(
        utterance_id=2,
        raw_text="abc",
        corrected_text="abc",
        accepted=False,
        rejection_reason="paraphrase_detected",
        model_run={"target": "gemma4:12b-it-qat", "latency_ms": 0, "error": "parse_error"},
    )
    assert cr.accepted is False
    assert cr.rejection_reason == "paraphrase_detected"
