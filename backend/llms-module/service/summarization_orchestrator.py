from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterator
from uuid import uuid4

from service.chunking_service import ChunkingService
from service.hierarchical_summarization import HierarchicalSummarizationService
from service.multiscale_text_tiling import MultiscaleTextTilingService
from schemas_dto.hierarchical_summary import HierarchicalSummary
from schemas_dto.segment import Chunk, SegmentResult
from schemas_dto.transcript import DialogueTranscript
from schemas_dto.utterance import Utterance


class SummarizationEventType(str, Enum):
    """5 main event types in the meeting summarization pipeline."""

    UTTERANCE_ACCEPTED = "utterance-accepted"
    SEGMENT_CLOSED = "segment-closed"
    CHUNK_CLOSED = "chunk-closed"
    TITLE_EMITTED = "title-emitted"
    MEETING_COMPLETED = "meeting-completed"


class OrchestratorEvent:
    """Container for event details in the summarization flow."""

    def __init__(self, type: str, data: dict[str, Any] | None = None) -> None:
        self.type = type
        self.data = data or {}


class StreamingOrchestrator:
    """Orchestrator linking topic segmentation and hierarchical summarization pipelines."""

    def __init__(
        self,
        tiler: MultiscaleTextTilingService | None = None,
        chunker: ChunkingService | None = None,
        summarizer: HierarchicalSummarizationService | None = None,
    ) -> None:
        """Initialize segmentation, chunking, and summarization services."""
        self.tiler = tiler or MultiscaleTextTilingService()
        self.chunker = chunker or ChunkingService()
        self.summarizer = summarizer or HierarchicalSummarizationService()

    def _build_segment_events(
        self,
        all_utterances: list[Utterance],
        seg_ranges: list[tuple[int, int]],
        segments_target: list[SegmentResult],
    ) -> Iterator[OrchestratorEvent]:
        """Summarize dialogue chunks and emit CHUNK_CLOSED, SEGMENT_CLOSED, and TITLE_EMITTED events."""
        for start_pos, end_pos in seg_ranges:
            seg_idx = len(segments_target)
            segment_utts = all_utterances[start_pos : end_pos + 1]
            if not segment_utts:
                continue

            seg = SegmentResult(
                title=f"Chapter {seg_idx + 1}",
                utterances_start=segment_utts[0].index,
                utterances_end=segment_utts[-1].index,
            )

            for chunk_idx, i in enumerate(range(0, len(segment_utts), self.chunker.CHUNK_SIZE)):
                chunk_utts = segment_utts[i : i + self.chunker.CHUNK_SIZE]
                chunk = Chunk(utterances=chunk_utts)
                chunk.rolling_summary = self.summarizer.abstractive(chunk)
                seg.chunks.append(chunk)

                yield OrchestratorEvent(
                    type=SummarizationEventType.CHUNK_CLOSED,
                    data={
                        "segment_id": str(seg.segment_id),
                        "chunk_id": str(chunk.chunk_id),
                        "chunk_index": chunk_idx,
                        "utterances_start": chunk_utts[0].index,
                        "utterances_end": chunk_utts[-1].index,
                        "rolling_summary": chunk.rolling_summary,
                    },
                )

            yield OrchestratorEvent(
                type=SummarizationEventType.SEGMENT_CLOSED,
                data={
                    "segment_id": str(seg.segment_id),
                    "utterances_start": seg.utterances_start,
                    "utterances_end": seg.utterances_end,
                },
            )

            title = self.summarizer.title(seg)
            seg.title = title
            segments_target.append(seg)
            yield OrchestratorEvent(
                type=SummarizationEventType.TITLE_EMITTED,
                data={"segment_id": str(seg.segment_id), "title": title},
            )

    def process_stream(
        self, transcript: DialogueTranscript
    ) -> Iterator[OrchestratorEvent]:
        """Process meeting transcript and emit events in a stream."""
        t0 = time.perf_counter()
        meeting_id = uuid4()
        if not transcript.utterances:
            raise ValueError("transcript has no utterances")

        all_utterances = transcript.utterances

        # 1. Emit utterance accepted events
        for utt in all_utterances[1:]:
            yield OrchestratorEvent(
                type=SummarizationEventType.UTTERANCE_ACCEPTED,
                data={"index": utt.index, "speaker": utt.speaker, "text": utt.text},
            )

        # 2. Segmentation and summarization
        segments: list[SegmentResult] = []
        seg_ranges = self.tiler.process([u.text for u in all_utterances])
        yield from self._build_segment_events(all_utterances, seg_ranges, segments)

        # 3. Finalize meeting and package results
        summary = HierarchicalSummary(
            meeting_id=meeting_id,
            segments=segments,
            generated_at=datetime.now(timezone.utc),
            processing_time_ms=int((time.perf_counter() - t0) * 1000),
        )
        yield OrchestratorEvent(
            type=SummarizationEventType.MEETING_COMPLETED,
            data={"hierarchical_summary": summary.model_dump(mode="json")},
        )

    def process_batch(
        self, transcript: DialogueTranscript
    ) -> HierarchicalSummary:
        """Process an entire meeting transcript in batch mode and return hierarchical summary results."""
        for event in self.process_stream(transcript):
            if event.type == SummarizationEventType.MEETING_COMPLETED:
                return HierarchicalSummary.model_validate(event.data["hierarchical_summary"])
        raise ValueError("Failed to process meeting batch")

    # --- Incremental / real-time streaming processing interface ---

    def reset_incremental(self) -> None:
        """Reset incremental processing state for a new streaming session."""
        self._incremental_utterances: list[Utterance] = []
        self._incremental_segments: list[SegmentResult] = []
        self._incremental_meeting_id = uuid4()
        self._incremental_t0 = time.perf_counter()
        self._incremental_finalized = False
        self.tiler.reset()

    def accept_utterance(
        self, text: str, speaker: str, index: int,
    ) -> Iterator[OrchestratorEvent]:
        """Accept a real-time utterance and push into segmentation/summarization pipeline."""
        if not hasattr(self, "_incremental_utterances"):
            self.reset_incremental()

        utt = Utterance(speaker=speaker, text=text, index=index)
        self._incremental_utterances.append(utt)

        yield OrchestratorEvent(
            type=SummarizationEventType.UTTERANCE_ACCEPTED,
            data={"index": utt.index, "speaker": utt.speaker, "text": utt.text},
        )

        new_ranges = self.tiler.update(utt.text)
        if new_ranges:
            yield from self._build_segment_events(
                self._incremental_utterances, new_ranges, self._incremental_segments
            )

    def flush_and_finalize(self) -> Iterator[OrchestratorEvent]:
        """Flush remaining utterances and emit meeting completed event."""
        if not hasattr(self, "_incremental_utterances") or not self._incremental_utterances:
            return
        if self._incremental_finalized:
            return
        self._incremental_finalized = True

        tail_ranges = self.tiler.flush()
        if tail_ranges:
            yield from self._build_segment_events(
                self._incremental_utterances, tail_ranges, self._incremental_segments
            )

        summary = HierarchicalSummary(
            meeting_id=self._incremental_meeting_id,
            segments=self._incremental_segments,
            generated_at=datetime.now(timezone.utc),
            processing_time_ms=int((time.perf_counter() - self._incremental_t0) * 1000),
        )
        yield OrchestratorEvent(
            type=SummarizationEventType.MEETING_COMPLETED,
            data={"hierarchical_summary": summary.model_dump(mode="json")},
        )
