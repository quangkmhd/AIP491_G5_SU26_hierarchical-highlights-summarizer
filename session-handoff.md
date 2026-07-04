# Session Handoff Template

> **Purpose:** Ensures the next agent session can resume work immediately without re-discovering context.
> **Use:** Fill this out at the END of every session, before committing. The next agent reads this FIRST after `AGENTS.md`.

---

## Handoff — Session: [DATE-TIME]

### Active Feature

**Feature ID:** [e.g. C005]
**Feature Name:** [e.g. Implement BERT NSP coherence scoring model]
**Phase:** [e.g. Phase 2: Core Pipeline Implementation]

### Status

**Percent Complete:** [e.g. 60%]
**What Works:**
- [e.g. BERT model loads and forward pass runs]
- [e.g. Dataset builder creates positive/negative pairs]

**What's In Progress:**
- [e.g. Implementing marginal ranking loss]
- [e.g. Writing training loop]

### Blockers

- [list any blockers, or write "None"]
- [if blocked, include: what's blocking, who can resolve, resolution plan]

### Files Touched This Session

```
[list files modified/created, one per line]
src/coherence/model.py
src/coherence/dataset.py
tests/unit/test_coherence_model.py
```

### Verification Status

```bash
make verify    # [PASS / FAIL — if FAIL, explain why]
```
- Lint: [PASS/FAIL]
- Typecheck: [PASS/FAIL]
- Tests: [PASS/FAIL — N passed, M failed]

### Next Session Should

1. [First action for next agent — be specific, reference exact file paths]
2. [Second action]
3. [Third action]

### Notes / Discoveries

- [Any discoveries, gotchas, or context the next agent needs]
- [e.g. "BERT NSP head needs custom modification — see docs/design-docs/002-nsp-adaptation.md"]
- [e.g. "Training is slow on CPU — recommend GPU or reduce batch size for testing"]

### Evidence

- [Link to test output, screenshots, or verification results]
- [e.g. "Coherence scores on sample dialogue: see outputs/results/sample-scores.json"]

---

_Completed: [TIME] — Committed as: [COMMIT HASH / MESSAGE]_