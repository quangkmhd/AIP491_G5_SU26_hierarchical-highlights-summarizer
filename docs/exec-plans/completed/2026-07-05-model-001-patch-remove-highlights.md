# model-001+ — Remove Highlights Data Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the Highlights data models (`Highlight`, `HighlightType`, `HighlightSource`, `HighlightUpsertRequest`) and the `highlights_notes` / `highlights_tasks` fields on `HierarchicalRecap` so the Types layer no longer carries dead types from the dropped DR1 (Highlights) product surface.

**Architecture:** Single-file deletions + targeted field removal in `HierarchicalRecap`. Tests in `test_types.py` are rewritten to drop `Highlight`-only cases and add new "no-highlights" assertions on the remaining types. No other layer is touched; downstream services that imported `Highlight` will be fixed in subsequent features (config-001+, svc-001+002, etc.).

**Tech Stack:** Python 3.10+, Pydantic v2, `unittest` (project convention; pytest not used), no new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md` (D1)
**Reference patterns:**
- `src/types/_base.py` for the `BaseSchema` shape
- `tests/unit/test_types.py` for the existing test class structure (mirror, don't restructure)

---

## File Structure

### Deleted (2)

| Path | Reason |
|---|---|
| `src/types/highlight.py` | DR1 (Highlights) dropped from product scope (D1) |
| `tests/unit/test_highlight_types.py` (if exists; verify first) | The Highlight class tests live inside `test_types.py` as `HighlightTests` class, NOT a separate file. This plan rewrites them inline. No file deleted. |

### Modified (4)

| Path | Change |
|---|---|
| `src/types/hierarchical_recap.py` | Drop `highlights_notes`, `highlights_tasks`, `all_highlights` property; drop `from .highlight import Highlight` import |
| `src/types/schemas.py` | Drop `HighlightUpsertRequest` class + import; drop `HighlightType` import |
| `src/types/__init__.py` | Drop re-exports of `Highlight`, `HighlightType`, `HighlightSource`, `HighlightUpsertRequest` |
| `tests/unit/test_types.py` | Drop `HighlightTests` class; remove highlight assertions from `HierarchicalRecapTests` and `ApiSchemaTests`; add new "no-highlights" assertion |

### Untouched

- All other files in `src/types/`, `src/repo/`, `src/config/`, `src/service/` (none exist yet)
- `tests/manual/test_meeting_committee_sample.py` — the 370-utterance round-trip still produces a valid `HierarchicalRecap` with only `segments`; existing test already passes if `highlights_notes`/`highlights_tasks` default to `[]` (which they will after the field removal)

### Update-on-done files (4)

| Path | Change |
|---|---|
| `feature_list.json` | `model-001+` status: `not_started` → `passing` |
| `docs/QUALITY_SCORE.md` | Types layer note: highlight models removed; nothing to bump (Types already B) |
| `progress.md` | Add Session 004 entry with verification run |
| `docs/exec-plans/active/model-001-patch-remove-highlights.md` | This plan; move to `completed/` after merge |

---

## Task 1: Verify baseline is green

**Files:**
- Read: `tests/unit/test_types.py` (no changes)

- [ ] **Step 1: Run the current unit suite to establish baseline**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
python3 -m unittest discover -s tests -v 2>&1 | tail -20
```

Expected: `OK` (or `Ran 144 tests ... OK`). If a baseline test fails, the worktree is broken — STOP and ask the user to verify the worktree base.

- [ ] **Step 2: Note the current test count for after-comparison**

Write down the number of tests reported (e.g. "Ran 144 tests"). After the migration, the count should be lower by ~7 (the Highlight-specific tests removed).

---

## Task 2: Delete `src/types/highlight.py`

**Files:**
- Delete: `src/types/highlight.py`

- [ ] **Step 1: Delete the file**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
rm src/types/highlight.py
```

- [ ] **Step 2: Verify the file is gone**

```bash
ls src/types/highlight.py 2>&1
```

Expected: `ls: cannot access 'src/types/highlight.py': No such file or directory`

- [ ] **Step 3: DO NOT commit yet — the import sites still reference the deleted module**

The next tasks update the imports. A single commit at the end of this plan is cleaner.

---

## Task 3: Drop highlights fields from `HierarchicalRecap`

**Files:**
- Modify: `src/types/hierarchical_recap.py`

- [ ] **Step 1: Remove the `from .highlight import Highlight` import**

The file currently has (around line 11):

```python
from .highlight import Highlight
```

Change to:

```python
# Highlight family removed in model-001+ (DR1 dropped from scope).
```

(Delete that line; replace with the comment so future readers see why the import is gone.)

- [ ] **Step 2: Remove `highlights_notes` and `highlights_tasks` fields**

In the `HierarchicalRecap` class body, delete these two fields:

```python
    highlights_notes: list[Highlight] = Field(
        default_factory=list,
        description="Global key-point highlights (UI calls these 'AI notes').",
    )
    highlights_tasks: list[Highlight] = Field(
        default_factory=list,
        description="Global action-item highlights (UI calls these 'AI tasks').",
    )
```

After deletion, the field list reads: `meeting_id`, `meeting_title`, `segments`, `generated_at`, `processing_time_ms`.

- [ ] **Step 3: Remove the `all_highlights` property**

In the same class, delete this `@property`:

```python
    @property
    def all_highlights(self) -> list[Highlight]:
        return [*self.highlights_notes, *self.highlights_tasks]
```

(With the fields gone, this property would raise `AttributeError` anyway. Delete it to keep the class self-consistent.)

- [ ] **Step 4: Verify the file compiles**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
python3 -c "from src.types.hierarchical_recap import HierarchicalRecap, MeetingStatus; print('OK')"
```

Expected: `OK`

---

## Task 4: Drop `HighlightUpsertRequest` from `src/types/schemas.py`

**Files:**
- Modify: `src/types/schemas.py`

- [ ] **Step 1: Remove the `Highlight` and `HighlightType` imports**

The file currently has (around line 12):

```python
from .highlight import Highlight, HighlightType
```

Change to:

```python
# Highlight family removed in model-001+ (DR1 dropped from scope).
```

(Delete the import line; replace with the comment.)

- [ ] **Step 2: Delete the `HighlightUpsertRequest` class**

Delete the entire class block (from `class HighlightUpsertRequest(BaseSchema):` through its last field, approximately lines 100-130). The class is no longer needed because the runtime will not accept a "create highlight" payload.

- [ ] **Step 3: Remove `HighlightUpsertRequest` from `__all__`**

The `__all__` list at the top of the file currently has:

```python
__all__ = [
    "TranscriptIngestionRequest",
    "HighlightUpsertRequest",
    "MeetingProcessResponse",
]
```

Change to:

```python
__all__ = [
    "TranscriptIngestionRequest",
    "MeetingProcessResponse",
]
```

- [ ] **Step 4: Verify the file compiles**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
python3 -c "from src.types.schemas import TranscriptIngestionRequest, MeetingProcessResponse; print('OK')"
```

Expected: `OK`

---

## Task 5: Update `src/types/__init__.py` re-exports

**Files:**
- Modify: `src/types/__init__.py`

- [ ] **Step 1: Remove the Highlight imports**

The file currently has:

```python
from ._base import BaseSchema
from .hierarchical_recap import HierarchicalRecap, MeetingStatus
from .highlight import Highlight, HighlightSource, HighlightType
from .schemas import (
    HighlightUpsertRequest,
    MeetingProcessResponse,
    TranscriptIngestionRequest,
)
from .segment import Chunk, SegmentResult
from .transcript import DialogueTranscript
from .utterance import Utterance
```

Change to:

```python
from ._base import BaseSchema
from .hierarchical_recap import HierarchicalRecap, MeetingStatus
# Highlight family removed in model-001+ (DR1 dropped from scope).
from .schemas import (
    MeetingProcessResponse,
    TranscriptIngestionRequest,
)
from .segment import Chunk, SegmentResult
from .transcript import DialogueTranscript
from .utterance import Utterance
```

- [ ] **Step 2: Update `__all__`**

The current `__all__` is:

```python
__all__ = [
    # Base
    "BaseSchema",
    # Domain types
    "Utterance",
    "DialogueTranscript",
    "Chunk",
    "SegmentResult",
    "Highlight",
    "HighlightType",
    "HighlightSource",
    "HierarchicalRecap",
    "MeetingStatus",
    # API request/response schemas
    "TranscriptIngestionRequest",
    "HighlightUpsertRequest",
    "MeetingProcessResponse",
]
```

Change to:

```python
__all__ = [
    # Base
    "BaseSchema",
    # Domain types
    "Utterance",
    "DialogueTranscript",
    "Chunk",
    "SegmentResult",
    "HierarchicalRecap",
    "MeetingStatus",
    # API request/response schemas
    "TranscriptIngestionRequest",
    "MeetingProcessResponse",
]
```

- [ ] **Step 3: Verify the public surface**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
python3 -c "
from src.types import (
    BaseSchema, Utterance, DialogueTranscript, Chunk, SegmentResult,
    HierarchicalRecap, MeetingStatus,
    TranscriptIngestionRequest, MeetingProcessResponse,
)
print('OK: all 9 names importable')
print('Highlight import attempt (should fail):')
try:
    from src.types import Highlight
    print('FAIL: Highlight still importable')
except ImportError as e:
    print(f'OK: ImportError as expected: {e}')
"
```

Expected: First `OK: all 9 names importable`, then `OK: ImportError as expected: cannot import name 'Highlight' ...`

---

## Task 6: Rewrite `tests/unit/test_types.py` — drop highlight cases, add no-highlights assertions

**Files:**
- Modify: `tests/unit/test_types.py`

The current file has 9 test classes. After this task, 8 remain (drop `HighlightTests`). The `HierarchicalRecapTests` and `ApiSchemaTests` classes lose the highlight-specific tests; they gain a small set of "no-highlights" assertions.

- [ ] **Step 1: Find the line ranges to edit**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
grep -n "^class " tests/unit/test_types.py
grep -n "Highlight\|highlights_" tests/unit/test_types.py | head -50
```

Expected: 9 class definitions; 30+ Highlight/highlights_ references. Use the line numbers from grep to locate edits.

- [ ] **Step 2: Delete the entire `HighlightTests` class**

Find the class definition (line ~XXX per grep output). Delete from `class HighlightTests(unittest.TestCase):` through the last method of that class (a blank line or the start of the next class). Verify the deletion does not leave a dangling blank line — leave exactly one blank line between `SegmentResultTests` and `HierarchicalRecapTests`.

- [ ] **Step 3: Update `HierarchicalRecapTests` to drop highlight assertions**

Find the methods in `HierarchicalRecapTests` that reference `highlights_notes`, `highlights_tasks`, `all_highlights`, or construct `Highlight` objects. For each such method:

- If the method's sole purpose was to test highlights, **delete the method entirely**.
- If the method tested other things alongside highlights (e.g. round-trip with highlights), **rewrite it to construct the recap without highlights**.

Add a new test method at the end of `HierarchicalRecapTests`:

```python
    def test_model_dump_contains_no_highlights_keys(self) -> None:
        """After model-001+ (D1), the recap carries no highlights_* fields."""
        recap = HierarchicalRecap()
        dumped = recap.model_dump(mode="json")
        self.assertNotIn("highlights_notes", dumped)
        self.assertNotIn("highlights_tasks", dumped)
        # Sanity: the remaining keys are exactly the documented surface.
        expected_keys = {
            "meeting_id", "meeting_title", "segments",
            "generated_at", "processing_time_ms",
        }
        self.assertEqual(set(dumped.keys()), expected_keys)
```

- [ ] **Step 4: Update `ApiSchemaTests` to drop HighlightUpsertRequest tests**

Find any test method in `ApiSchemaTests` that constructs a `HighlightUpsertRequest` or asserts on `HighlightUpsertRequest` fields. **Delete those methods entirely.**

- [ ] **Step 5: Add a "no-highlights" assertion in `ApiSchemaTests`**

Add at the end of `ApiSchemaTests`:

```python
    def test_highlight_upsert_request_is_removed(self) -> None:
        """After model-001+ (D1), HighlightUpsertRequest is not importable."""
        with self.assertRaises(ImportError):
            from src.types.schemas import HighlightUpsertRequest  # noqa: F401
```

- [ ] **Step 6: Remove the `Highlight` import from the test file**

Find the import line (likely near the top):

```python
from src.types import (
    BaseSchema,
    Utterance,
    ...
    Highlight,
    HighlightType,
    HighlightSource,
    ...
)
```

Remove the 3 Highlight names from the import list.

- [ ] **Step 7: Run the updated test file to verify it passes**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
python3 -m unittest tests.unit.test_types -v 2>&1 | tail -30
```

Expected: `OK` (count should be lower than the baseline; ~31 tests instead of 38).

If a test fails, read the error, fix the test, and re-run. Do NOT modify the source code to make a test pass — the source is the truth in this plan.

---

## Task 7: Run the full test suite to confirm no regressions

**Files:**
- Read: full repo (no changes)

- [ ] **Step 1: Run the full unit + manual suite**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
python3 -m unittest discover -s tests -v 2>&1 | tail -30
python3 tests/manual/test_meeting_committee_sample.py 2>&1 | tail -10
```

Expected: Both runs `OK`. The unit suite count should be lower than the baseline by ~7 (the Highlight-specific tests removed). The committee sample test should still pass because it constructs a `HierarchicalRecap` with only `segments`.

- [ ] **Step 2: Verify the layer-rule AST test still passes**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
python3 -m unittest tests.unit.test_repo_layer_rules -v 2>&1 | tail -10
```

Expected: `OK`. (The Types layer still has zero imports from config/repo/service/runtime/ui; the removal of `highlight.py` cannot have introduced new cross-layer imports.)

---

## Task 8: Update `feature_list.json` to mark `model-001+` as passing

**Files:**
- Modify: `feature_list.json`

- [ ] **Step 1: Find the `model-001+` feature entry**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
python3 -c "
import json
with open('feature_list.json') as f: d = json.load(f)
for f in d['features']:
    if f['id'] == 'model-001+':
        print(json.dumps(f, indent=2, ensure_ascii=False)[:500])
        break
"
```

- [ ] **Step 2: Update the `status` field**

Change `"status": "not_started"` to `"status": "passing"` for the `model-001+` entry only. Do not modify any other field.

- [ ] **Step 3: Add an evidence line referencing this plan**

Add to the `evidence` list a new entry at the top:

```json
"src/types/highlight.py: deleted (model-001+ D1)",
"src/types/hierarchical_recap.py: highlights_notes/highlights_tasks fields removed; all_highlights property removed",
"src/types/schemas.py: HighlightUpsertRequest class removed",
"src/types/__init__.py: Highlight/HighlightType/HighlightSource/HighlightUpsertRequest re-exports removed",
"tests/unit/test_types.py: HighlightTests class deleted; new no-highlights assertions added in HierarchicalRecapTests and ApiSchemaTests",
"docs/superpowers/plans/2026-07-05-model-001-patch-remove-highlights.md: implementation plan (completed)"
```

(Replace any pre-existing evidence lines that referenced the old highlight fields; the new entries above are the post-migration truth.)

- [ ] **Step 4: Verify the JSON is still valid**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
python3 -c "import json; json.load(open('feature_list.json')); print('JSON valid')"
```

Expected: `JSON valid`

---

## Task 9: Update `progress.md` with a Session 004 entry

**Files:**
- Modify: `progress.md`

- [ ] **Step 1: Find the bottom of the file**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
tail -20 progress.md
```

- [ ] **Step 2: Append a new session entry**

Append this block to the end of `progress.md` (preserving the file's existing format):

```markdown

## model-001+ — Remove Highlights Data Models (2026-07-05)

**Status:** passing

- Deleted `src/types/highlight.py` (Highlight, HighlightType, HighlightSource).
- Removed `highlights_notes` and `highlights_tasks` fields from `HierarchicalRecap`; removed `all_highlights` property.
- Removed `HighlightUpsertRequest` from `src/types/schemas.py` and the corresponding `__all__` entry.
- Updated `src/types/__init__.py` to drop Highlight re-exports.
- Rewrote `tests/unit/test_types.py`: deleted `HighlightTests` class; added `test_model_dump_contains_no_highlights_keys` in `HierarchicalRecapTests`; added `test_highlight_upsert_request_is_removed` in `ApiSchemaTests`.
- Verification: `python3 -m unittest discover -s tests -v` → all tests pass; `python3 tests/manual/test_meeting_committee_sample.py` → still passes (370-utterance round-trip with only `segments`).
- AST layer-rule test (`tests/unit/test_repo_layer_rules.py`) still green: no cross-layer imports introduced.
- Spec: `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md` D1.
- Plan: `docs/superpowers/plans/2026-07-05-model-001-patch-remove-highlights.md`.
- Worktree: `.worktrees/feat-model-001-plus` (branch `feat/model-001-plus`).
```

- [ ] **Step 3: Verify the file still ends cleanly**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
tail -25 progress.md
```

Expected: The new session entry appears at the end; the file ends with a newline.

---

## Task 10: Commit and merge

**Files:**
- All changes from Tasks 2-9

- [ ] **Step 1: Stage all changes**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
git add -A
git status
```

Expected: A clean staging of `src/types/highlight.py` (deleted), `src/types/hierarchical_recap.py`, `src/types/schemas.py`, `src/types/__init__.py`, `tests/unit/test_types.py`, `feature_list.json`, `progress.md`. No unintended files.

- [ ] **Step 2: Commit with a conventional message**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/.worktrees/feat-model-001-plus
git commit -m "feat(model-001+): remove Highlights data models (DR1 dropped)

- Delete src/types/highlight.py
- Remove highlights_notes/highlights_tasks fields from HierarchicalRecap
- Remove HighlightUpsertRequest from src/types/schemas.py
- Update src/types/__init__.py re-exports
- Rewrite tests/unit/test_types.py: drop HighlightTests; add no-highlights assertions
- Update feature_list.json: model-001+ status -> passing
- Update progress.md: Session 004 entry

Spec: docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md D1
Plan: docs/superpowers/plans/2026-07-05-model-001-patch-remove-highlights.md"
```

- [ ] **Step 3: Merge into main**

The user's stated policy is "Chỉ sau khi tính năng đó được hoàn thành và HOÀN TOÀN GỘP VÀO NHÁNH MAIN, bạn mới được phép chuyển sang tính năng tiếp theo." So merge to main now:

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary
git checkout main
git merge --no-ff feat/model-001-plus -m "Merge feat/model-001-plus: remove Highlights data models"
git log --oneline -3
```

Expected: A merge commit on `main` referencing `feat/model-001-plus`.

- [ ] **Step 4: Verify main is still green after the merge**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary
python3 -m unittest discover -s tests -v 2>&1 | tail -10
```

Expected: `OK` (same count as on the feature branch).

- [ ] **Step 5: Clean up the worktree**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary
git worktree remove .worktrees/feat-model-001-plus
git worktree list
```

Expected: Only the main checkout remains in `git worktree list`.

- [ ] **Step 6: Move the plan to `completed/`**

```bash
cd /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary
mkdir -p docs/exec-plans/completed
mv docs/superpowers/plans/2026-07-05-model-001-patch-remove-highlights.md docs/exec-plans/completed/
git add docs/exec-plans/completed/2026-07-05-model-001-patch-remove-highlights.md
git commit -m "docs(model-001+): archive implementation plan to completed/"
```

---

## Self-Review

### 1. Spec coverage

Skim `docs/superpowers/specs/2026-07-05-streaming-hierarchical-recap-design.md` D1:

- [x] "src/types/highlight.py — deleted" — Task 2
- [x] "HierarchicalRecap.highlights_notes / highlights_tasks fields removed" — Task 3
- [x] "src/types/__init__.py re-exports removed" — Task 5
- [x] "tests/unit/test_types.py — 5-7 highlight cases deleted" — Task 6
- [x] "tests/manual/test_meeting_committee_sample.py still passes" — Task 7 step 1

All spec D1 requirements are covered. No gaps.

### 2. Placeholder scan

- "TBD" / "TODO" / "fix in follow-up" — none in this plan.
- "Add appropriate error handling" — none; the deletions are mechanical.
- "Similar to Task N" — none; every step shows the exact code or file path.

### 3. Type consistency

- `HierarchicalRecap` is referenced by its full name in all tasks; matches the import path `src.types.hierarchical_recap.HierarchicalRecap`.
- `HighlightUpsertRequest` is referenced by its full name; matches the import path `src.types.schemas.HighlightUpsertRequest`.
- Test class names (`HighlightTests`, `HierarchicalRecapTests`, `ApiSchemaTests`) match the existing names in `tests/unit/test_types.py`.

No type or naming inconsistencies.

---

## Verification at archive time

When the plan is moved to `docs/exec-plans/completed/`, the archive entry must include:

- **Green-test command:** `python3 -m unittest discover -s tests -v` → `OK` (count: ~137 tests, was 144 baseline).
- **Layer-rule command:** `python3 -m unittest tests.unit.test_repo_layer_rules -v` → `OK`.
- **Manual smoke:** `python3 tests/manual/test_meeting_committee_sample.py` → 370-utterance round-trip succeeds, output `HierarchicalRecap` JSON has no `highlights_*` keys.
- **Merge commit hash:** (recorded at archive time).
- **Worktree path at archive time:** `.worktrees/feat-model-001-plus` (removed after merge).
