"""Unit tests for the 4 Vietnamese prompt templates."""

import unittest

from src.repo.prompts_vi import (
    HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
    HIERARCHIC_SEGMENT_PROMPT_VI,
    HIERARCHIC_TITLE_PROMPT_VI,
    HIGHLIGHTS_PROMPT_VI,
    LLMTask,
    get_prompt,
)


class TestPromptsVi(unittest.TestCase):
    def test_all_four_prompts_present_and_non_empty(self) -> None:
        for name, text in [
            ("segment", HIERARCHIC_SEGMENT_PROMPT_VI),
            ("abstractive", HIERARCHIC_ABSTRACTIVE_PROMPT_VI),
            ("title", HIERARCHIC_TITLE_PROMPT_VI),
            ("highlights", HIGHLIGHTS_PROMPT_VI),
        ]:
            self.assertTrue(text.strip(), f"{name} prompt is empty")
            self.assertGreater(len(text), 50, f"{name} prompt too short")

    def test_llm_task_enum_has_four_members(self) -> None:
        self.assertEqual(
            {t.name for t in LLMTask},
            {"SEGMENT", "ABSTRACTIVE", "TITLE", "HIGHLIGHTS"},
        )

    def test_get_prompt_returns_correct_template(self) -> None:
        for task in LLMTask:
            self.assertIsInstance(get_prompt(task), str)

    def test_prompts_mention_vietnamese(self) -> None:
        for text in [
            HIERARCHIC_SEGMENT_PROMPT_VI,
            HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
            HIERARCHIC_TITLE_PROMPT_VI,
            HIGHLIGHTS_PROMPT_VI,
        ]:
            self.assertIn("tiếng Việt", text)


if __name__ == "__main__":
    unittest.main()
