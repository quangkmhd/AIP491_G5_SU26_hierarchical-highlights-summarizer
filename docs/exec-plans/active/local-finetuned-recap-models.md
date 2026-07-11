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

## Open Decisions

None.
