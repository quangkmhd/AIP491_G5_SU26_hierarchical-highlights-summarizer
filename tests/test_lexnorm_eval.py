"""Tests for the lexnorm evaluator (WER/CER + confusion matrix)."""

import pytest

from app.services.lexnorm.evaluator import (
    LexnormEvaluator,
    aggregate_metrics,
    classify_token_transition,
    normalize_text,
)


def test_normalize_text_lowercases_and_strips_punctuation():
    assert normalize_text("Xin CHAO, ban!") == "xin chao ban"


def test_normalize_text_collapses_whitespace():
    assert normalize_text("  xin   chao   ban  ") == "xin chao ban"


def test_classify_token_transition_tp_when_raw_differs_and_corrected_matches_truth():
    assert classify_token_transition(raw="do ploi", corrected="deploy", truth="deploy") == "TP"


def test_classify_token_transition_fn_when_raw_differs_and_corrected_keeps_raw():
    assert classify_token_transition(raw="do ploi", corrected="do ploi", truth="deploy") == "FN"


def test_classify_token_transition_fp1_when_raw_matches_truth_and_corrected_differs():
    assert classify_token_transition(raw="deploy", corrected="deploi", truth="deploy") == "FP1"


def test_classify_token_transition_fp2_when_all_three_differ():
    assert classify_token_transition(raw="do ploi", corrected="deploi", truth="deploy") == "FP2"


def test_aggregate_metrics_sums_confusion_matrix():
    categories = ["TP", "FN", "FP1", "FP2", "TP", "FN", "FP1"]
    metrics = aggregate_metrics(
        wer_raw=0.3,
        wer_corrected=0.2,
        cer_raw=0.25,
        cer_corrected=0.15,
        categories=categories,
        latency_ms_values=[100, 200, 300],
    )
    assert metrics["tp"] == 2
    assert metrics["fn"] == 2
    assert metrics["fp1"] == 2
    assert metrics["fp2"] == 1
    assert metrics["total_tokens"] == 7
    assert metrics["wer_delta"] == pytest.approx(-0.1)
    assert metrics["cer_delta"] == pytest.approx(-0.1)
    assert metrics["latency_ms_total"] == 600
    assert metrics["latency_ms_mean"] == 200


def test_evaluator_runs_against_three_sentences():
    evaluator = LexnormEvaluator()
    raw = ["do ploi he thong", "chi dung cho may tinh", "OK chung ta di"]
    truth = ["deploy he thong", "chi dung cho may tinh", "OK chung ta di"]
    corrected = ["deploy he thong", "chi dung cho may tinh", "OK chung ta di"]
    result = evaluator.evaluate(raw, corrected, truth, latency_ms_values=[100, 100, 100])
    assert "wer_raw" in result
    assert "wer_corrected" in result
    assert "cer_raw" in result
    assert "cer_corrected" in result
    assert "tp" in result
    assert "fn" in result
    assert "fp1" in result
    assert "fp2" in result
    assert result["tp"] >= 1
    assert result["wer_delta"] <= 0
