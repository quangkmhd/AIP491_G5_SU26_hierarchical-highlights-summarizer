# Prompt Registry Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace prototype Vietnamese LLM prompts with the approved hierarchical JSON-only prompt set from `references_code/prompts.yaml` and remove highlights from the active prompt registry.

**Architecture:** `src/repo/prompts_vi.py` remains the single code-facing prompt registry in the Repo layer. Prompt text is vendored into Python constants so production code does not read from `references_code/` at runtime. Tests lock the public enum, prompt placeholders, JSON-only constraints, and hierarchical-only scope.

**Tech Stack:** Python stdlib `enum`, `unittest`, existing repo-layer prompt registry.

---

## File Structure

- Modify `src/repo/prompts_vi.py`: replace prototype prompts with vendored YAML prompt constants; remove `HIGHLIGHTS` from `LLMTask`; add `SYSTEM_PROMPT_VI`; keep `get_prompt(task)` as registry interface.
- Modify `src/repo/__init__.py`: update repo exports to match prompt registry changes.
- Modify `src/repo/smoke_loader.py`: ensure smoke check iterates current `LLMTask` values and validates `SYSTEM_PROMPT_VI` without expecting highlights.
- Modify `tests/unit/test_prompts_vi.py`: update tests for hierarchical-only prompt registry and required placeholders.
- Modify `docs/QUALITY_SCORE.md`: add a benchmark/simplification note after verification.

## Task 1: Prompt Registry Tests

**Files:**
- Modify: `tests/unit/test_prompts_vi.py`
- Reference: `references_code/prompts.yaml`

- [x] **Step 1: Replace prompt tests with hierarchical-only expectations**

Use this complete test file:

```python
"""Unit tests for Vietnamese prompt templates."""

import unittest

from src.repo.prompts_vi import (
    HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
    HIERARCHIC_TITLE_PROMPT_VI,
    LLMTask,
    SSDST_ABSTRACTIVE_PROMPT_VI,
    SSDST_STATE_UPDATE_PROMPT_VI,
    SYSTEM_PROMPT_VI,
    get_prompt,
)


class TestPromptsVi(unittest.TestCase):
    def test_public_prompts_present_and_non_empty(self) -> None:
        for name, text in [
            ("system", SYSTEM_PROMPT_VI),
            ("hierarchical_abstractive", HIERARCHIC_ABSTRACTIVE_PROMPT_VI),
            ("hierarchical_title", HIERARCHIC_TITLE_PROMPT_VI),
            ("ssdst_abstractive", SSDST_ABSTRACTIVE_PROMPT_VI),
            ("ssdst_state_update", SSDST_STATE_UPDATE_PROMPT_VI),
        ]:
            self.assertTrue(text.strip(), f"{name} prompt is empty")
            self.assertGreater(len(text), 500, f"{name} prompt too short")
            self.assertIn("tiếng Việt", text)

    def test_llm_task_enum_is_hierarchical_only(self) -> None:
        self.assertEqual(
            {task.name for task in LLMTask},
            {"ABSTRACTIVE", "TITLE", "SSDST_ABSTRACTIVE", "SSDST_STATE_UPDATE"},
        )
        self.assertNotIn("HIGHLIGHTS", {task.name for task in LLMTask})
        self.assertNotIn("SEGMENT", {task.name for task in LLMTask})

    def test_get_prompt_returns_correct_template(self) -> None:
        self.assertIs(get_prompt(LLMTask.ABSTRACTIVE), HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        self.assertIs(get_prompt(LLMTask.TITLE), HIERARCHIC_TITLE_PROMPT_VI)
        self.assertIs(get_prompt(LLMTask.SSDST_ABSTRACTIVE), SSDST_ABSTRACTIVE_PROMPT_VI)
        self.assertIs(get_prompt(LLMTask.SSDST_STATE_UPDATE), SSDST_STATE_UPDATE_PROMPT_VI)

    def test_system_prompt_requires_strict_json_only(self) -> None:
        self.assertIn("Chỉ trả về JSON parseable", SYSTEM_PROMPT_VI)
        self.assertIn("Không dùng Markdown", SYSTEM_PROMPT_VI)
        self.assertIn("Không bịa", SYSTEM_PROMPT_VI)
        self.assertIn('"none"', SYSTEM_PROMPT_VI)

    def test_hierarchical_title_placeholders_and_schema(self) -> None:
        for placeholder in ["{input_name}", "{chapter_number}", "{segment_utterances}"]:
            self.assertIn(placeholder, HIERARCHIC_TITLE_PROMPT_VI)
        self.assertIn('"title"', HIERARCHIC_TITLE_PROMPT_VI)
        self.assertIn('"one_line_summary"', HIERARCHIC_TITLE_PROMPT_VI)
        self.assertIn("Return strict JSON only", HIERARCHIC_TITLE_PROMPT_VI)

    def test_hierarchical_abstractive_placeholders_and_schema(self) -> None:
        for placeholder in [
            "{input_name}",
            "{chapter_number}",
            "{required_chunk_ids}",
            "{prompt_chunks}",
            "{example_chunk_id}",
        ]:
            self.assertIn(placeholder, HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        self.assertIn('"notes"', HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        self.assertIn('"chunk_id"', HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        self.assertIn('"contains_key_point"', HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        self.assertIn('"contains_action_item"', HIERARCHIC_ABSTRACTIVE_PROMPT_VI)

    def test_ssdst_prompts_keep_rolling_memory_contract(self) -> None:
        for placeholder in [
            "{input_name}",
            "{chapter_number}",
            "{chunk_index}",
            "{belief_state}",
            "{required_chunk_ids}",
            "{prompt_chunks}",
            "{example_chunk_id}",
        ]:
            self.assertIn(placeholder, SSDST_ABSTRACTIVE_PROMPT_VI)
        for placeholder in [
            "{chapter_number}",
            "{chunk_index}",
            "{previous_state}",
            "{chunk_text}",
            "{chunk_summary}",
        ]:
            self.assertIn(placeholder, SSDST_STATE_UPDATE_PROMPT_VI)
        self.assertIn('"current_topic"', SSDST_STATE_UPDATE_PROMPT_VI)
        self.assertIn('"resolved_references"', SSDST_STATE_UPDATE_PROMPT_VI)


if __name__ == "__main__":
    unittest.main()
```

- [x] **Step 2: Run test to verify it fails before implementation**

Run:

```bash
MODEL_LOAD_LLM=0 python3 -m unittest tests.unit.test_prompts_vi -v
```

Expected: FAIL because `SYSTEM_PROMPT_VI`, `SSDST_ABSTRACTIVE_PROMPT_VI`, and `SSDST_STATE_UPDATE_PROMPT_VI` are not exported yet, and old `LLMTask` still contains `SEGMENT` and `HIGHLIGHTS`.

## Task 2: Prompt Registry Implementation

**Files:**
- Modify: `src/repo/prompts_vi.py`
- Modify: `src/repo/__init__.py`
- Modify: `src/repo/smoke_loader.py`

- [x] **Step 1: Replace `src/repo/prompts_vi.py` with vendored hierarchical prompts**

Implementation details:

- Copy exact text from `references_code/prompts.yaml` keys:
  - `system_prompt` -> `SYSTEM_PROMPT_VI`
  - `hierarchical_abstractive` -> `HIERARCHIC_ABSTRACTIVE_PROMPT_VI`
  - `hierarchical_title` -> `HIERARCHIC_TITLE_PROMPT_VI`
  - `ssdst_abstractive` -> `SSDST_ABSTRACTIVE_PROMPT_VI`
  - `ssdst_state_update` -> `SSDST_STATE_UPDATE_PROMPT_VI`
- Use triple-quoted strings and preserve placeholders exactly.
- Define enum:

```python
class LLMTask(str, Enum):
    """Hierarchical recap LLM tasks served by the Vietnamese backbone."""

    ABSTRACTIVE = "hierarchical_abstractive"
    TITLE = "hierarchical_title"
    SSDST_ABSTRACTIVE = "ssdst_abstractive"
    SSDST_STATE_UPDATE = "ssdst_state_update"
```

- Define mapping:

```python
def get_prompt(task: LLMTask) -> str:
    """Return the Vietnamese prompt template for a supported LLM task."""
    mapping = {
        LLMTask.ABSTRACTIVE: HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
        LLMTask.TITLE: HIERARCHIC_TITLE_PROMPT_VI,
        LLMTask.SSDST_ABSTRACTIVE: SSDST_ABSTRACTIVE_PROMPT_VI,
        LLMTask.SSDST_STATE_UPDATE: SSDST_STATE_UPDATE_PROMPT_VI,
    }
    return mapping[task]
```

- Do not include `HIGHLIGHTS_PROMPT_VI`.
- Do not include `HIERARCHIC_SEGMENT_PROMPT_VI` because segmentation is lexical Sliding TextTiling, not an LLM prompt task.

- [x] **Step 2: Update repo package exports**

In `src/repo/__init__.py`:

- Remove imports and `__all__` entries for `HIERARCHIC_SEGMENT_PROMPT_VI` and `HIGHLIGHTS_PROMPT_VI`.
- Add imports and `__all__` entries for `SYSTEM_PROMPT_VI`, `SSDST_ABSTRACTIVE_PROMPT_VI`, and `SSDST_STATE_UPDATE_PROMPT_VI`.
- Keep `HIERARCHIC_ABSTRACTIVE_PROMPT_VI`, `HIERARCHIC_TITLE_PROMPT_VI`, `LLMTask`, and `get_prompt`.

- [x] **Step 3: Update smoke loader prompt validation**

In `src/repo/smoke_loader.py`:

- Import `SYSTEM_PROMPT_VI` if prompt smoke validation should include the system prompt.
- Keep iterating over `for task in LLMTask` so the smoke check follows the updated enum automatically.
- Ensure no code references removed constants.

- [x] **Step 4: Run prompt test to verify implementation**

Run:

```bash
MODEL_LOAD_LLM=0 python3 -m unittest tests.unit.test_prompts_vi -v
```

Expected: PASS.

## Task 3: Docs And Full Verification

**Files:**
- Modify: `docs/QUALITY_SCORE.md`
- Modify: `docs/superpowers/plans/2026-07-05-prompt-registry-replacement.md`

- [x] **Step 1: Update quality document**

Append a benchmark/simplification row noting prompt registry replacement after tests pass. Use this exact row shape in the most relevant table:

```markdown
| 2026-07-05 | `prompt-registry-replacement` | 100% (`tests.unit.test_prompts_vi`, full discover if run) | 0 | 0 | Replaced prototype prompt registry with strict JSON-only hierarchical prompts from `references_code/prompts.yaml`; removed highlights and LLM segmentation from prompt task surface. | 2026-07-05 |
```

If full discover has not passed yet, write `targeted prompt tests green; full discover pending` instead of `full discover if run`.

- [x] **Step 2: Run full verification**

Run:

```bash
MODEL_LOAD_LLM=0 python3 -m unittest discover -v
```

Expected: PASS. If failures are unrelated to prompt registry changes, record the failing test names and do not fix unrelated dirty workspace changes.

- [x] **Step 3: Update this plan progress**

Check off completed steps and add a short progress note with the exact verification command and result.

## Self-Review

- Spec coverage: all requirements in `docs/superpowers/specs/2026-07-05-prompt-registry-replacement-design.md` map to Tasks 1-3.
- Placeholder scan: this plan contains no unfinished placeholder markers and no open-ended implementation gaps, and concrete commands for each verification step.
- Type consistency: public names match the proposed implementation and tests: `SYSTEM_PROMPT_VI`, `HIERARCHIC_ABSTRACTIVE_PROMPT_VI`, `HIERARCHIC_TITLE_PROMPT_VI`, `SSDST_ABSTRACTIVE_PROMPT_VI`, `SSDST_STATE_UPDATE_PROMPT_VI`, `LLMTask`, `get_prompt`.

## Progress Log

- 2026-07-05: Implemented vendored hierarchical prompt registry from `references_code/prompts.yaml`; removed highlights and LLM segmentation from `LLMTask`; updated repo exports, smoke validation, mock LLM responses, and summarization JSON parsing.
- 2026-07-05: Targeted verification passed: `MODEL_LOAD_LLM=0 python3 -m unittest tests.unit.test_prompts_vi -v` -> 7 tests OK.
- 2026-07-05: Full verification passed: `MODEL_LOAD_LLM=0 python3 -m unittest discover -v` -> Ran 252 tests in 61.692s, OK.
