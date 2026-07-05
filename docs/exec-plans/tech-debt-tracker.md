# Tech Debt Tracker

This file tracks deferred work and follow-ups that are out of scope for
the current active plan. Items here are non-blocking for shipping the
current milestone but should be addressed before the next major one.

## Severity Legend

- **Important** -- affects correctness, performance, or UX in a way users
  can notice.
- **Minor** -- cleanup, polish, or documentation that improves legibility
  but does not change observable behavior.

## Open Items

### Minor (from model-001 self-review, 2026-07-04)

- **No `__all__` in `src/types/schemas.py`**
  - File: `src/types/schemas.py`
  - Issue: `__init__.py` already names the three classes explicitly, so
    this is fine, but a local `__all__` would tighten the module's
    public surface.
  - Fix: add `__all__ = ["TranscriptIngestionRequest", "HighlightUpsertRequest", "MeetingProcessResponse"]`.
  - Owner: next agent touching `schemas.py`.

- **No `repr` customization for large models**
  - File: `src/types/transcript.py`, `src/types/hierarchical_recap.py`
  - Issue: Pydantic's default repr prints every utterance, which is
    noisy for a 370-utterance transcript.
  - Fix: add `__repr_args__` that limits nested repr depth, or set
    `model_config = ConfigDict(repr=False)` for these two models.
  - Owner: next agent touching debugging UX.

- **Deterministic UUID in demo is undocumented**
  - File: `tests/manual/test_meeting_committee_sample.py`
  - Issue: the demo uses `UUID(int=(dial_id + 1) * 10**12)` so the
    output JSON is reproducible. Production code uses `uuid4()`.
  - Fix: a one-line comment explaining "deterministic for diffable demo
    output" so the next reader doesn't think the production code is
    supposed to be deterministic.
  - Owner: next agent touching the smoke test.

- **No `to_compact_dict()` helper on `HierarchicalRecap`**
  - File: `src/types/hierarchical_recap.py`
  - Issue: `model_dump_json()` includes the full `Chunk.utterances` text,
    which is 243 KB for the Vietnamese committee meeting. The recap
    payload the UI needs is just metadata (segment ranges, titles, rolling
    summaries, highlights) -- the raw utterances already live in the
    source transcript.
  - Fix: add a `to_compact_dict()` method that drops `chunks[].utterances`
    and includes only `chunks[].chunk_id` + `chunks[].rolling_summary`.
  - Owner: next agent implementing `api-001`.

## Resolved Items

(none yet)

### Important (from model-002 code review, 2026-07-05)

- **C4: Tokenizer vocab mismatch (38168 ckpt vs 119547 multilingual base)**
  - File: `src/repo/model_loader.py:113-129` (mitigation); root cause is
    missing 38168-vocab Vietnamese-subset tokenizer.
  - Issue: The pre-trained `cpt_4000.pth` was trained with a Vietnamese-
    subset tokenizer (vocab 38168) that is NOT shipped with the project.
    The repo currently loads `bert-base-multilingual-cased` (vocab
    119547) and mitigates the OOV problem with `_coerce_token_ids` that
    clamps IDs >= 38168 to 0 (UNK). This means the model cannot reliably
    score real Vietnamese text -- clamped tokens lose all semantic
    content and degrade coherence scoring accuracy.
  - Mitigations: (1) obtain the 38168-vocab tokenizer from the model
    author, (2) train a frequency-truncated tokenizer from the
    multilingual vocab that matches the checkpoint, or (3) rebuild the
    CoherenceNet architecture to use a 119547-vocab checkpoint
    (re-train or fine-tune from scratch).
  - Required before: `svc-001` (real Vietnamese inference).
  - Workaround today: `_coerce_token_ids` keeps the embedding lookup
    from raising; tests pass with synthetic IDs in [0, 38167].

- **I2: `src/repo/_io.py` is not yet used by every new repo**
  - File: `src/repo/recap_repo.py:50-72` and `src/repo/transcript_repo.py:69-79`
  - Issue: Both repos now call into `_io.read_json_file`, but
    `RecapRepo.write` re-implements the temp-file + `os.replace` flow
    inline rather than going through a shared `write_json_file` helper.
    The next repo added will copy one of these two patterns.
  - Required before: adding a third repo (e.g. `HighlightsRepo`).

### Minor (from model-002 code review, 2026-07-05)

- **M1: `ModelLoader.reset_instance()` does not evict model weights**
  - File: `src/repo/model_loader.py:185-189`
  - Issue: `reset_instance` only nulls the class-level `_instance`. If
    a caller already holds a reference to the old loader, the model
    weights stay loaded in VRAM.
  - Note: Documented as test-only; production code should never call
    `reset_instance`.

- **M2: `coerce_checkpoint_path` is dead code on `CoherenceNet`**
  - File: `src/repo/coherence_net.py:80-88`
  - Issue: A static method on the class that duplicates the check in
    `_load_nsp_weights`. Future maintainers may call it from a new
    service and end up with two divergent implementations.
  - Fix: Delete; if a public validator is needed, move to a module-
    level function in `model_loader.py` and call it from both sites.

- **M3: `CoherenceNet.forward` runs BERT one pair at a time**
  - File: `src/repo/coherence_net.py:62-78`
  - Issue: For a 100-sample batch, this issues 300 separate BERT
    forward passes instead of one batched `[300, L]` forward.
  - Performance impact: ~3-10x slower than the batched version
    (depends on device). The Service layer in `svc-001` will score
    many utterance pairs in tight loops, so this matters at scale.
  - Fix: Stack input dicts across the batch, run BERT once per
    pair-type, then reshape back into `[B, 3, 768]`.
