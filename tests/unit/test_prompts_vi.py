import unittest

from src.repo.prompts_vi import SUMMARY_PREFIX_VI, TITLE_PREFIX_VI


class PromptPrefixTests(unittest.TestCase):
    def test_prefixes_match_fine_tuning(self):
        self.assertEqual(SUMMARY_PREFIX_VI, "Tóm tắt: ")
        self.assertEqual(TITLE_PREFIX_VI, "Tạo tiêu đề: ")

    def test_prefixes_have_no_legacy_instructions(self):
        text = SUMMARY_PREFIX_VI + TITLE_PREFIX_VI
        self.assertNotIn("JSON", text)
        self.assertNotIn("\n", text)
        self.assertNotIn("chapter", text.lower())


if __name__ == "__main__":
    unittest.main()
