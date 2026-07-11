# Local Fine-Tuned Recap Models

## Objective

Replace Gemma recap generation with local ViT5 chunk summaries and BARTpho
titles generated only from completed topic summaries.

## Scope

Repo model loading, task adapters, hierarchical summarization input contracts,
orchestrator ordering verification, local artifacts, runtime tests, and matching
documentation.

## Out of Scope

Retraining, segmentation changes, schema changes, CPU fallback, quantization,
and remote downloads.

## Verification Path

- `uv run pytest tests/ -q -m 'not real_model'`
- `uv run pytest tests/manual/test_local_recap_models_smoke.py -v -m real_model`
- `uv run python -m src.runtime.cli process <fixture> -o <output>`

## Risks and Blockers

- Both float32 models must fit available CUDA VRAM.
- Local artifacts are ignored and must be provisioned before runtime startup.

## Progress Log

- 2026-07-11: plan opened in isolated worktree.
- 2026-07-11: baseline `uv run python -m unittest discover -s tests -v`
  passed 265 tests with 3 skips.
- 2026-07-11: copied inference-only artifacts: ViT5 864 MB and BARTpho
  508 MB; no training state is present and `models/` is git-ignored.
- 2026-07-11: dual CUDA loader, task adapters, exact fine-tuning inputs,
  summary-only titles, and runtime test injection implemented.
- 2026-07-11: real CLI processed `/tmp/local-recap-smoke.json` in 2.148 s,
  producing 3 segments, 3 non-empty summaries, and 3 non-empty titles at
  `/tmp/local-recap-smoke-output.json`.

## Open Decisions

None.

## Verification at archive time

- Fast suite: `uv run pytest tests/ -q -m 'not real_model'` — 266 passed,
  3 skipped, 1 deselected, 12 subtests passed.
- CUDA smoke: `uv run pytest tests/manual/test_local_recap_models_smoke.py
  -q -m real_model` — 1 passed on NVIDIA GeForce RTX 4060 8 GB.
- CLI restart: `uv run python -m src.runtime.cli process
  /tmp/local-recap-smoke.json -o /tmp/local-recap-smoke-output.json` — exit 0;
  every segment title and chunk summary non-empty.
- Production lint: `uv run ruff check` on changed production modules — green.
- Legacy runtime search: zero matches for mock/GGUF/`MODEL_LOAD_LLM` symbols
  in `src`, `tests`, and `pyproject.toml`.
