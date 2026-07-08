"""Unit tests for the unified dataset builder.

Tests parsing functions for MultiWOZ, KVRET, Taskmaster, CamRest676, Schema, CCPE, e2e_challenge, metalwoz, and frames.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.unified_dataset_builder import (
    parse_multiwoz,
    parse_kvret,
    parse_taskmaster,
    parse_camrest,
    parse_schema,
    parse_ccpe,
    parse_e2e_challenge,
    parse_metalwoz,
    parse_frames,
)


class UnifiedDatasetBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_parse_multiwoz(self) -> None:
        mock_data = {
            "SNG0123.json": {
                "goal": {
                    "hotel": {
                        "info": {"internet": "yes"}
                    }
                },
                "log": [
                    {"text": "I want a cheap hotel."},
                    {"text": "Sure, I found one."}
                ]
            }
        }
        file_path = os.path.join(self.temp_dir.name, "multiwoz.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        dialogues = parse_multiwoz(file_path)
        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0]["dataset_source"], "multiwoz")
        self.assertEqual(dialogues[0]["topic_title"], "hotel")
        self.assertEqual(len(dialogues[0]["utterances"]), 2)

    def test_parse_kvret(self) -> None:
        mock_data = [
            {
                "scenario": {
                    "uuid": "uuid_123",
                    "kb": {"kb_title": "weather"}
                },
                "dialogue": [
                    {"turn": "driver", "data": {"utterance": "What is the weather?"}},
                    {"turn": "assistant", "data": {"utterance": "It is rainy."}}
                ]
            }
        ]
        file_path = os.path.join(self.temp_dir.name, "kvret_train.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        dialogues = parse_kvret(self.temp_dir.name)
        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0]["dataset_source"], "kvret")
        self.assertEqual(dialogues[0]["topic_title"], "weather")

    def test_parse_taskmaster(self) -> None:
        mock_data = [
            {
                "conversation_id": "tm_123",
                "instruction_id": "restaurant_reservation",
                "utterances": [
                    {"speaker": "user", "text": "Book a table"},
                    {"speaker": "assistant", "text": "Sure"}
                ]
            }
        ]
        file_path = os.path.join(self.temp_dir.name, "tm_data.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        dialogues = parse_taskmaster(self.temp_dir.name)
        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0]["dataset_source"], "taskmaster")

    def test_parse_camrest(self) -> None:
        mock_data = [
            {
                "dial": [
                    {
                        "usr": {"transcript": "I need a restaurant."},
                        "sys": {"sent": "Okay."}
                    }
                ]
            }
        ]
        file_path = os.path.join(self.temp_dir.name, "camrest.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        dialogues = parse_camrest(file_path)
        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0]["dataset_source"], "camrest")

    def test_parse_schema(self) -> None:
        mock_data = [
            {
                "dialogue_id": "sch_123",
                "services": ["Restaurants_1"],
                "turns": [
                    {"speaker": "USER", "utterance": "Find food"},
                    {"speaker": "SYSTEM", "utterance": "Yes"}
                ]
            }
        ]
        file_path = os.path.join(self.temp_dir.name, "dialogues_001.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        dialogues = parse_schema(self.temp_dir.name)
        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0]["dataset_source"], "schema")

    def test_parse_ccpe(self) -> None:
        mock_data = [
            {
                "conversationId": "ccpe_123",
                "utterances": [
                    {"speaker": "USER", "text": "I like movies."},
                    {"speaker": "ASSISTANT", "text": "What type?"}
                ]
            }
        ]
        file_path = os.path.join(self.temp_dir.name, "ccpe.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        dialogues = parse_ccpe(file_path)
        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0]["dataset_source"], "ccpe")
        self.assertEqual(dialogues[0]["topic_title"], "movie_recommendation")

    def test_parse_e2e_challenge(self) -> None:
        # Mock dữ liệu TSV cho e2e challenge
        tsv_content = "session.ID\tMessage.From\tMessage.Text\n1\tuser\tBook taxi\n1\tagent\tOkay\n"
        file_path = os.path.join(self.temp_dir.name, "taxi_all.tsv")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(tsv_content)

        dialogues = parse_e2e_challenge(self.temp_dir.name)
        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0]["dataset_source"], "e2e_challenge")
        self.assertEqual(dialogues[0]["topic_title"], "taxi_booking")

    def test_parse_metalwoz(self) -> None:
        # Mock dữ liệu JSONL cho metalwoz
        jsonl_content = '{"id": "mw_123", "domain": "ALARM_SET", "turns": ["Hello", "Set alarm"]}\n'
        file_path = os.path.join(self.temp_dir.name, "alarm.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(jsonl_content)

        dialogues = parse_metalwoz(self.temp_dir.name)
        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0]["dataset_source"], "metalwoz")
        self.assertEqual(dialogues[0]["topic_title"], "alarm_set")

    def test_parse_frames(self) -> None:
        # Mock dữ liệu frames.json
        mock_data = [
            {
                "id": "fr_123",
                "turns": [
                    {"author": "user", "text": "Book travel"},
                    {"author": "wizard", "text": "Where to?"}
                ]
            }
        ]
        file_path = os.path.join(self.temp_dir.name, "frames.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        dialogues = parse_frames(file_path)
        self.assertEqual(len(dialogues), 1)
        self.assertEqual(dialogues[0]["dataset_source"], "frames")
        self.assertEqual(dialogues[0]["topic_title"], "travel_booking")


if __name__ == "__main__":
    unittest.main()
