"""Unit tests for TranscriptRepo (data/eval_vi JSON -> DialogueTranscript)."""

import unittest
from pathlib import Path

from src.repo.transcript_repo import TranscriptRepo, TranscriptRepoError

DATA_DIR = Path("data/eval_vi")
ALL_FILES = [
    "dialseg_711.json",
    "doc2dial.json",
    "meeting_ami.json",
    "meeting_committee.json",
    "meeting_icsi.json",
    "tiage.json",
]


class TestTranscriptRepoHappyPath(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TranscriptRepo()

    def test_loads_all_six_files(self) -> None:
        for name in ALL_FILES:
            with self.subTest(file=name):
                transcripts = self.repo.load_all(Path(DATA_DIR) / name)
                self.assertGreater(len(transcripts), 0)
                self.assertGreater(transcripts[0].utterance_count, 0)

    def test_utterance_indices_are_contiguous(self) -> None:
        transcripts = self.repo.load_all(Path(DATA_DIR) / "meeting_committee.json")
        for t in transcripts:
            indices = [u.index for u in t.utterances]
            self.assertEqual(indices, list(range(len(indices))))

    def test_speaker_synthesized_when_missing(self) -> None:
        transcripts = self.repo.load_all(Path(DATA_DIR) / "meeting_committee.json")
        t = transcripts[0]
        # eval_vi data has no speaker labels; we synthesize "S{i+1}".
        self.assertTrue(all(u.speaker.startswith("S") for u in t.utterances))

    def test_uses_vietnamese_text(self) -> None:
        transcripts = self.repo.load_all(Path(DATA_DIR) / "meeting_committee.json")
        t = transcripts[0]
        # The first utterances of the committee sample are in Vietnamese and long.
        self.assertGreater(len(t.utterances[0].text), 50)

    def test_meeting_title_includes_dial_id(self) -> None:
        transcripts = self.repo.load_all(Path(DATA_DIR) / "meeting_committee.json")
        t = transcripts[0]
        self.assertIsNotNone(t.meeting_title)
        self.assertIn("0", t.meeting_title)

    def test_get_one_by_dial_id(self) -> None:
        t = self.repo.get_by_dial_id(
            Path(DATA_DIR) / "meeting_committee.json", dial_id=0
        )
        self.assertEqual(t.utterances[0].index, 0)


class TestTranscriptRepoErrors(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TranscriptRepo()

    def test_missing_file_raises_typed_error(self) -> None:
        with self.assertRaises(TranscriptRepoError):
            self.repo.load_all(Path("does_not_exist.json"))

    def test_malformed_json_raises_typed_error(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fp:
            fp.write("{not valid json")
            bad_path = Path(fp.name)
        try:
            with self.assertRaises(TranscriptRepoError):
                self.repo.load_all(bad_path)
        finally:
            bad_path.unlink()

    def test_get_by_dial_id_not_found(self) -> None:
        with self.assertRaises(TranscriptRepoError):
            self.repo.get_by_dial_id(
                Path(DATA_DIR) / "meeting_committee.json", dial_id=99999
            )


if __name__ == "__main__":
    unittest.main()


class TestTranscriptRepoDropping(unittest.TestCase):
    def test_empty_utterances_dropped_indices_recorded(self) -> None:
        # meeting_ami.json dial_id=123 has 1 empty string in utterances_vi.
        repo = TranscriptRepo()
        t = repo.get_by_dial_id(
            Path(DATA_DIR) / "meeting_ami.json", dial_id=123
        )
        dropped = t.metadata.get("dropped_empty_indices", "")
        self.assertNotEqual(dropped, "", "expected at least one dropped index")
        self.assertEqual(t.utterances[0].index, 0)
        # Final indices must still be contiguous 0..N-1.
        self.assertEqual(
            [u.index for u in t.utterances],
            list(range(len(t.utterances))),
        )


class TestTranscriptRepoAnnotationHandling(unittest.TestCase):
    """C1: inline `{vocalsound}` / `{disfmarker}` annotations are stripped.

    Previously only fully-placeholder utterances were dropped, so a text like
    `"{vocalsound} Vâng, ạ."` was loaded verbatim and would be passed to the
    abstractive LLM, producing summaries that quote the disfluency markers.
    """

    def setUp(self) -> None:
        self.repo = TranscriptRepo()
        import tempfile
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.path = Path(self._tmpdir.name) / "inline.json"
        self.path.write_text(
            json.dumps(
                [
                    {
                        "dial_id": 99,
                        "utterances": [
                            "{vocalsound} Vâng, ạ.",
                            "{gap} Sếp.",
                            "Câu bình thường.",
                            "{disfmarker} Ý tôi là...",
                        ],
                        "segments": [4],
                        "set": "test",
                        "utterances_vi": [
                            "{vocalsound} Vâng, ạ.",
                            "{gap} Sếp.",
                            "Câu bình thường.",
                            "{disfmarker} Ý tôi là...",
                        ],
                        "utterances_en": [
                            "{vocalsound} Yes.",
                            "{gap} Boss.",
                            "A normal sentence.",
                            "{disfmarker} I mean...",
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )

    def test_inline_placeholders_stripped_from_text(self) -> None:
        transcripts = self.repo.load_all(self.path)
        t = transcripts[0]
        texts = [u.text for u in t.utterances]
        self.assertEqual(
            texts,
            ["Vâng, ạ.", "Sếp.", "Câu bình thường.", "Ý tôi là..."],
        )
        # No literal {vocalsound} or {disfmarker} survives.
        for u in t.utterances:
            self.assertNotIn("{vocalsound}", u.text)
            self.assertNotIn("{disfmarker}", u.text)
            self.assertNotIn("{gap}", u.text)

    def test_full_placeholder_utterances_still_dropped(self) -> None:
        # A record where the entire utterance is just the placeholder.
        self.path.write_text(
            json.dumps(
                [
                    {
                        "dial_id": 100,
                        "utterances_vi": ["{vocalsound}", "Câu thật.", "{vocalsound}"],
                        "segments": [3],
                        "set": "test",
                    }
                ]
            ),
            encoding="utf-8",
        )
        transcripts = self.repo.load_all(self.path)
        t = transcripts[0]
        self.assertEqual([u.text for u in t.utterances], ["Câu thật."])
        self.assertEqual(t.metadata["dropped_empty_indices"], "0,2")


class TestTranscriptRepoOriginalIndexSpeakerLabels(unittest.TestCase):
    """C2: speaker labels track the ORIGINAL index, not the post-filter one."""

    def test_speaker_labels_track_original_index_after_drop(self) -> None:
        import tempfile
        import json as _json
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "drop.json"
            p.write_text(
                _json.dumps(
                    [
                        {
                            "dial_id": 7,
                            "utterances_vi": ["", "câu một", "câu hai"],
                            "segments": [3],
                            "set": "test",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            t = TranscriptRepo().load_all(p)[0]
        # Even though we dropped the first utterance, the kept speakers still
        # reflect their ORIGINAL positions (S2 and S3), not post-filter S1/S2.
        self.assertEqual(
            [(u.index, u.speaker, u.text) for u in t.utterances],
            [(0, "S2", "câu một"), (1, "S3", "câu hai")],
        )


import json  # for the inner write_text above
