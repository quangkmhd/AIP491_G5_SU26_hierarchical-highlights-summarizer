"""Run the segmentation eval harness on data/eval_vi/.

Usage:
    python -m src.eval.run_segmentation_eval --corpus meeting_committee

Reports P_k, Win-Diff, and F1 for each sample, then aggregate stats.
At MVP this is a structural harness: it does NOT call the full
StreamingOrchestrator (that would take 30+ minutes on 5,000 utt). The
harness verifies the metric pipeline + ground-truth conventions; the
real P_k/F1 numbers come from running svc-001+002 over the same data and
plumbing predictions through this module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.data import Corpus, EvalLoader
from src.eval.segmentation_metrics import f1_score, pk, win_diff


def _ends_from_sizes(sizes: list[int]) -> list[int]:
    ends: list[int] = []
    cursor = 0
    for s in sizes:
        cursor += s
        ends.append(cursor - 1)
    return ends


def evaluate_corpus(corpus: Corpus, data_root: Path) -> dict:
    loader = EvalLoader(data_root)
    result = loader.load(corpus)
    pk_scores: list[float] = []
    wd_scores: list[float] = []
    f1_scores: list[float] = []
    for sample in result.samples:
        ends = _ends_from_sizes(sample.segment_sizes)
        # Self-evaluation: P_k=0, F1=1.0 always
        pk_scores.append(pk(ends, ends))
        wd_scores.append(win_diff(ends, ends))
        f1_scores.append(f1_score(ends, ends))
    return {
        "corpus": corpus.value,
        "n_samples": result.total,
        "mean_pk": sum(pk_scores) / len(pk_scores) if pk_scores else 0.0,
        "mean_wd": sum(wd_scores) / len(wd_scores) if wd_scores else 0.0,
        "mean_f1": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="src.eval.run_segmentation_eval")
    parser.add_argument("--corpus", choices=[c.value for c in Corpus], default="meeting_committee")
    parser.add_argument("--data-root", type=Path, default=Path("data/eval_vi"))
    parser.add_argument("--output", "-o", type=Path, help="Write JSON report to this path")
    args = parser.parse_args(argv)

    corpus = Corpus(args.corpus)
    report = evaluate_corpus(corpus, args.data_root)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
