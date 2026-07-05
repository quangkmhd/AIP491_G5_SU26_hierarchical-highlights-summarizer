"""End-to-end smoke test: load real CoherenceNet + run TextTiling on committee sample.

This is the integration test for svc-001+002 (paper-1 *Ours (full)*).
It runs on the actual NSP-BERT checkpoint at vibert_checkpoints_vi/cpt_4000.pth.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config.text_tiling import TextTilingConfig
from src.data import Corpus, EvalLoader
from src.service import CoherenceScorer, TextTilingService


def main() -> int:
    print("=== svc-001+002 smoke: paper-1 *Ours (full)* on committee sample ===")
    loader = EvalLoader(ROOT / "data" / "eval_vi")
    result = loader.load(Corpus.MEETING_COMMITTEE)
    sample = result.samples[0]
    print(f"loaded {result.total} committee dialogues")
    print(f"using sample dial_id={sample.dial_id}, "
          f"{sample.utterance_count} utt, {sample.segment_count} ground-truth segments")

    print("loading CoherenceScorer (loads CoherenceNet from cpt_4000.pth)...")
    t0 = time.perf_counter()
    scorer = CoherenceScorer()
    load_time = time.perf_counter() - t0
    print(f"loaded in {load_time:.2f}s")

    print(f"scoring {sample.utterance_count - 1} pairs (this may take ~1 min on CPU)...")
    t0 = time.perf_counter()
    scores = list(scorer.score_stream(sample.utterances))
    score_time = time.perf_counter() - t0
    print(f"scored in {score_time:.2f}s; got {len(scores)} scores")
    print(f"score range: [{min(scores):.3f}, {max(scores):.3f}], "
          f"mean={sum(scores)/len(scores):.3f}")

    print("running TextTilingService.process()...")
    tiler = TextTilingService(TextTilingConfig())
    events = tiler.process(scores, n_utterances=sample.utterance_count)
    print(f"TextTiling emitted {len(events)} SegmentEvents")
    for e in events:
        print(f"  {e.segment_id}: utt [{e.utterances_start}..{e.utterances_end}] "
              f"depth={e.depth_score:.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
