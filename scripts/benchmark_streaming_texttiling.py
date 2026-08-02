#!/usr/bin/env python3
"""Benchmark the thesis streaming TextTiling configuration reproducibly."""

from __future__ import annotations

import json
import logging
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import segeval
import stopwordsiso
from sklearn.metrics import f1_score

from src.data import Corpus, EvalLoader
from src.service.sliding_text_tiling import StreamingTextTilingSegmenter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "generated" / "streaming_texttiling_benchmark.json"
REPEATS = 3
CONFIG = {
    "block_size": 2,
    "radii": [3, 5, 10, 15, 20],
    "alpha": 1.2,
    "agg": "mean",
    "normalize_mode": "zscore",
    "min_segment_ratio": 0.20,
    "window_size": 40,
    "stride": 5,
    "lookahead": 20,
}


def boundaries_to_binary(boundaries: list[int], length: int) -> list[int]:
    values = [0] * length
    for boundary in boundaries:
        if 0 <= boundary < length:
            values[boundary] = 1
    values[-1] = 1
    return values


def segments_to_binary(segment_sizes: list[int]) -> list[int]:
    length = sum(segment_sizes)
    values = [0] * length
    position = 0
    for size in segment_sizes[:-1]:
        position += size
        values[position - 1] = 1
    values[-1] = 1
    return values


def boundaries_to_segments(boundaries: list[int]) -> list[int]:
    sizes: list[int] = []
    previous = -1
    for boundary in sorted(set(boundaries)):
        sizes.append(boundary - previous)
        previous = boundary
    return sizes


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q)) if values else 0.0


def evaluate_corpus(samples, stopwords: set[str]) -> dict:
    pk_values: list[float] = []
    wd_values: list[float] = []
    f1_values: list[float] = []
    repeat_ms_per_utterance: list[float] = []
    update_latencies_ms: list[float] = []
    commit_delays: list[int] = []
    online_boundaries = 0
    flushed_boundaries = 0
    utterance_count = sum(len(sample.utterances) for sample in samples)

    for repeat in range(REPEATS):
        repeat_started = time.perf_counter()
        repeat_update_latencies: list[float] = []

        for sample in samples:
            segmenter = StreamingTextTilingSegmenter(stopwords=stopwords, **CONFIG)
            for utterance_index, utterance in enumerate(sample.utterances):
                update_started = time.perf_counter()
                committed = segmenter.update(utterance)
                repeat_update_latencies.append((time.perf_counter() - update_started) * 1000.0)
                if repeat == 0:
                    online_boundaries += len(committed)
                    commit_delays.extend(utterance_index - boundary for boundary, _ in committed)

            flushed = segmenter.flush()
            if repeat == 0:
                flushed_boundaries += len(flushed)
                boundaries = sorted(set(segmenter.committed_boundaries))
                predicted_segments = boundaries_to_segments(boundaries)
                reference_segments = sample.segment_sizes
                predicted_binary = boundaries_to_binary(boundaries, len(sample.utterances))
                reference_binary = segments_to_binary(reference_segments)
                pk_values.append(float(segeval.pk(predicted_segments, reference_segments)))
                wd_values.append(float(segeval.window_diff(predicted_segments, reference_segments)))
                f1_values.append(
                    float(f1_score(reference_binary, predicted_binary, labels=[0, 1], average="macro"))
                )

        elapsed_ms = (time.perf_counter() - repeat_started) * 1000.0
        repeat_ms_per_utterance.append(elapsed_ms / utterance_count)
        update_latencies_ms.extend(repeat_update_latencies)

    return {
        "samples": len(samples),
        "utterances": utterance_count,
        "pk": statistics.fmean(pk_values),
        "window_diff": statistics.fmean(wd_values),
        "macro_f1": statistics.fmean(f1_values),
        "mean_processing_ms_per_utterance": statistics.fmean(repeat_ms_per_utterance),
        "p95_update_latency_ms": percentile(update_latencies_ms, 95),
        "mean_commit_delay_utterances": statistics.fmean(commit_delays) if commit_delays else 0.0,
        "p95_commit_delay_utterances": percentile([float(value) for value in commit_delays], 95),
        "online_boundaries": online_boundaries,
        "flushed_boundaries": flushed_boundaries,
    }


def main() -> None:
    logging.disable(logging.CRITICAL)
    loader = EvalLoader(str(ROOT / "data" / "eval_vi"))
    stopwords = set(stopwordsiso.stopwords(["vi"]))
    corpora: dict[str, dict] = {}

    for corpus in Corpus:
        loaded = loader.load(corpus)
        corpora[corpus.value] = evaluate_corpus(loaded.samples, stopwords)
        print(corpus.value, json.dumps(corpora[corpus.value], ensure_ascii=False))

    metrics = list(corpora.values())
    total_utterances = sum(item["utterances"] for item in metrics)
    aggregate = {
        "pk_macro": statistics.fmean(item["pk"] for item in metrics),
        "window_diff_macro": statistics.fmean(item["window_diff"] for item in metrics),
        "macro_f1_macro": statistics.fmean(item["macro_f1"] for item in metrics),
        "processing_ms_per_utterance_weighted": sum(
            item["mean_processing_ms_per_utterance"] * item["utterances"] for item in metrics
        ) / total_utterances,
        "mean_commit_delay_utterances_weighted": sum(
            item["mean_commit_delay_utterances"] * item["online_boundaries"] for item in metrics
        ) / max(1, sum(item["online_boundaries"] for item in metrics)),
        "total_samples": sum(item["samples"] for item in metrics),
        "total_utterances": total_utterances,
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "repeats": REPEATS,
        "configuration": CONFIG,
        "corpora": corpora,
        "aggregate": aggregate,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
