"""WER / CER + confusion matrix evaluator for the lexnorm corrector.

Reimplements the core logic from `tools/10-lexical-normalization/lexnorm/evaluator.py`
locally so tool 09 has no cross-tool import. The implementation uses
`jiwer` for WER/CER and a simple per-utterance token-level classification
for the TP / FN / FP1 / FP2 confusion matrix.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import jiwer


_WHITESPACE_RE = re.compile(r"\s+", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    """Lowercase, replace _/- with space, strip punctuation, collapse whitespace."""
    lowered = text.lower().replace("_", " ")
    cleaned = re.sub(r"[^\w\s-]", " ", lowered, flags=re.UNICODE)
    cleaned = cleaned.replace("-", " ")
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def _build_wer_transform() -> jiwer.Compose:
    return jiwer.Compose(
        [
            jiwer.ToLowerCase(),
            jiwer.SubstituteRegexes({r"[_-]": " ", r"[^\w\s]": " "}),
            jiwer.RemoveMultipleSpaces(),
            jiwer.Strip(),
            jiwer.ReduceToListOfListOfWords(),
        ]
    )


_WER_TRANSFORM = _build_wer_transform()
_CER_TRANSFORM = jiwer.Compose(
    [
        jiwer.ToLowerCase(),
        jiwer.SubstituteRegexes({r"[_\s-]": "", r"[^\w\s]": ""}),
        jiwer.RemoveMultipleSpaces(),
        jiwer.Strip(),
        jiwer.ReduceToListOfListOfChars(),
    ]
)


def _wer(reference: list[str], hypothesis: list[str]) -> float:
    filtered_pairs = [
        (ref, hyp) for ref, hyp in zip(reference, hypothesis)
        if ref.strip()
    ]
    if not filtered_pairs:
        return 0.0
    ref_list, hyp_list = zip(*filtered_pairs)
    out = jiwer.process_words(
        list(ref_list),
        list(hyp_list),
        reference_transform=_WER_TRANSFORM,
        hypothesis_transform=_WER_TRANSFORM,
    )
    return float(out.wer)


def _cer(reference: list[str], hypothesis: list[str]) -> float:
    filtered_pairs = [
        (ref, hyp) for ref, hyp in zip(reference, hypothesis)
        if ref.strip()
    ]
    if not filtered_pairs:
        return 0.0
    ref_list, hyp_list = zip(*filtered_pairs)
    out = jiwer.process_characters(
        list(ref_list),
        list(hyp_list),
        reference_transform=_CER_TRANSFORM,
        hypothesis_transform=_CER_TRANSFORM,
    )
    return float(out.cer)



def classify_token_transition(*, raw: str, corrected: str, truth: str) -> str:
    """Classify a single utterance transition into TP / FN / FP1 / FP2."""
    raw_match = normalize_text(raw) == normalize_text(truth)
    corrected_match = normalize_text(corrected) == normalize_text(truth)
    raw_corrected_match = normalize_text(raw) == normalize_text(corrected)
    if raw_match and corrected_match:
        return "TP"  # both right (no change needed)
    if not raw_match and corrected_match:
        return "TP"  # raw wrong, corrector fixed it
    if raw_match and not corrected_match:
        return "FP1"  # raw right, corrector broke it
    if not raw_match and not corrected_match and raw_corrected_match:
        return "FN"  # raw wrong, corrector kept it wrong
    return "FP2"  # raw wrong, corrector changed to a different wrong value


@dataclass
class LexnormEvaluator:
    """Compute WER/CER + confusion matrix for a corrector run."""

    def evaluate(
        self,
        raw_texts: list[str],
        corrected_texts: list[str],
        truth_texts: list[str],
        *,
        latency_ms_values: Iterable[int] | None = None,
    ) -> dict:
        if len(raw_texts) != len(corrected_texts) or len(raw_texts) != len(truth_texts):
            raise ValueError(
                f"length mismatch: raw={len(raw_texts)} corrected={len(corrected_texts)} truth={len(truth_texts)}"
            )

        categories = [
            classify_token_transition(raw=r, corrected=c, truth=t)
            for r, c, t in zip(raw_texts, corrected_texts, truth_texts)
        ]
        wer_raw = _wer(truth_texts, raw_texts)
        wer_corrected = _wer(truth_texts, corrected_texts)
        cer_raw = _cer(truth_texts, raw_texts)
        cer_corrected = _cer(truth_texts, corrected_texts)

        latency_list = list(latency_ms_values or [])
        return aggregate_metrics(
            wer_raw=wer_raw,
            wer_corrected=wer_corrected,
            cer_raw=cer_raw,
            cer_corrected=cer_corrected,
            categories=categories,
            latency_ms_values=latency_list,
        )


def aggregate_metrics(
    *,
    wer_raw: float,
    wer_corrected: float,
    cer_raw: float,
    cer_corrected: float,
    categories: list[str],
    latency_ms_values: list[int],
) -> dict:
    tp = sum(1 for c in categories if c == "TP")
    fn = sum(1 for c in categories if c == "FN")
    fp1 = sum(1 for c in categories if c == "FP1")
    fp2 = sum(1 for c in categories if c == "FP2")
    return {
        "wer_raw": wer_raw,
        "wer_corrected": wer_corrected,
        "wer_delta": wer_corrected - wer_raw,
        "cer_raw": cer_raw,
        "cer_corrected": cer_corrected,
        "cer_delta": cer_corrected - cer_raw,
        "tp": tp,
        "fn": fn,
        "fp1": fp1,
        "fp2": fp2,
        "total_tokens": len(categories),
        "latency_ms_total": sum(latency_ms_values),
        "latency_ms_mean": (
            int(sum(latency_ms_values) / len(latency_ms_values))
            if latency_ms_values
            else 0
        ),
    }
