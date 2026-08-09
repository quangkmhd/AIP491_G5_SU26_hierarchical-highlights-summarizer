# Custom 10h Human Evaluation HTML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a self-contained offline HTML application for human scoring of all Custom_10h topic summaries.

**Architecture:** A Python module validates JSONL topic outputs and renders a static HTML template with safely embedded JSON. Vanilla JavaScript renders the review workflow, calculates rubric totals, persists ratings in localStorage, and imports/exports portable JSON.

**Tech Stack:** Python 3, pytest, HTML5, CSS, vanilla JavaScript, browser localStorage.

## Global Constraints

- Read only `topic_outputs.jsonl`; do not embed AI judgments or `.env` values.
- Preserve one WAV as one utterance and show the complete topic evidence.
- Work on the current branch and preserve unrelated dirty files.
- The generated page must work from `file://` without a server or CDN.

---

### Task 1: HTML Generator Contract

**Files:**
- Create: `training-eval-suite/tests/custom_10h_summary/test_human_evaluation.py`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/human_evaluation.py`

**Interfaces:**
- Consumes: `Path` to a JSONL file containing serialized `TopicOutput` records
- Produces: `load_topics(path) -> list[dict]` and `build_human_evaluation_html(topics, run_id) -> str`

- [ ] Write fixture-based failing tests for ordered topic loading, invalid records, safe `</script>` embedding, offline assets, and required review controls.
- [ ] Run the focused test file and confirm failure because the module is absent.
- [ ] Implement validated loading and template rendering without reading any other run artifact.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Manual Scoring Application

**Files:**
- Modify: `training-eval-suite/src/evaluate/custom_10h_summary/human_evaluation.py`
- Modify: `training-eval-suite/tests/custom_10h_summary/test_human_evaluation.py`

**Interfaces:**
- Consumes: embedded topic list and browser form events
- Produces: versioned localStorage state, exact rubric total, filtering/navigation, JSON import/export

- [ ] Add failing tests for presence of the score dimensions, run-specific storage key, import/export schema, and absence of AI score fields.
- [ ] Run tests and confirm the expected UI contract is missing.
- [ ] Implement responsive navigation, evidence display, 0–5 inputs, flags, notes, automatic scoring, completion/review state, localStorage, and JSON portability.
- [ ] Run focused and complete Custom_10h tests.

### Task 3: CLI Generation and Real Artifact

**Files:**
- Create: `training-eval-suite/scripts/generate_custom_10h_human_eval.py`
- Modify: `training-eval-suite/openwiki/operations/custom-10h-summary-evaluation.md`
- Generate: `training-eval-suite/eval_results/custom_10h_summary/runs/custom-10h-full-v2/human_evaluation.html`

**Interfaces:**
- Consumes: `--run-dir` and optional `--output`
- Produces: a self-contained HTML file and prints its resolved path

- [ ] Add a failing subprocess test that invokes the script on a fixture run.
- [ ] Implement argument parsing and atomic output writing.
- [ ] Generate the real 246-topic artifact and verify the embedded count and file size.
- [ ] Run browser smoke checks when a headless browser is available, then run all relevant project tests.
