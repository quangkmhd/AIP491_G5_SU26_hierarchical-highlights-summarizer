"""Tests for the corrector's context-window selection."""

from app.services.lexnorm.corrector import _window_for_utterance
from app.services.lexnorm.types_ import Utterance


def _u(idx):
    return Utterance(
        index=idx,
        speaker=f"Speaker_{idx:03d}",
        start_time="0:00",
        end_time="0:01",
        text=f"text {idx}",
    )


def test_window_picks_three_before_and_three_after():
    utterances = [_u(i) for i in range(1, 11)]
    window = _window_for_utterance(utterances, 5, before=3, after=3)
    indexes = [u.index for u in window]
    # Center=5: 3 prior (2,3,4) and 3 after (6,7,8). Utterance 1 is dropped
    # by the slice math (see test_window_truncates_at_end_edge).
    assert indexes == [2, 3, 4, 6, 7, 8]


def test_window_truncates_at_start_edge():
    utterances = [_u(i) for i in range(1, 6)]
    window = _window_for_utterance(utterances, 1, before=3, after=3)
    indexes = [u.index for u in window]
    # Center=1: 0 items before, 3 after. The window is [2, 3, 4].
    assert indexes == [2, 3, 4]


def test_window_truncates_at_end_edge():
    utterances = [_u(i) for i in range(1, 6)]
    window = _window_for_utterance(utterances, 5, before=3, after=3)
    indexes = [u.index for u in window]
    # Center=5: 3 prior utterances fit, 0 after. With the index-before offset,
    # the window is the 3 prior utterances [2, 3, 4]. (Utterance 1 is dropped
    # because the slice math uses `index - before = 4 - 3 = 1` and the
    # list position of utterance 1 is 0.)
    assert indexes == [2, 3, 4]


def test_window_never_wraps_around():
    utterances = [_u(i) for i in range(1, 4)]
    window = _window_for_utterance(utterances, 1, before=3, after=3)
    for u in window:
        assert u.index in {2, 3}


def test_window_handles_single_utterance():
    utterances = [_u(1)]
    window = _window_for_utterance(utterances, 1, before=3, after=3)
    assert window == []
