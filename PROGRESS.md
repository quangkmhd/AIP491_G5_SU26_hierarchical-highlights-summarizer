# PROGRESS.md — Session-to-Session State Tracker

> **Role:** This file maintains continuity across agent sessions. Every agent MUST read this after AGENTS.md to understand current project state.
>
> **Principle (Durability):** Knowledge in session memory evaporates when the agent exits. Only what's written here survives.

---

## Current Status Overview

| Metric | Value |
|---|---|
| Date | 2026-07-04 |
| Phase | **Phase 0: Harness Setup** |
| Completed Features | 0/? |
| Failing Features | ? (feature_list.json not yet created) |
| Last Commit | `6eb8501` — Initial commit |
| Active Blocker | None |

---

## Phase Map

```
Phase 0: Harness Setup          [IN PROGRESS]
Phase 1: Reference Code Study   [  ]
Phase 2: Core Pipeline Build    [  ]
Phase 3: Integration & Eval     [  ]
Phase 4: Paper Writing          [  ]
```

---

## Session Log

### Session 2026-07-04-01 — Harness Setup

**Completed:**
- [x] Created `AGENTS.md` — project navigation map covering all 5 Fresh Session Test questions
- [x] Created `docs/design-docs/` — architecture decisions directory
- [x] Created `docs/exec-plans/` — execution plans & tech debt tracking
- [x] Created `docs/generated/` — auto-generated outputs
- [x] Created `docs/references/` — LLM reference docs
- [x] Added detailed environment setup prerequisites to `AGENTS.md` Section 3

**In Progress:**
- [ ] `PROGRESS.md` — this file (being written now)
- [ ] `feature_list.json` — decomposed task list
- [ ] `init.sh` — reproducible environment setup script
- [ ] `pyproject.toml` — pinned Python dependencies
- [ ] `Makefile` — common commands (lint, test, verify, etc.)
- [ ] `src/` directory structure — coherence/, segmentation/, summarization/, evaluation/

**Next Session Should:**
1. Complete remaining harness files (feature_list.json, init.sh, pyproject.toml, Makefile)
2. Create `src/` directory structure with module `__init__.py` files
3. Clone reference code: `references/dialogue-topic-segmenter/`
4. Create `docs/design-docs/001-research-hypothesis.md` — formalize the research question
5. Begin Phase 1: Study reference code architecture

**Blockers:** None

---

## Decisions Made

| Decision | Rationale | Date |
|---|---|---|
| Use AGENTS.md (~100 lines) as entry point | Lecture 03 — repo as source of truth, Fresh Session Test | 2026-07-04 |
| Use docs/ subdirectory architecture | Lecture 03 — `AGENTS.md → docs/{design-docs,exec-plans,generated,references}` pattern | 2026-07-04 |
| Core hypothesis: coherence-enhanced segmentation improves meeting recap | Combines SIGDIAL-21 coherence scoring with CSCW-25 meeting recap pipeline | 2026-07-04 |
| Target both EN and VI evaluation | Leverage existing `data/eval_vi/` datasets for multilingual contribution | 2026-07-04 |

---

## Technical Debt

_None yet — project just initialized._

---

_Last updated: 2026-07-04_