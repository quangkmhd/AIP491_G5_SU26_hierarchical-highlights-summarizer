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
            self.assertIn("Bạn", text)

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
        ]:
            self.assertIn(placeholder, HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        # The example chunk_id in the JSON schema is literal text, not a
        # .format() placeholder — see the double-brace escaping in the template.
        self.assertIn('"example_chunk_id"', HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
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
        ]:
            self.assertIn(placeholder, SSDST_ABSTRACTIVE_PROMPT_VI)
        # The example chunk_id in the JSON schema is literal text, not a
        # .format() placeholder.
        self.assertIn('"example_chunk_id"', SSDST_ABSTRACTIVE_PROMPT_VI)
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
