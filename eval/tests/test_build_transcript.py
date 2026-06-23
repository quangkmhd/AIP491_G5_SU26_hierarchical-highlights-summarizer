"""Tests for the transcript synthesizer."""

from eval.build_transcript import synthesize_transcript
from eval.load_segments import PairedSegment


def _pair(video: str, seg: int, transcript: str, duration: float = 10.0) -> PairedSegment:
    return PairedSegment(
        video_id=video,
        segment_number=seg,
        sherpa_transcript=transcript,
        soniox_transcript=transcript,
        duration_sec=duration,
    )


def test_synthesize_uses_provider_field_for_text():
    pairs = [_pair("vid01", 0, "CHUNG TA DI LAM", duration=5.0),
             _pair("vid01", 1, "HOM NAY DEP", duration=3.0)]
    text = synthesize_transcript(pairs, provider="sherpa")
    assert "CHUNG TA DI LAM" in text
    assert "HOM NAY DEP" in text


def test_synthesize_handles_empty_input():
    assert synthesize_transcript([], provider="sherpa") == ""
    assert synthesize_transcript([], provider="soniox") == ""


def test_synthesize_keeps_segments_in_order():
    pairs = [_pair("vid01", 0, "AAA"),
             _pair("vid01", 1, "BBB"),
             _pair("vid01", 2, "CCC")]
    text = synthesize_transcript(pairs, provider="sherpa")
    a_pos = text.index("AAA")
    b_pos = text.index("BBB")
    c_pos = text.index("CCC")
    assert a_pos < b_pos < c_pos
