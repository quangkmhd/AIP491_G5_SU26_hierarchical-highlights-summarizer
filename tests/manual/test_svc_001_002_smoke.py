"""End-to-end smoke test: run SlidingTextTilingService on a committee sample.

The pipeline uses pure lexical Sliding TextTiling; it runs in under
0.1s on 370 utterances with no model dependency.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config.sliding_text_tiling import SlidingTextTilingConfig
from src.data import Corpus, EvalLoader
from src.service import SlidingTextTilingService


def main() -> int:
    print("=== svc-001+002 smoke: Sliding TextTiling on committee sample ===")
    loader = EvalLoader(ROOT / "data" / "eval_vi")
    result = loader.load(Corpus.MEETING_COMMITTEE)
    sample = result.samples[0]
    print(f"loaded {result.total} committee dialogues")
    print(f"using sample dial_id={sample.dial_id}, "
          f"{sample.utterance_count} utt, {sample.segment_count} ground-truth segments")

    t0 = time.perf_counter()
    tiler = SlidingTextTilingService(SlidingTextTilingConfig())
    print(f"constructed SlidingTextTilingService in {time.perf_counter() - t0:.3f}s")

    print("running SlidingTextTilingService.process()...")
    t0 = time.perf_counter()
    events = tiler.process(sample.utterances)
    print(f"done in {time.perf_counter() - t0:.3f}s; emitted {len(events)} SegmentEvents")
    for e in events:
        print(f"  {e.segment_id}: utt [{e.utterances_start}..{e.utterances_end}] "
              f"depth={e.depth_score:.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())