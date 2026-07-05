# svc-001+002 — Topic Segmentation Pipeline (Archived)

**Goal:** Implement paper-1 *Ours (full)* topic segmentation using the user-fine-tuned NSP-BERT checkpoint + TextTiling.

**Result:**
- `src/service/{__init__,coherence_scorer,text_tiling}.py` (3 new files).
- `CoherenceScorer.score_pair` returns float in [0, 1] (mode CM).
- `TextTilingService.process(scores, n_utterances)` emits `SegmentEvent` with depth-score cutoffs (`tau = mu - sigma/2`).
- 16 unit tests + 1 layer-rule test + 1 end-to-end smoke = 18 new tests.

**Verification at archive time:**
- `python3 -m unittest discover -s tests -v` → 172/172 OK
- `CUDA_VISIBLE_DEVICES="" python3 tests/manual/test_svc_001_002_smoke.py` → loads checkpoint, scores 369 pairs, emits 192 events
- AST service-layer rule green
- `feature_list.json` svc-001+002 status: passing
- Branch `feat/svc-001-002` merged to main
