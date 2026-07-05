# data-001 — Multi-corpus Evaluation Data Loader Implementation Plan (Archived)

**Goal:** Load every JSON file in `data/eval_vi/` as a uniform `DialogueSample` list with per-corpus metadata.

**Result:**
- `src/data/{__init__,corpus,dialogue_sample,eval_loader}.py` created (4 files, 1 layer).
- Convention: `segments` is a list of segment SIZES (cumulative sum = utterance count). Validated by `model_validator`.
- `EvalLoader.load(corpus)` returns `LoadResult(samples, train/dev/test counts, metadata)`. 6 corpora supported: dialseg_711, doc2dial, meeting_ami, meeting_committee, meeting_icsi, tiage.
- 19 unit tests + 1 AST layer-rule test = 20 new tests.

**Verification at archive time:**
- `python3 -m unittest discover -s tests -v` → 154/154 OK
- AST data-layer rule green
- `feature_list.json` data-001 status: passing
- Branch `feat/data-001` merged to main
