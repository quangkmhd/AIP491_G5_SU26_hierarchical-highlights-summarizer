"""Unit tests for Vietnamese prompt templates."""

import unittest

from src.repo.prompts_vi import (
    HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
    HIERARCHIC_TITLE_PROMPT_VI,
    LLMTask,
    SYSTEM_PROMPT_VI,
    get_prompt,
)


class TestPromptsVi(unittest.TestCase):
    def test_public_prompts_present_and_non_empty(self) -> None:
        for name, text in [
            ("system", SYSTEM_PROMPT_VI),
            ("hierarchical_abstractive", HIERARCHIC_ABSTRACTIVE_PROMPT_VI),
            ("hierarchical_title", HIERARCHIC_TITLE_PROMPT_VI),
        ]:
            self.assertTrue(text.strip(), f"{name} prompt is empty")
            self.assertGreater(len(text), 200, f"{name} prompt too short")
            self.assertIn("Bạn", text)

    def test_llm_task_enum_is_hierarchical_only(self) -> None:
        self.assertEqual(
            {task.name for task in LLMTask},
            {"ABSTRACTIVE", "TITLE"},
        )
        self.assertNotIn("HIGHLIGHTS", {task.name for task in LLMTask})
        self.assertNotIn("SEGMENT", {task.name for task in LLMTask})

    def test_get_prompt_returns_correct_template(self) -> None:
        self.assertIs(get_prompt(LLMTask.ABSTRACTIVE), HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        self.assertIs(get_prompt(LLMTask.TITLE), HIERARCHIC_TITLE_PROMPT_VI)

    def test_system_prompt(self) -> None:
        self.assertIn("Không bịa", SYSTEM_PROMPT_VI)
        self.assertIn("tiếng Việt", SYSTEM_PROMPT_VI)

    def test_hierarchical_title_placeholders(self) -> None:
        self.assertIn("{segment_utterances}", HIERARCHIC_TITLE_PROMPT_VI)
        self.assertIn("Trả về hai dòng", HIERARCHIC_TITLE_PROMPT_VI)

    def test_hierarchical_abstractive_placeholders(self) -> None:
        self.assertIn("{prompt_chunks}", HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        self.assertNotIn("contains_key_point", HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        self.assertNotIn("contains_action_item", HIERARCHIC_ABSTRACTIVE_PROMPT_VI)
        self.assertNotIn("chunk_id", HIERARCHIC_ABSTRACTIVE_PROMPT_VI)


if __name__ == "__main__":
    unittest.main()
