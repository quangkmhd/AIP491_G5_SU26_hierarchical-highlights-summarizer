# Custom 10h Human-Only Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make offline human review the only Custom_10h summary-quality evaluation path.

**Architecture:** End the model pipeline after topic generation and compatibility audit, then generate `human_evaluation.html`. Persist human-only manifest state and retain no programmatic quality-scoring component or scored run artifact.

**Tech Stack:** Python 3, pytest, HTML/CSS/vanilla JavaScript, localStorage.

## Global Constraints

- Preserve ASR, CAM++, topic outputs, input diagnostics, and unrelated dirty files.
- Remove scored artifacts and obsolete cache from v1 and v2.
- Do not claim human evaluation is complete before exported human ratings exist.
- Work on the current branch.

---

### Task 1: Human-Only Pipeline Contract

**Files:**
- Modify: `training-eval-suite/tests/custom_10h_summary/test_cli.py`
- Modify: `training-eval-suite/src/evaluate/custom_10h_summary/cli.py`
- Modify: `training-eval-suite/src/evaluate/custom_10h_summary/artifacts.py`
- Modify: `training-eval-suite/src/evaluate/custom_10h_summary/human_evaluation.py`

**Interfaces:**
- Consumes: generated `TopicOutput` records
- Produces: `human_evaluation.html` and manifest fields `evaluation_mode=human`, `human_evaluation_status=pending`

- [ ] Add failing tests that require a no-credential run, no obsolete CLI controls, human manifest fields, and generated review HTML.
- [ ] Run focused tests and confirm failure against the old pipeline.
- [ ] Remove the obsolete stage and generate the review page atomically after topic persistence.
- [ ] Run focused tests and confirm they pass.

### Task 2: Remove Obsolete Components and Documentation

**Files:**
- Delete: obsolete evaluator source and tests under `training-eval-suite/src/evaluate/custom_10h_summary` and `tests/custom_10h_summary`
- Modify: `training-eval-suite/openwiki/quickstart.md`
- Modify: `training-eval-suite/openwiki/operations/custom-10h-summary-evaluation.md`
- Delete: superseded Custom_10h design/plan documents that describe the old workflow

**Interfaces:**
- Consumes: human-only CLI and page generator
- Produces: documentation and test collection containing only the human-review path

- [ ] Remove imports, artifact names, report generation, source modules, and tests belonging only to the old workflow.
- [ ] Rewrite operations and quickstart instructions around page generation and exported human ratings.
- [ ] Scan the scoped files for obsolete terms and run the full test suite.

### Task 3: Purge Derived Run Artifacts

**Files:**
- Modify: v1/v2 `manifest.json`
- Delete: scored artifacts in v1/v2 and their shared scored-result cache namespace
- Generate: v1/v2 `human_evaluation.html`

**Interfaces:**
- Consumes: retained `topic_outputs.jsonl`
- Produces: two human-review-ready runs with no pre-existing quality result

- [ ] Resolve and list exact deletion targets before deletion.
- [ ] Delete only the approved derived artifacts and cache namespace.
- [ ] Sanitize manifests and generate both review pages.
- [ ] Verify retained artifact counts, browser loading, scoped repository scan, and tests.
