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

(empty -- work has not begun on this plan yet)

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
