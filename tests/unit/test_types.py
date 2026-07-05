"""Unit tests for the Types layer (model-001).

Exercises every Pydantic model end-to-end, including a real sample from
`data/eval_vi/meeting_committee.json` to keep the scope tight to a single
Vietnamese committee meeting (the first dialogue in the file).
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError

from src.types import (
    BaseSchema,
    Chunk,
    DialogueTranscript,
    HierarchicalRecap,
    MeetingProcessResponse,
    MeetingStatus,
    SegmentResult,
    TranscriptIngestionRequest,
    Utterance,
)

DATA_FILE = ROOT / "data" / "eval_vi" / "meeting_committee.json"
CHUNK_SIZE = Chunk.MAX_CHUNK_SIZE


def _load_first_dialogue() -> dict:
    with DATA_FILE.open("r", encoding="utf-8") as f:
        dialogues = json.load(f)
    assert dialogues, "expected at least one dialogue in eval_vi data"
    return dialogues[0]


def _chunked(utterances: list[Utterance], size: int) -> list[Chunk]:
    return [Chunk(utterances=utterances[i : i + size]) for i in range(0, len(utterances), size)]


class BaseSchemaTests(unittest.TestCase):
    def test_extra_field_rejected_everywhere(self) -> None:
        # Sanity check: BaseSchema actually enforces extra="forbid".
        with self.assertRaises(ValidationError):
            Utterance(speaker="A", text="x", index=0, surprise="nope")  # type: ignore[call-arg]


class UtteranceTests(unittest.TestCase):
    def test_minimal_construction(self) -> None:
        u = Utterance(speaker="A", text="hello", index=0)
        self.assertEqual(u.speaker, "A")
        self.assertEqual(u.text, "hello")
        self.assertEqual(u.index, 0)
        self.assertIsInstance(u.utterance_id, UUID)
        self.assertIsNone(u.timestamp)

    def test_frozen(self) -> None:
        u = Utterance(speaker="A", text="x", index=0)
        with self.assertRaises(ValidationError):
            u.text = "y"  # type: ignore[misc]

    def test_validation_requires_speaker(self) -> None:
        with self.assertRaises(ValidationError):
            Utterance(speaker="", text="x", index=0)

    def test_validation_requires_text(self) -> None:
        with self.assertRaises(ValidationError):
            Utterance(speaker="A", text="", index=0)

    def test_validation_rejects_negative_index(self) -> None:
        with self.assertRaises(ValidationError):
            Utterance(speaker="A", text="x", index=-1)

    def test_optional_timestamp(self) -> None:
        ts = datetime(2026, 7, 4, 9, 0, tzinfo=timezone.utc)
        u = Utterance(speaker="A", text="x", index=0, timestamp=ts)
        self.assertEqual(u.timestamp, ts)


class DialogueTranscriptTests(unittest.TestCase):
    def _make_utterances(self, n: int) -> list[Utterance]:
        return [Utterance(speaker=f"S{i % 3}", text=f"u{i}", index=i) for i in range(n)]

    def test_builds_from_utterances(self) -> None:
        utterances = self._make_utterances(3)
        t = DialogueTranscript(utterances=utterances, meeting_title="Demo")
        self.assertEqual(t.utterance_count, 3)
        self.assertEqual(t.meeting_title, "Demo")
        self.assertIsInstance(t.transcript_id, UUID)
        self.assertIsInstance(t.submitted_at, datetime)

    def test_indices_must_be_contiguous(self) -> None:
        utterances = self._make_utterances(3)
        # Utterance is frozen, so we need a fresh one with a bad index.
        utterances[1] = utterances[1].model_copy(update={"index": 99})
        with self.assertRaises(ValidationError):
            DialogueTranscript(utterances=utterances)

    def test_utterance_pairs_yield_consecutive(self) -> None:
        utterances = self._make_utterances(4)
        t = DialogueTranscript(utterances=utterances)
        pairs = list(t.utterance_pairs)
        self.assertEqual(len(pairs), 3)
        self.assertEqual([a.text for a, _ in pairs], ["u0", "u1", "u2"])
        self.assertEqual([b.text for _, b in pairs], ["u1", "u2", "u3"])

    def test_rejects_empty_utterance_list(self) -> None:
        with self.assertRaises(ValidationError):
            DialogueTranscript(utterances=[])

    def test_max_utterances_is_class_constant(self) -> None:
        self.assertEqual(DialogueTranscript.MAX_UTTERANCES, 5000)

    def test_rejects_oversized_transcript(self) -> None:
        # MAX_UTTERANCES + 1 utterances must raise.
        utterances = [Utterance(speaker="S", text="x", index=i) for i in range(DialogueTranscript.MAX_UTTERANCES + 1)]
        with self.assertRaises(ValidationError) as ctx:
            DialogueTranscript(utterances=utterances)
        self.assertIn("MAX_UTTERANCES", str(ctx.exception))


class ChunkTests(unittest.TestCase):
    def _make_utterances(self, n: int) -> list[Utterance]:
        return [Utterance(speaker="S", text=f"u{i}", index=i) for i in range(n)]

    def test_accepts_max_chunk_size(self) -> None:
        chunk = Chunk(utterances=self._make_utterances(CHUNK_SIZE))
        self.assertEqual(len(chunk.utterances), CHUNK_SIZE)

    def test_rejects_chunk_too_large(self) -> None:
        with self.assertRaises(ValidationError):
            Chunk(utterances=self._make_utterances(CHUNK_SIZE + 1))

    def test_rejects_empty_chunk(self) -> None:
        with self.assertRaises(ValidationError):
            Chunk(utterances=[])

    def test_rolling_summary_optional(self) -> None:
        chunk = Chunk(utterances=self._make_utterances(2), rolling_summary="A summary.")
        self.assertEqual(chunk.rolling_summary, "A summary.")

    def test_max_chunk_size_is_class_constant(self) -> None:
        self.assertEqual(Chunk.MAX_CHUNK_SIZE, 8)


class SegmentResultTests(unittest.TestCase):
    def _chunks(self, n: int) -> list[Chunk]:
        out = []
        i = 0
        for _ in range(n):
            utterances = [Utterance(speaker="S", text=f"u{j}", index=i + j) for j in range(2)]
            out.append(Chunk(utterances=utterances))
            i += 2
        return out

    def test_display_title_prefers_override(self) -> None:
        seg = SegmentResult(
            title="Auto title",
            chunks=self._chunks(1),
            utterances_start=0,
            utterances_end=1,
            user_title_override="User title",
        )
        self.assertEqual(seg.display_title, "User title")

    def test_display_title_falls_back_to_auto(self) -> None:
        seg = SegmentResult(
            title="Auto title",
            chunks=self._chunks(1),
            utterances_start=0,
            utterances_end=1,
        )
        self.assertEqual(seg.display_title, "Auto title")

    def test_utterance_count_and_chunk_count(self) -> None:
        seg = SegmentResult(
            title="t",
            chunks=self._chunks(3),
            utterances_start=0,
            utterances_end=5,
        )
        self.assertEqual(seg.utterance_count, 6)
        self.assertEqual(seg.chunk_count, 3)

    def test_no_duplicate_uuid_field(self) -> None:
        # segment_id is the single source of truth.
        self.assertIn("segment_id", SegmentResult.model_fields)
        self.assertNotIn("segment_uuid", SegmentResult.model_fields)


class HierarchicalRecapTests(unittest.TestCase):
    def test_empty_recap(self) -> None:
        r = HierarchicalRecap()
        self.assertEqual(r.segment_count, 0)
        self.assertEqual(r.total_chunks, 0)
        self.assertIsInstance(r.meeting_id, UUID)
        # Highlights (notes/tasks) were removed in model-001+ (D1).
        dumped = r.model_dump(mode="json")
        self.assertNotIn("highlights_notes", dumped)
        self.assertNotIn("highlights_tasks", dumped)

    def test_aggregates_segments(self) -> None:
        seg = SegmentResult(
            title="t",
            chunks=[
                Chunk(utterances=[Utterance(speaker="A", text="x", index=0)]),
                Chunk(utterances=[Utterance(speaker="B", text="y", index=1)]),
            ],
            utterances_start=0,
            utterances_end=1,
        )
        recap = HierarchicalRecap(segments=[seg])
        self.assertEqual(recap.segment_count, 1)
        self.assertEqual(recap.total_chunks, 2)

    def test_model_dump_contains_no_highlights_keys(self) -> None:
        """After model-001+ (D1), the recap carries no highlights_* fields."""
        recap = HierarchicalRecap()
        dumped = recap.model_dump(mode="json")
        self.assertNotIn("highlights_notes", dumped)
        self.assertNotIn("highlights_tasks", dumped)
        expected_keys = {
            "meeting_id", "meeting_title", "segments",
            "generated_at", "processing_time_ms",
        }
        self.assertEqual(set(dumped.keys()), expected_keys)


class ApiSchemaTests(unittest.TestCase):
    def test_request_materializes_from_flat(self) -> None:
        req = TranscriptIngestionRequest(
            meeting_title="Cuộc họp Ủy ban",
            flat_texts=["Xin chào", "Cảm ơn"],
            language="vi",
        )
        t = req.materialize()
        self.assertEqual(t.utterance_count, 2)
        self.assertEqual(t.meeting_title, "Cuộc họp Ủy ban")
        self.assertEqual(t.metadata["language"], "vi")
        self.assertEqual(t.utterances[0].speaker, "S1")
        self.assertEqual(t.utterances[0].index, 0)
        self.assertEqual(t.utterances[1].index, 1)

    def test_request_materializes_from_utterances(self) -> None:
        utterances = [Utterance(speaker="A", text="x", index=0)]
        req = TranscriptIngestionRequest(utterances=utterances)
        t = req.materialize()
        self.assertEqual(t.utterance_count, 1)
        self.assertEqual(t.utterances[0].speaker, "A")

    def test_request_rejects_both_payloads(self) -> None:
        # Both payloads is now caught by the model_validator on the request,
        # so it raises ValidationError before .materialize() is even called.
        with self.assertRaises(ValidationError) as ctx:
            TranscriptIngestionRequest(
                flat_texts=["x"],
                utterances=[Utterance(speaker="A", text="y", index=0)],
            )
        self.assertIn("not both", str(ctx.exception))


    def test_meeting_process_response(self) -> None:
        resp = MeetingProcessResponse(
            meeting_id="abc",
            status=MeetingStatus.COMPLETED,
        )
        self.assertEqual(resp.status, MeetingStatus.COMPLETED)
        self.assertIsNone(resp.recap)
        self.assertIsNone(resp.error)

    def test_request_rejects_empty_payload(self) -> None:
        # No utterances, no flat_texts -> ValidationError at request level.
        with self.assertRaises(ValidationError) as ctx:
            TranscriptIngestionRequest(meeting_title="empty")
        self.assertIn("at least one", str(ctx.exception))

    def test_request_rejects_both_payloads_via_validator(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            TranscriptIngestionRequest(
                flat_texts=["x"],
                utterances=[Utterance(speaker="A", text="y", index=0)],
            )
        self.assertIn("not both", str(ctx.exception))

    def test_materialize_rejects_oversized_flat_texts(self) -> None:
        # flat_texts itself is just a list[str] (no max_length on the schema
        # field), so the limit is enforced inside materialize().
        oversized = [f"utt {i}" for i in range(DialogueTranscript.MAX_UTTERANCES + 1)]
        req = TranscriptIngestionRequest(flat_texts=oversized)
        with self.assertRaises(ValueError) as ctx:
            req.materialize()
        self.assertIn("MAX_UTTERANCES", str(ctx.exception))


class MeetingCommitteeSampleTests(unittest.TestCase):
    """Smoke test: load the FIRST dialogue from the Vietnamese committee data."""

    def test_loads_and_wraps_in_transcript(self) -> None:
        sample = _load_first_dialogue()
        self.assertEqual(sample["dial_id"], 0)
        self.assertEqual(len(sample["utterances_vi"]), 370)

        req = TranscriptIngestionRequest(
            meeting_title=f"Committee Meeting {sample['dial_id']}",
            flat_texts=sample["utterances_vi"],
            language="vi",
        )
        transcript = req.materialize()
        self.assertEqual(transcript.utterance_count, 370)
        self.assertEqual(transcript.metadata["language"], "vi")

        # Speakers are auto-assigned "S1..SN"; indices are 0..N-1.
        self.assertEqual(transcript.utterances[0].speaker, "S1")
        self.assertEqual(transcript.utterances[-1].index, 369)

    def test_segments_layout_matches_data(self) -> None:
        sample = _load_first_dialogue()
        # segments are lengths; convert to (start, end) inclusive ranges.
        seg_lengths = sample["segments"]
        self.assertEqual(sum(seg_lengths), len(sample["utterances_vi"]))

        # Build chunks per segment respecting the <=8 utterance limit.
        cursor = 0
        chunks_per_segment: list[list[Chunk]] = []
        for length in seg_lengths:
            seg_utts = [
                Utterance(speaker=f"S{j + 1}", text=t, index=cursor + j)
                for j, t in enumerate(sample["utterances_vi"][cursor : cursor + length])
            ]
            chunks_per_segment.append(_chunked(seg_utts, CHUNK_SIZE))
            cursor += length
        self.assertEqual(
            sum(len(c.utterances) for cs in chunks_per_segment for c in cs),
            370,
        )

        # Build a SegmentResult per length so we can round-trip into HierarchicalRecap.
        cursor = 0
        segments: list[SegmentResult] = []
        for i, length in enumerate(seg_lengths):
            start, end = cursor, cursor + length - 1
            segments.append(
                SegmentResult(
                    title=f"Chapter {i + 1}",
                    chunks=chunks_per_segment[i],
                    utterances_start=start,
                    utterances_end=end,
                )
            )
            cursor += length

        recap = HierarchicalRecap(
            segments=segments,
            meeting_title=f"Committee Meeting {sample['dial_id']}",
        )
        self.assertEqual(recap.segment_count, len(seg_lengths))
        self.assertEqual(
            recap.total_chunks,
            sum(len(cs) for cs in chunks_per_segment),
        )
        # Highlights (notes/tasks) were removed in model-001+ (D1).
        # The recap carries only segments and lifecycle metadata.
        self.assertNotIn("highlights_notes", recap.model_dump(mode="json"))
        self.assertNotIn("highlights_tasks", recap.model_dump(mode="json"))

        # Round-trip via JSON
        as_json = recap.model_dump_json()
        restored = HierarchicalRecap.model_validate_json(as_json)
        self.assertEqual(restored.segment_count, recap.segment_count)
        self.assertEqual(
            len(restored.segments[0].chunks[0].utterances),
            len(chunks_per_segment[0][0].utterances),
        )


if __name__ == "__main__":
    unittest.main()
