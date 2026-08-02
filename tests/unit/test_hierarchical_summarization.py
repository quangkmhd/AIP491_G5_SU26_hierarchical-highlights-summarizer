import unittest

from src.service.hierarchical_summarization import HierarchicalSummarizationService
from src.types.segment import Chunk, SegmentResult
from src.types.utterance import Utterance


def utterance(index, text, speaker="S1"):
    return Utterance(index=index, speaker=speaker, text=text)


class RecordingSummarizer:
    def __init__(self, output="summary"):
        self.inputs = []
        self.output = output
    def summarize(self, text):
        self.inputs.append(text)
        return self.output


class RecordingTitler:
    def __init__(self, output="title"):
        self.inputs = []
        self.output = output
    def generate_title(self, text):
        self.inputs.append(text)
        return self.output


class HierarchicalSummarizationTests(unittest.TestCase):
    def setUp(self):
        self.summarizer = RecordingSummarizer()
        self.titler = RecordingTitler()
        self.service = HierarchicalSummarizationService(self.summarizer, self.titler)

    def test_summary_body_matches_training_format(self):
        chunk = Chunk(utterances=[utterance(0, "Xin chào", "Lan"), utterance(1, "Kế hoạch", "Minh")])
        self.assertEqual(self.service.abstractive(chunk), "summary")
        self.assertEqual(self.summarizer.inputs, ["- Lan: Xin chào\n- Minh: Kế hoạch"])

    def test_summary_is_not_arbitrarily_clipped(self):
        self.summarizer.output = "x" * 1000
        chunk = Chunk(utterances=[utterance(0, "Nội dung")])
        self.assertEqual(len(self.service.abstractive(chunk)), 1000)

    def test_title_uses_only_ordered_summaries(self):
        segment = SegmentResult(
            title="placeholder",
            chunks=[
                Chunk(utterances=[utterance(0, "RAW_SECRET")], rolling_summary="Tóm tắt một"),
                Chunk(utterances=[utterance(1, "RAW_OTHER")], rolling_summary="Tóm tắt hai"),
            ],
            utterances_start=0,
            utterances_end=1,
        )
        self.assertEqual(self.service.title(segment), "title")
        self.assertEqual(self.titler.inputs, ["Tóm tắt một / Tóm tắt hai"])
        self.assertNotIn("RAW_SECRET", self.titler.inputs[0])

    def test_title_skips_empty_summaries(self):
        segment = SegmentResult(
            title="placeholder",
            chunks=[
                Chunk(utterances=[utterance(0, "a")], rolling_summary=" "),
                Chunk(utterances=[utterance(1, "b")], rolling_summary="Có nội dung"),
            ], utterances_start=0, utterances_end=1,
        )
        self.service.title(segment)
        self.assertEqual(self.titler.inputs, ["Có nội dung"])

    def test_title_keeps_last_1500_characters(self):
        text = "A" * 1000 + "B" * 1000
        segment = SegmentResult(
            title="placeholder",
            chunks=[Chunk(utterances=[utterance(0, "raw")], rolling_summary=text)],
            utterances_start=0, utterances_end=0,
        )
        self.service.title(segment)
        self.assertEqual(self.titler.inputs[0], text[-1500:])

    def test_title_returns_empty_chapter_without_summaries(self):
        segment = SegmentResult(title="placeholder", chunks=[], utterances_start=0, utterances_end=0)
        self.assertEqual(self.service.title(segment), "Chương trống")
        self.assertEqual(self.titler.inputs, [])

    def test_abstractive_utterances_helper(self):
        self.service.abstractive_utterances([utterance(0, "nội dung")])
        self.assertEqual(self.summarizer.inputs, ["- S1: nội dung"])


if __name__ == "__main__":
    unittest.main()
