# model-002 — AI Model Loader & File Repository (ACTIVE)

## Objective

Implement the Repository layer: a `ModelLoader` that loads HuggingFace
checkpoints (NSP BERT / CoherenceNet, deBERTa title & abstractive, BART
extract & abstractive) into memory on the right device, and a
`TranscriptRepo` that reads raw transcript files and parses them into
domain `DialogueTranscript` objects.

## Scope

- `src/repo/model_loader.py`: `ModelLoader` class with explicit
  `load_coherence_net()`, `load_title_model()`, `load_abstractive_model()`,
  `load_highlights_models()` methods. Each returns a `ModelHandle`
  dataclass that records the device (cpu/cuda), checkpoint path, and any
  tokenizer. Each method must cache so the same model isn't reloaded twice
  in the same process.
- `src/repo/coherence_net.py`: PyTorch module architecture for the NSP
  coherence model. It should accept a pair of texts and return a
  `CoherenceScore` (float in [0, 1]).
- `src/repo/transcript_repo.py`: read a raw JSON / TXT transcript, parse
  it into `Utterance` objects, wrap in a `DialogueTranscript`. Support
  the `data/eval_vi/*.json` schema (the same shape used in the smoke
  test) and a plain text fallback (one utterance per line).
- `src/repo/recap_repo.py`: write a `HierarchicalRecap` to a local JSON
  file (round-trip safe), and read it back.
- Unit tests for each module. Aim for >= 30 tests.

## Out of Scope

- Actual model inference (covered by `svc-001` and `svc-002`).
- FastAPI endpoints (covered by `api-001`).
- The full Vietnamese committee dataset; the smoke test should still only
  load the first dialogue.

## Verification Path

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary
python3 -m unittest discover -s tests -v
# Expected: >= 69 tests (39 existing + >= 30 new), all green.

python3 -m src.repo.smoke_loader
# Expected: ModelLoader loads CoherenceNet from vibert_checkpoints_vi/cpt_1000.pth,
#           prints device + parameter count, does not raise.
```

The layer rule check (already inside the smoke test) must continue to
hold: zero imports from `config`/`service`/`runtime` inside `src/repo/`.

## Risks and Blockers

- The Vietnamese CoherenceNet checkpoint is 463 MB and is `cuda:0`-tagged.
  If the dev machine has no GPU, the loader must transparently remap to
  CPU. Verify this with `python3 -c "import torch; print(torch.cuda.is_available())"`
  early.
- `transformers` is not yet a declared dependency. Add it to
  `pyproject.toml` with justification recorded in this plan's progress
  log before importing.
- Do **not** commit the `cpt_*.pth` files. The repo's `.gitignore` already
  excludes them; verify by `git check-ignore vibert_checkpoints_vi/cpt_1000.pth`.

## Progress Log

### 2026-07-04 -- implementation complete
- All 5 modules + smoke loader implemented per `docs/superpowers/plans/2026-07-04-model-002.md`.
- Verification (offline mode): `MODEL_LOAD_LLM=0 python3 -m unittest discover -s tests` -> green (74/74 tests, 35 new + 39 existing).
- Verification (smoke): `MODEL_LOAD_LLM=0 python3 -m src.repo.smoke_loader` -> loads CoherenceNet, prints device=cuda + 115M params, exits 0.
- Spec lives at `docs/superpowers/specs/2026-07-04-model-002-design.md`.
- Status: ready to archive to `docs/exec-plans/completed/`.
- Note: Vistral-7B-Chat chosen as the single Vietnamese LLM backbone (4-bit) to replace paper-2's 4 fine-tuned BART/deBERTa models per user direction.
- Known limitations deferred:
  - Tokenizer mismatch (multilingual BERT base vocab 119547 vs ckpt vocab 38168): handled by `resize_token_embeddings` + shape-filtered `load_state_dict(strict=False)`. Real text inference is svc-001's job.
  - Real 4-bit Vistral load is gated by `MODEL_LOAD_LLM=1` env var; CI uses mock LLM.

## Open Decisions

- Should the `ModelLoader` be a singleton or per-request? Default to
  per-process singleton (HF model loading is expensive); document the
  choice in `src/repo/model_loader.py`.
- Should `TranscriptRepo` validate via Pydantic (current
  `TranscriptIngestionRequest`) or use a simpler parser? Default to
  Pydantic -- consistency with the API boundary.
- Should the `recap_repo` be a separate module or part of
  `transcript_repo`? Default to separate module -- reads and writes are
  different enough concerns.

## Verification at archive time

- **Date (initial archive):** 2026-07-04 — 74/74 tests pass.
- **Date (post-review):** 2026-07-05 — 92/92 tests pass after C1, C2, C3, C4, I1, I2, I3 fixes.
- **Command (post-review):** `MODEL_LOAD_LLM=0 python3 -m unittest discover -s tests`
- **Result:** `Ran 92 tests in 15.032s -- OK` (38 existing model-001 + 54 new model-002)
- **Smoke:** `MODEL_LOAD_LLM=0 python3 -m src.repo.smoke_loader` exits 0 with output:
  ```
  [smoke] NSP_CKPT_PATH = vibert_checkpoints_vi/cpt_4000.pth
  [smoke] loaded NSP on device=cuda, params=115,946,498
  [smoke] 4 Vietnamese prompt templates loaded
  [smoke] LLM_BACKBONE offline mock returned: kind=ModelKind.LLM_BACKBONE
  [smoke] OK
  ```
- **Status:** passing -- archive complete.

### 2026-07-05 -- code review & critical-bug fixes

- Reviewer: `docs/generated/review-2026-07-05.md` (Senior reviewer).
- Verdict (initial): **Not ready to merge** — 4 critical + 3 important bugs.
- All 4 critical (C1, C2, C3, C4) and 3 important (I1, I2, I3) issues fixed in this session.
- Test count: 76 -> 92 (+16 new tests directly targeting the review findings).
- C4 (vocab mismatch between checkpoint 38168 and multilingual BERT base
  119547) is **mitigated** with `_coerce_token_ids`; the **root cause**
  (missing 38168-vocab Vietnamese-subset tokenizer) is tracked as
  Important tech debt in `docs/exec-plans/tech-debt-tracker.md` and
  blocks production-quality inference in `svc-001`.
