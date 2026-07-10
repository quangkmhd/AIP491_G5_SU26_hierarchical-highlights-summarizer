# Prompt Registry Replacement — Design Spec

**Date:** 2026-07-05
**Status:** Draft for user review
**Area:** `repo`, `tests`, `docs`
**Layer position:** `Types -> Config -> Repo -> Service -> Runtime -> UI`

## Context

The project now implements only the streaming hierarchical recap pipeline. The
current Vietnamese prompt registry still contains short prototype prompts and a
highlights prompt, while `references_code/prompts.yaml` contains stricter
production-oriented prompts for JSON-only meeting recap generation.

## Goal

Replace the current prompt templates with the hierarchical prompts from
`references_code/prompts.yaml`, keeping the prompt registry stable for code and
tests while removing highlights from the supported LLM task surface.

## Scope

- Keep `src/repo/prompts_vi.py` as the single code-facing prompt registry.
- Add `SYSTEM_PROMPT_VI` from `references_code/prompts.yaml`.
- Replace hierarchical title and hierarchical abstractive prompts with the YAML
  versions.
- Include SS-DST prompts from the YAML only if they are already part of the
  rolling-memory summarization path or needed by existing service contracts.
- Remove highlights from `LLMTask` and `get_prompt()` because highlights are out
  of product scope.
- Update unit tests to lock JSON-only behavior, required placeholders, and the
  absence of highlights from the registry.

## Out Of Scope

- No new model inference code.
- No changes to the Sliding TextTiling topic segmentation (NSP-BERT was already removed; current segmentation is purely lexical).
- No reintroduction of highlights extractive or highlights abstractive behavior.
- No runtime prompt loading from `references_code/prompts.yaml`; reference code
  remains a source reference, not a runtime dependency.

## Design

Use a vendored-constant approach:

1. Copy the approved prompt text into Python constants so runtime code does not
   depend on external reference files.
2. Keep prompt names explicit and hierarchical-only:
   - `SYSTEM_PROMPT_VI`
   - `HIERARCHIC_ABSTRACTIVE_PROMPT_VI`
   - `HIERARCHIC_TITLE_PROMPT_VI`
   - optional `SSDST_ABSTRACTIVE_PROMPT_VI`
   - optional `SSDST_STATE_UPDATE_PROMPT_VI`
3. Update `LLMTask` so it represents only LLM-backed recap tasks that remain in
    scope. Topic segmentation is handled by lexical Sliding TextTiling and should not
   be represented as an LLM prompt task.
4. Keep `get_prompt(task)` as the small public interface used by smoke tests and
   future model callers.

## Verification

Run targeted tests first:

```bash
MODEL_LOAD_LLM=0 python3 -m unittest tests.unit.test_prompts_vi -v
```

Then run full verification:

```bash
MODEL_LOAD_LLM=0 python3 -m unittest discover -v
```

## Acceptance Criteria

- Prompt registry contains strict JSON-only system and hierarchical prompts from
  `references_code/prompts.yaml`.
- Prompt registry no longer exposes highlights tasks.
- Tests verify required placeholders for title and abstractive prompts.
- Tests verify all public prompt templates are Vietnamese and non-empty.
- Full unittest suite passes with `MODEL_LOAD_LLM=0`.
