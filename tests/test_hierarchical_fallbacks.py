import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep

from app.methods.hierarchical_recap import (
    chunk_segment,
    has_complete_chunk_note_result,
    is_valid_title_result,
    parse_chunk_notes,
    parse_title_result,
)
from app.services.prompt_loader import PromptLoader
from app.services.transcript_parser import Utterance


def make_utterances(texts: list[str]) -> list[Utterance]:
    return [
        Utterance(
            index=index,
            speaker=f"Speaker {index}",
            start_time=f"00:{index:02d}",
            end_time=f"00:{index + 1:02d}",
            text=text,
        )
        for index, text in enumerate(texts, start=1)
    ]


class HierarchicalFallbackTests(unittest.TestCase):
    def test_empty_title_result_falls_back_to_segment_text(self) -> None:
        utterances = make_utterances(["Thống nhất kiến trúc summary gồm highlights và hierarchical."])
        runs = [{"parsed": {"title": "", "one_line_summary": ""}, "target": "local-model", "error": ""}]

        result = parse_title_result(runs, utterances)

        self.assertNotEqual(result["title"], "")
        self.assertNotIn("Lỗi tạo tiêu đề", result["title"])
        self.assertIn("summary", result["title"])
        self.assertNotEqual(result["one_line_summary"], "")

    def test_empty_chunk_note_result_falls_back_to_chunk_text(self) -> None:
        chunks = chunk_segment(make_utterances(["Cần viết test và report kết quả chạy demo."]))
        runs = [
            {
                "parsed": {
                    "notes": [
                        {
                            "chunk_id": chunks[0]["chunk_id"],
                            "summary": "",
                            "contains_key_point": False,
                            "contains_action_item": True,
                        }
                    ]
                },
                "target": "local-model",
                "error": "",
            }
        ]

        notes_by_chunk = parse_chunk_notes(runs, chunks)
        notes = notes_by_chunk[chunks[0]["chunk_id"]]

        self.assertEqual(len(notes), 1)
        self.assertNotEqual(notes[0]["summary"], "")
        self.assertIn("test", notes[0]["summary"])
        self.assertTrue(notes[0]["contains_action_item"])

    def test_empty_structural_outputs_are_accepted_for_local_fallback(self) -> None:
        chunks = chunk_segment(make_utterances(["Cần viết test và report kết quả chạy demo."]))

        self.assertTrue(is_valid_title_result({"title": "", "one_line_summary": ""}))
        self.assertTrue(
            has_complete_chunk_note_result(
                {
                    "notes": [
                        {
                            "chunk_id": chunks[0]["chunk_id"],
                            "summary": "",
                            "contains_key_point": False,
                            "contains_action_item": False,
                        }
                    ]
                },
                chunks,
            )
        )

    def test_prompts_use_none_instead_of_empty_text_fields(self) -> None:
        combined = "\n".join(
            [
                PromptLoader.get_prompt("system_prompt"),
                PromptLoader.get_prompt("highlights_abstractive"),
                PromptLoader.get_prompt("hierarchical_title"),
                PromptLoader.get_prompt("hierarchical_abstractive"),
            ]
        )

        self.assertIn('ghi đúng chuỗi "none"', combined)
        self.assertIn('dùng "none"', combined)
        self.assertIn('ghi "none"', combined)
        self.assertNotIn('dùng chuỗi rỗng ""', combined)
        self.assertNotIn('dùng ""', combined)
        self.assertNotIn('chuỗi rỗng. Nếu', combined)

    def test_prompt_loader_reloads_when_prompt_file_changes(self) -> None:
        previous_prompts = PromptLoader._prompts
        previous_path = PromptLoader._loaded_path
        previous_mtime = PromptLoader._loaded_mtime_ns
        try:
            with TemporaryDirectory() as directory:
                prompt_path = Path(directory) / "prompts.yaml"
                prompt_path.write_text("system_prompt: first\n", encoding="utf-8")
                PromptLoader._prompts = {}
                PromptLoader._loaded_path = None
                PromptLoader._loaded_mtime_ns = None

                self.assertEqual(PromptLoader.load_prompts(prompt_path)["system_prompt"], "first")

                sleep(0.01)
                prompt_path.write_text("system_prompt: second\n", encoding="utf-8")

                self.assertEqual(PromptLoader.load_prompts(prompt_path)["system_prompt"], "second")
        finally:
            PromptLoader._prompts = previous_prompts
            PromptLoader._loaded_path = previous_path
            PromptLoader._loaded_mtime_ns = previous_mtime


if __name__ == "__main__":
    unittest.main()
