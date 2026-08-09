# Custom 10h Speaker-Domain Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent Custom_10h CAM++ display labels from becoming semantic entities in ViT5 summaries, then measure the correction on GPU without overwriting the baseline.

**Architecture:** Preserve speaker diarization artifacts, normalize speaker identities only at the ViT5 formatting boundary, and version the pipeline cache contract. Validate behavior with focused tests before a real-model ablation and a new persisted evaluation run.

**Tech Stack:** Python 3, pytest, PyTorch/Transformers, existing Custom_10h evaluation CLI, CAM++ cached artifacts, DeepSeek judge.

## Global Constraints

- Do not modify the user's unrelated dirty report or topic-titler files.
- Preserve the completed `custom-10h-full-v1` baseline artifacts.
- Reuse cached ASR and CAM++ results.
- Each summary chunk contains at most eight utterances.

---

### Task 1: Normalize Speaker Labels at the ViT5 Boundary

**Files:**
- Modify: `training-eval-suite/tests/custom_10h_summary/test_recap_models.py`
- Modify: `training-eval-suite/src/evaluate/custom_10h_summary/recap_models.py`

**Interfaces:**
- Consumes: `Sequence[TranscriptUtterance]`
- Produces: `format_chunk_input(items) -> str` using first-seen labels `no.0`, `no.1`, ...

- [ ] Add a failing test expecting `Speaker 01: a\nSpeaker 02: b\nSpeaker 01: c` to format as `no.0: a\nno.1: b\nno.0: c`.
- [ ] Run `pytest tests/custom_10h_summary/test_recap_models.py -q` and confirm the literal-label assertion fails.
- [ ] Implement deterministic first-appearance remapping inside `format_chunk_input`.
- [ ] Update the generation-contract assertion to require `Tóm tắt: no.0: nội dung`.
- [ ] Run the focused test file and confirm it passes.

### Task 2: Invalidate Only Stale Pipeline Outputs

**Files:**
- Modify: `training-eval-suite/tests/custom_10h_summary/test_cli.py`
- Modify: `training-eval-suite/src/evaluate/custom_10h_summary/cli.py`

**Interfaces:**
- Consumes: transcript, segmenter, and model fingerprints
- Produces: pipeline cache keys containing `speaker-colon-text-train-labels-v2`

- [ ] Add a failing CLI/cache test that observes a cache miss for the corrected formatter version while ASR and speaker cache inputs stay reusable.
- [ ] Run the focused test and confirm failure against the v1 fingerprint.
- [ ] Replace the pipeline format fingerprint with `speaker-colon-text-train-labels-v2`.
- [ ] Run all `tests/custom_10h_summary` tests.

### Task 3: Real-Model GPU Validation

**Files:**
- Create through CLI: `training-eval-suite/eval_results/custom_10h_summary/runs/custom-10h-speaker-fix-ablation/`
- Create through CLI after positive ablation: `training-eval-suite/eval_results/custom_10h_summary/runs/custom-10h-full-v2/`

**Interfaces:**
- Consumes: existing Custom_10h WAVs and content-addressed ASR/CAM++ caches
- Produces: persisted topic outputs, AI judgments, compatibility audit, aggregate metrics, and report

- [ ] Run a small corrected GPU evaluation under a new run ID.
- [ ] Compare literal `Speaker` leakage and AI scores with matching baseline topics.
- [ ] If the ablation improves the diagnosed failure mode, run all 246 topics under `custom-10h-full-v2`.
- [ ] Recompute aggregate totals independently and verify no API key appears in artifacts.
- [ ] Run the complete relevant test suites and record exact results.
