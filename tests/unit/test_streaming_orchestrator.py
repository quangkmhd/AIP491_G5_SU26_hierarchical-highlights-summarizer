"""Unit tests for StreamingOrchestrator (svc-006+streaming).

Tests use a tiny synthetic transcript (8 utterances, 1 clear boundary) so
the pipeline can run quickly on CPU with MockLLMBackbone.

The orchestrator uses lexical Sliding TextTiling for segmentation;
it requires no external scoring model.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Force MockLLMBackbone so the suite stays offline (no real GGUF download).
os.environ.setdefault("MODEL_LOAD_LLM", "0")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.service import (
    ChunkingService,
    HierarchicalSummarizationService,
    RecapEventType,
    SlidingTextTilingService,
    StreamingOrchestrator,
)
from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance


def _t(texts: list[str]) -> DialogueTranscript:
    return DialogueTranscript(
        utterances=[Utterance(speaker="S1", text=t, index=i) for i, t in enumerate(texts)],
    )


class StreamingOrchestratorEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.orchestrator = StreamingOrchestrator()

    def test_event_order_for_tiny_transcript(self) -> None:
        # 6 utterances, one likely topic shift at index 2
        transcript = _t([
            "Chào buổi sáng.",
            "Hôm nay chúng ta thảo luận về dự án X.",
            "Dự án X tiến triển tốt.",  # possibly same topic
            "Chuyển sang chủ đề mới: ngân sách.",  # topic shift
            "Ngân sách quý này là 500 triệu.",
            "Đồng ý phân bổ cho team A.",
        ])
        events = list(self.orchestrator.process_stream(transcript))
        # Last event is always MEETING_COMPLETED
        self.assertEqual(events[-1].type, RecapEventType.MEETING_COMPLETED)
        # At least one SEGMENT_CLOSED
        seg_events = [e for e in events if e.type == RecapEventType.SEGMENT_CLOSED]
        self.assertGreaterEqual(len(seg_events), 1)
        # At least one TITLE_EMITTED
        title_events = [e for e in events if e.type == RecapEventType.TITLE_EMITTED]
        self.assertEqual(len(title_events), len(seg_events))

    def test_process_batch_returns_hierarchical_recap(self) -> None:
        transcript = _t([
            "Xin chào.",
            "Chúng ta bắt đầu họp.",
            "Mục tiêu hôm nay là thống nhất kế hoạch.",
        ])
        recap = self.orchestrator.process_batch(transcript)
        self.assertIsNotNone(recap.meeting_id)
        self.assertGreaterEqual(len(recap.segments), 1)
        # Each segment has a non-empty title
        for seg in recap.segments:
            self.assertGreater(len(seg.title), 0)
        # processing_time_ms is recorded
        self.assertIsNotNone(recap.processing_time_ms)
        self.assertGreaterEqual(recap.processing_time_ms, 0)

    def test_processing_time_under_3_minutes(self) -> None:
        transcript = _t(["a", "b", "c", "d", "e", "f", "g", "h"])
        recap = self.orchestrator.process_batch(transcript)
        self.assertLessEqual(recap.processing_time_ms, 180_000)

    def test_no_highlights_keys(self) -> None:
        transcript = _t(["x", "y", "z"])
        recap = self.orchestrator.process_batch(transcript)
        dumped = recap.model_dump(mode="json")
        self.assertNotIn("highlights_notes", dumped)
        self.assertNotIn("highlights_tasks", dumped)

    def test_segments_have_chunks(self) -> None:
        # 16 utterances, likely 1+ segments, each with chunks
        texts = [f"câu {i}" for i in range(16)]
        transcript = _t(texts)
        recap = self.orchestrator.process_batch(transcript)
        self.assertGreater(len(recap.segments), 0)
        for seg in recap.segments:
            # 16 utt, 1 segment -> 2 chunks (8+8)
            self.assertGreater(len(seg.chunks), 0)
            for chunk in seg.chunks:
                self.assertLessEqual(len(chunk.utterances), ChunkingService.CHUNK_SIZE)

    def test_streaming_emits_utterance_accepted(self) -> None:
        # For 4+ utterances, we should get at least 3 UTTERANCE_ACCEPTED events
        # (the first utterance is the segment start, not "accepted")
        transcript = _t(["a", "b", "c", "d", "e"])
        events = list(self.orchestrator.process_stream(transcript))
        utt_events = [e for e in events if e.type == RecapEventType.UTTERANCE_ACCEPTED]
        self.assertEqual(len(utt_events), 4)  # 5 utt - 1 first

    def test_no_depth_score_updated_events(self) -> None:
        # DEPTH_SCORE_UPDATED was dropped from the event type enum;
        # verify the enum no longer has that member.
        transcript = _t(["a", "b", "c", "d"])
        events = list(self.orchestrator.process_stream(transcript))
        self.assertFalse(hasattr(RecapEventType, "DEPTH_SCORE_UPDATED"))
        # No event should carry a type that does not exist in the enum
        for e in events:
            self.assertIsInstance(e.type, RecapEventType)

    def test_chunk_closed_events_present(self) -> None:
        # 10 utterances, likely 1 segment, 2 chunks
        transcript = _t([f"u{i}" for i in range(10)])
        events = list(self.orchestrator.process_stream(transcript))
        chunk_events = [e for e in events if e.type == RecapEventType.CHUNK_CLOSED]
        self.assertGreaterEqual(len(chunk_events), 1)

    def test_batch_equals_streaming_final_recap(self) -> None:
        # process_batch and process_stream should produce equivalent recaps
        transcript = _t(["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"])
        recap_batch = self.orchestrator.process_batch(transcript)
        events = list(self.orchestrator.process_stream(transcript))
        final = [e for e in events if e.type == RecapEventType.MEETING_COMPLETED][0]
        recap_stream = final.data["hierarchical_recap"]
        # Compare structure (not generated_at / processing_time_ms)
        self.assertEqual(len(recap_batch.segments), len(recap_stream["segments"]))
        for a, b in zip(recap_batch.segments, recap_stream["segments"]):
            self.assertEqual(a.utterances_start, b["utterances_start"])
            self.assertEqual(a.utterances_end, b["utterances_end"])

    def test_segments_do_not_overlap(self) -> None:
        """Segments must cover contiguous, non-overlapping utterance ranges.

        Regression test for overlapping segment bug.
        """
        texts = [f"utt_{i}" for i in range(24)]
        transcript = _t(texts)
        recap = self.orchestrator.process_batch(transcript)
        ranges = [(s.utterances_start, s.utterances_end) for s in recap.segments]
        for i in range(1, len(ranges)):
            prev_end = ranges[i - 1][1]
            curr_start = ranges[i][0]
            self.assertGreaterEqual(
                curr_start, prev_end + 1,
                f"segments overlap: {ranges[i - 1]} -> {ranges[i]}",
            )
        if ranges:
            self.assertEqual(ranges[0][0], 0)
            self.assertEqual(ranges[-1][1], len(texts) - 1)
        covered = set()
        for s, e in ranges:
            for idx in range(s, e + 1):
                self.assertNotIn(
                    idx, covered,
                    f"utterance {idx} appears in more than one segment",
                )
                covered.add(idx)
        self.assertEqual(len(covered), len(texts))

    def test_segments_non_overlapping_with_real_data(self) -> None:
        """Real dial_id=0 transcript: segments must not overlap.

        Regression test for the overlapping-segment bug that triggered
        the rewrite of the boundary handling in the orchestrator.
        """
        import json
        p = ROOT / "data" / "eval_vi" / "dialseg_711.json"
        with open(p) as f:
            data = json.load(f)
        # Find dial_id=0
        item = None
        for d in data:
            if d.get("dial_id") == 0:
                item = d
                break
        self.assertIsNotNone(item, "dial_id=0 not found")
        texts = item["utterances_vi"]
        self.assertGreater(len(texts), 0)
        transcript = _t(texts)
        recap = self.orchestrator.process_batch(transcript)
        ranges = [(s.utterances_start, s.utterances_end) for s in recap.segments]
        for i in range(1, len(ranges)):
            prev_end = ranges[i - 1][1]
            curr_start = ranges[i][0]
            self.assertGreaterEqual(
                curr_start, prev_end + 1,
                f"segments overlap: {ranges[i - 1]} -> {ranges[i]}",
            )
        if ranges:
            self.assertEqual(ranges[0][0], 0)
            self.assertEqual(ranges[-1][1], len(texts) - 1)
        covered = set()
        for s, e in ranges:
            for idx in range(s, e + 1):
                self.assertNotIn(
                    idx, covered,
                    f"utterance {idx} appears in more than one segment",
                )
                covered.add(idx)
        self.assertEqual(len(covered), len(texts))

    def test_custom_tiler_pluggable(self) -> None:
        """Caller can pass a SlidingTextTilingService directly via the
        orchestrator's `tiler` constructor arg."""
        from src.config.text_tiling import SlidingTextTilingConfig
        cfg = SlidingTextTilingConfig(radii=[3, 5], alpha=0.5, min_segment_ratio=0.1)
        tiler = SlidingTextTilingService(cfg)
        orch = StreamingOrchestrator(tiler=tiler)
        transcript = _t([f"chủ đề {i}" for i in range(10)])
        recap = orch.process_batch(transcript)
        self.assertGreaterEqual(len(recap.segments), 1)