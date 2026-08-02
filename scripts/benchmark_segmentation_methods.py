#!/usr/bin/env python3
"""Evaluate reproducible segmentation baselines on all six thesis corpora."""

from __future__ import annotations

import json
import logging
import os
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import segeval
import stopwordsiso
from nltk.tokenize import TextTilingTokenizer
from sklearn.metrics import f1_score

from src.config.sliding_text_tiling import SlidingTextTilingConfig
from src.data import Corpus, EvalLoader
from src.service.sliding_text_tiling import SlidingTextTilingService


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "generated" / "segmentation_methods_benchmark.json"


def boundaries_to_binary(boundaries: list[int], length: int) -> list[int]:
    values = [0] * length
    for boundary in boundaries:
        if 0 <= boundary < length:
            values[boundary] = 1
    values[-1] = 1
    return values


def segments_to_binary(segment_sizes: list[int]) -> list[int]:
    values = [0] * sum(segment_sizes)
    cursor = 0
    for size in segment_sizes[:-1]:
        cursor += size
        values[cursor - 1] = 1
    values[-1] = 1
    return values


def nltk_segments(utterances: list[str], stopwords: set[str]) -> list[int]:
    raw = "\n\n".join(utterances)
    try:
        chunks = TextTilingTokenizer(w=20, k=10, stopwords=stopwords).tokenize(raw)
    except Exception:
        return [len(utterances)]
    sizes = [len([part for part in chunk.split("\n\n") if part.strip()]) for chunk in chunks]
    return sizes if sizes and sum(sizes) == len(utterances) else [len(utterances)]


def nltk_prediction_task(utterances: list[str]) -> list[int]:
    """Process-safe NLTK prediction for one dialogue."""
    return nltk_segments(utterances, set(stopwordsiso.stopwords(["vi"])))


def evaluate_predictions(predicted: list[int], reference: list[int]) -> tuple[float, float, float]:
    predicted_boundaries: list[int] = []
    cursor = 0
    for size in predicted:
        cursor += size
        predicted_boundaries.append(cursor - 1)
    predicted_binary = boundaries_to_binary(predicted_boundaries, sum(reference))
    reference_binary = segments_to_binary(reference)
    return (
        float(segeval.pk(predicted, reference)),
        float(segeval.window_diff(predicted, reference)),
        float(f1_score(reference_binary, predicted_binary, labels=[0, 1], average="macro")),
    )


def main() -> None:
    logging.disable(logging.CRITICAL)
    loader = EvalLoader(ROOT / "data" / "eval_vi")
    stopwords = set(stopwordsiso.stopwords(["vi"]))
    configs = {
        "lexical_single_scale": SlidingTextTilingConfig(
            block_size=2, radii=[3], alpha=0.5, normalize="minmax",
            min_segment_ratio=0.0, window_size=99999, stride=99998,
        ),
        "multi_scale_sliding_texttiling": SlidingTextTilingConfig(
            block_size=2, radii=[3, 5, 10, 15, 20], alpha=1.2,
            normalize="zscore", min_segment_ratio=0.20,
            window_size=40, stride=5,
        ),
    }
    results: dict[str, dict[str, dict]] = {}

    for corpus in Corpus:
        loaded = loader.load(corpus)
        corpus_results: dict[str, dict] = {}
        methods = ["nltk_texttiling", *configs.keys()]
        for method in methods:
            pk_values: list[float] = []
            wd_values: list[float] = []
            f1_values: list[float] = []
            started = time.perf_counter()
            service = SlidingTextTilingService(config=configs[method]) if method in configs else None
            if method == "nltk_texttiling":
                workers = min(4, os.cpu_count() or 1)
                with ProcessPoolExecutor(max_workers=workers) as executor:
                    predictions = list(executor.map(
                        nltk_prediction_task,
                        (sample.utterances for sample in loaded.samples),
                        chunksize=1,
                    ))
            else:
                predictions = []
                for sample in loaded.samples:
                    events = service.process(sample.utterances)
                    predictions.append([event.utterances_end - event.utterances_start + 1 for event in events])
            for sample, predicted in zip(loaded.samples, predictions, strict=True):
                pk, wd, macro_f1 = evaluate_predictions(predicted, sample.segment_sizes)
                pk_values.append(pk)
                wd_values.append(wd)
                f1_values.append(macro_f1)
            corpus_results[method] = {
                "pk": statistics.fmean(pk_values),
                "window_diff": statistics.fmean(wd_values),
                "macro_f1": statistics.fmean(f1_values),
                "elapsed_s": time.perf_counter() - started,
                "samples": len(loaded.samples),
            }
            print(corpus.value, method, json.dumps(corpus_results[method]))
        results[corpus.value] = corpus_results

    aggregate: dict[str, dict] = {}
    for method in ["nltk_texttiling", *configs.keys()]:
        rows = [results[corpus.value][method] for corpus in Corpus]
        aggregate[method] = {
            "pk_macro": statistics.fmean(row["pk"] for row in rows),
            "window_diff_macro": statistics.fmean(row["window_diff"] for row in rows),
            "macro_f1_macro": statistics.fmean(row["macro_f1"] for row in rows),
            "elapsed_s_total": sum(row["elapsed_s"] for row in rows),
        }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methods": {
            "nltk_texttiling": {"w": 20, "k": 10},
            "lexical_single_scale": configs["lexical_single_scale"].model_dump(),
            "multi_scale_sliding_texttiling": configs["multi_scale_sliding_texttiling"].model_dump(),
        },
        "corpora": results,
        "aggregate": aggregate,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
