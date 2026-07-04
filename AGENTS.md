# AGENTS.md — Project Navigation Map

> **Role:** Entry point for any AI agent session. Read this first — every time, even if you think you know the project.

## 1. What Is This System?

A **research pipeline for dialogue topic segmentation (DTS)** that combines:

- **Neural utterance-pair coherence scoring** (Xing & Carenini, SIGDIAL-21) to improve unsupervised DTS
- **LLM-powered hierarchical meeting recap** (Asthana et al., CSCW-25) for structured meeting summarization

**Goal:** Build a novel system that replaces basic TextTiling with coherence-enhanced segmentation in meeting recap pipelines, then evaluate improvements quantitatively and qualitatively. Target output: a publishable research paper.

## 2. How Is It Organized?

```
.
├── AGENTS.md                  ← You are here (project map)
├── README.md                  ← Human-facing overview
├── CLAUDE.md                  ← Claude Code specific guidance (auto-loaded each session)
├── PROGRESS.md                ← Session-to-session state tracker (READ THIS NEXT)
├── feature_list.json          ← Decomposed task list with pass/fail status
├── init.sh                    ← One-command reproducible dev environment
├── Makefile                   ← Common commands: lint, test, run, clean
├── pyproject.toml             ← Python project config with pinned dependencies
│
├── papers/                    ← Reference papers (PDF + converted MD)
│   ├── *.pdf                  ← Original papers — preserve, never overwrite
│   └── *.md                   ← Converted markdown versions
│
├── docs/                      ← Knowledge architecture (repo as source of truth)
│   ├── design-docs/           ← Core architecture decisions, research hypotheses
│   ├── exec-plans/            ← Execution plans, experiment tracking, tech debt log
│   ├── generated/             ← Auto-generated (e.g., experiment result tables)
│   └── references/            ← LLM reference docs for tools (markitdown, pdfplumber, etc.)
│
├── data/                      ← Standardized DTS datasets
│   ├── train/                 ← Training data (DailyDial EN + VI)
│   └── eval/                  ← Evaluation data (DialSeg, Doc2Dial, Tiage, AMI, ICSI, Committee + VI variants)
│
├── src/                       ← Source code (to be built)
│   ├── coherence/             ← Utterance-pair coherence scoring model
│   ├── segmentation/          ← Topic segmentation (TextTiling + coherence-enhanced)
│   ├── summarization/         ← Meeting recap generation (highlights + hierarchical)
│   └── evaluation/            ← Metrics: Pk, WinDiff, F1, user-study framework
│
└── outputs/                   ← Experiment outputs, generated summaries, evaluation results
```

## 3. How to Run It?

### Prerequisites (what must exist on the machine BEFORE `init.sh`)

These are **system-level requirements** — `init.sh` checks for them but does NOT install them:

| Requirement | Check command | Install (Ubuntu/Debian) | Install (macOS) |
|---|---|---|---|
| Python 3.10+ | `python3 --version` | `sudo apt install python3` | `brew install python@3.10` |
| pip | `pip --version` | `sudo apt install python3-pip` | (comes with brew python) |
| venv | `python3 -m venv --help` | `sudo apt install python3-venv` | (comes with brew python) |
| git | `git --version` | `sudo apt install git` | `brew install git` |
| poppler-utils | `pdftotext -v` | `sudo apt install poppler-utils` | `brew install poppler` |

**Quick check all prerequisites:**
```bash
python3 --version && pip --version && python3 -m venv --help >/dev/null 2>&1 && echo "venv: OK" && git --version && pdftotext -v 2>&1 | head -1
```

### Datalab API Key (required for PDF → Markdown conversion)

Create `.env` in the project root:
```env
DATALAB_API_KEY_2=your_api_key_here
```
If you don't have an API key, skip this — the converted `.md` files are already committed in `papers/`.

### First-Time Setup

```bash
# 1. Clone Paper 1's reference implementation
git clone https://github.com/lxing532/Dialogue-Topic-Segmenter references/dialogue-topic-segmenter/

# 2. Run init.sh — creates .venv, installs pinned deps, downloads BERT/BART models, smoke test
bash init.sh

# 3. Activate environment (MUST do this in every new shell session)
source .venv/bin/activate

# 4. Verify the full pipeline initializes correctly
make verify
```

### What `init.sh` Does (5 steps)

1. **Create virtual environment** — `python3 -m venv .venv`
2. **Install pinned dependencies** — from `pyproject.toml` (or `requirements.txt`), all pinned to exact versions
3. **Download NLP data** — NLTK punkt/stopwords, spaCy model (en_core_web_sm)
4. **Cache pre-trained models** — BERT-base-uncased (coherence scoring), BART-large (summarization)
5. **Smoke test** — runs a minimal pipeline (load model → segment 1 dialogue → summarize) to confirm everything works

### Daily Usage (every new session)

```bash
source .venv/bin/activate    # ← ALWAYS do this first

# Common commands (see Makefile):
make lint       # Run ruff linter
make typecheck  # Run mypy type checking
make test       # Run pytest with coverage
make verify     # Full verification: lint → typecheck → test (must pass before commit)
make train-coherence   # Train utterance-pair coherence model
make segment     # Run topic segmentation on eval datasets
make recap       # Generate meeting recaps from segmented transcripts
make evaluate    # Compute P_k, WinDiff, F1 metrics
make paper-figs  # Generate figures and tables for the paper
```

## 4. How to Verify/Test It?

**Required before every commit:**

```bash
make verify
```

This runs: `ruff check` → `mypy src/` → `pytest -x --cov=src/`. All must pass.

**Individual verification commands:**

- `make lint` — Code style and basic bug detection
- `make typecheck` — Static type correctness
- `make test` — Unit + integration tests
- `make test-e2e` — End-to-end: segment → summarize → evaluate one full dataset

## 5. Where Is the Project Now?

**Read `PROGRESS.md`** — it tracks every completed task, current work-in-progress, and blocked items across sessions. Also check `feature_list.json` for detailed decomposed task status.

Quick status: `git log --oneline -5` and `grep -c '"passes": true' feature_list.json`

---

## Core Principles for Agents

1. **Repo as Source of Truth.** Information not in this repo does not exist for you. Don't guess — read the relevant file in `docs/design-docs/` or `docs/references/`.
2. **One Task Per Session.** Pick the highest-priority `passes: false` item from `feature_list.json`. Focus on it exclusively. Don't multi-task.
3. **Clean Handoff.** Before ending a session, you MUST:

   - Run `make verify` and ensure all checks pass
   - Commit with a clear message: `git commit -m "<type>: <what was done>"`
   - Update `feature_list.json` — set `passes: true` for completed items
   - Update `PROGRESS.md` — log what was done, what's next, any blockers
4. **Diagnostic Loop.** When something fails → classify the failure (vague spec? missing tool? env issue?) → fix the harness → retry. Do NOT silently skip failing checks.
5. **Verify, Don't Assume.** Use `make verify` as concrete proof. "Looks correct" is not verification. If `make verify` fails, the task is NOT done.
6. **Knowledge lives next to code.** Put architecture notes in the module's directory, not in a monolithic doc. Proximity > length.

---

## Key References

- Paper 1 (coherence scoring): `papers/improving-unsupervised-dialogue-topic-segmentation.md`
- Paper 2 (meeting recap): `papers/llm-powered-meeting-recap-system.md`
- Original code (Paper 1): [references/dialogue-topic-segmenter/](file:///home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/references/dialogue-topic-segmenter) (cloned from https://github.com/lxing532/Dialogue-Topic-Segmenter)
- Data format spec: `data/README.md`
- Datasets: `data/eval/*.json`

---

_Last updated: 2026-07-04 | Harness v1.0_
