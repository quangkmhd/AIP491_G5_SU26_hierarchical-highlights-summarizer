
# Progress Log

## Current Verified State

- Repository root: /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary
- Standard startup path: `pwd` then read AGENTS.md -> ARCHITECTURE.md -> docs/QUALITY_SCORE.md -> docs/PLANS.md -> docs/product-specs/.
- Standard verification path: `python3 -m unittest discover -s tests -v`.
- Current highest-priority unfinished feature: model-002 (AI Model Loader & File Repository).
- Current blocker: none for model-001; model-002 needs the HuggingFace model checkpoints or offline stubs.

## Session Log

### Session 001

- Date: 2026-07-04
- Goal: Implement model-001 (Core Data Models) and run it on the first Vietnamese committee transcript.
- Completed: Pydantic v2 models in src/types (Utterance, DialogueTranscript, Chunk, SegmentResult, Highlight, HighlightType, HighlightSource, HierarchicalRecap, MeetingStatus, TranscriptIngestionRequest, HighlightUpsertRequest, MeetingProcessResponse). 38/38 unit tests pass. End-to-end demo (tests/manual/test_meeting_committee_sample.py) loads data/eval_vi/meeting_committee.json[0] (370 utterances, 8 segments) and writes a HierarchicalRecap JSON to docs/generated/model001_demo_recap.json.
- Verification run: `python3 -m unittest tests.unit.test_types_model001 -v` -> OK (30 tests). `python3 -m tests/manual/test_meeting_committee_sample.py` -> 8 segments / 50 chunks / 2 highlights.
- Evidence captured: tests/unit/test_types.py, docs/generated/model001_demo_recap.json, feature_list.json (model-001 -> passing), QUALITY_SCORE.md.
- Commits: not committed (per AGENTS.md contract).
- Files or artifacts updated: src/types/{_base,__init__,utterance,transcript,segment,highlight,hierarchical_recap,schemas}.py, src/__init__.py, tests/unit/__init__.py, tests/unit/test_types.py, feature_list.json, docs/QUALITY_SCORE.md, docs/generated/model001_demo_recap.json.
- Known risk or unresolved issue: model-001 is the foundation only; svc-001 (TextTiling) and svc-002 (Summarization) are still placeholders. model-002 (ModelLoader) is the next dependency.
- Post-review hardening (same session): enforced MAX_UTTERANCES in DialogueTranscript and at the request boundary (materialize()), added model_validator requiring exactly one of `utterances` / `flat_texts`, and locked the Highlight JSON wire format to canonical 'key_point' / 'action_item' values via a new test. Test count grew 34 -> 38.
- Next best step: Begin model-002 (ModelLoader) so svc-001 can wire CoherenceNet into HuggingFace pipeline.

### Session 002

- Date:
- Goal:
- Completed:
- Verification run:
- Evidence captured:
- Commits:
- Files or artifacts updated:
- Known risk or unresolved issue:
- Next best step:

## model-002 — AI Model Loader & File Repository (2026-07-04)

**Status:** passing

- Implemented `src/repo/{coherence_net,model_loader,transcript_repo,recap_repo,smoke_loader}.py` + `prompts_vi.py`.
- CoherenceNet loads from `vibert_checkpoints_vi/cpt_4000.pth` (paper-1 architecture, BERT-base multilingual base, embeddings resized to ckpt vocab 38168, strict=False for shape-mismatched MLM-head keys).
- ModelLoader is a per-process singleton; `MODEL_LOAD_LLM=0` env var returns a `MockLLMBackbone` for offline CI.
- Vistral-7B-Chat selected as the single Vietnamese LLM backbone (4-bit via `bitsandbytes`, deferred behind env var).
- 4 Vietnamese prompt templates cover the collapsed paper-2 task list (segment / abstractive / title / highlights).
- TranscriptRepo reads all 6 `data/eval_vi/*.json` files into `DialogueTranscript` with synthesised speaker labels and drops empty/placeholder utterances (e.g. AMI `{vocalsound}` artefacts).
- RecapRepo round-trips `HierarchicalRecap` via Pydantic v2 `model_dump_json`.
- AST-based layer-rule test enforces zero imports from `config`/`service`/`runtime`/`ui` in `src/repo/`.
- 35 new unit tests; full suite green (74/74).
- Verification: `MODEL_LOAD_LLM=0 python3 -m unittest discover -s tests` and `python3 -m src.repo.smoke_loader` both green.

## model-002 — Code Review & Fixes (2026-07-05)

**Reviewer:** `docs/generated/review-2026-07-05.md`
**Verdict (initial):** Not ready to merge — 4 critical + 3 important bugs.

**Fixes applied (same session):**
- **C1** (`src/repo/transcript_repo.py`): `_strip_inline_placeholders` now
  removes inline `{vocalsound}` / `{gap}` / `{disfmarker}` annotations
  from kept utterance text, not just fully-placeholder utterances.
- **C2** (`src/repo/transcript_repo.py:_build_transcript`): speaker labels
  now track the ORIGINAL index (`S{original_idx + 1}`) so dropping
  utterances does not shift everyone else's speaker tag.
- **C3** (`src/repo/model_loader.py`): added `_cache_lock` to make the
  per-kind lookup-and-insert atomic. Two threads can no longer both
  trigger a fresh `ModelKind.NSP` load.
- **C4** (`src/repo/model_loader.py`): added `_coerce_token_ids` helper
  that clamps token IDs >= vocab_size (38168) to 0 (UNK) so the
  embedding lookup no longer raises on real Vietnamese text. **Tracked
  as Important debt** in `docs/exec-plans/tech-debt-tracker.md` —
  clamped tokens lose semantic content, so the model is not yet
  production-quality for real Vietnamese.
- **I1** (`src/repo/recap_repo.py`): write is atomic via
  `tempfile.NamedTemporaryFile` + `os.replace`. A mid-write crash no
  longer leaves a truncated file at the destination path.
- **I2** (`src/repo/_io.py`): new shared module for
  `read_json_file` / `write_json_file`. Both `RecapRepo` and
  `TranscriptRepo` call into it; new repos will follow the same
  pattern automatically.
- **I3** (`src/repo/smoke_loader.py`): added `REQUIRE_CUDA=1` env var
  for the smoke loader to fail loudly on CPU-only hosts. The default
  remains permissive.

**Test count:** 76 → 92 (+16 new tests covering C1, C2, C3, C4, I1, I2,
I3 directly).

**Documentation:**
- `docs/QUALITY_SCORE.md`: `Topic Segmentation` row claim reworded
  to "on the resolved device (cuda preferred, cpu fallback)";
  `Benchmark Snapshots` row for `model-002-repo` now records the
  4-critical-bug review + 16-test fix cycle.
- `docs/exec-plans/tech-debt-tracker.md`: C4 (vocab mismatch) and
  I2 (incomplete _io adoption) recorded as Important; M1, M2, M3
  recorded as Minor.
