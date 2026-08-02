"""StreamingOrchestrator -- end-to-end meeting recap with 5 event types.

Wires SlidingTextTilingService + ChunkingService +
HierarchicalSummarizationService into a single async generator that yields
incremental state events as the pipeline produces them.

The segmentation layer is standalone lexical Sliding TextTiling
(multi-scale BoW + cosine + depth); it requires no external scoring model.

Event types (per spec D5, revised):
  - utterance-accepted: every new utterance after the first
  - segment-closed: Sliding TextTiling boundary crossed
  - chunk-closed: chunk filled (8 utt) or segment closed; rolling_summary is synchronous
  - title-emitted: segment closed; title generated from all completed chunk summaries
  - meeting-completed: transcript exhausted; final HierarchicalRecap attached

Both process_stream (async generator) and process_batch (one-shot returning
the final HierarchicalRecap) are exposed. The batch path is implemented in
terms of the stream: collect all events, return the final recap.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterator
from uuid import uuid4

from src.config.text_tiling import SlidingTextTilingConfig
from src.service.chunking_service import ChunkingService
from src.service.hierarchical_summarization import HierarchicalSummarizationService
from src.service.sliding_text_tiling import SlidingTextTilingService
from src.types.hierarchical_recap import HierarchicalRecap
from src.types.segment import Chunk, SegmentResult
from src.logging import (
    LoggableError,
    get_logger,
    log_error_with_fix,
)
from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance


class RecapEventType(str, Enum):
    """The 5 canonical recap event types from spec D5 (revised)."""

    UTTERANCE_ACCEPTED = "utterance-accepted"
    SEGMENT_CLOSED = "segment-closed"
    CHUNK_CLOSED = "chunk-closed"
    TITLE_EMITTED = "title-emitted"
    MEETING_COMPLETED = "meeting-completed"


@dataclass
class OrchestratorEvent:
    """A single event in the recap stream."""

    type: RecapEventType
    data: dict[str, Any] = field(default_factory=dict)


class StreamingOrchestrator:
    """Wires the segmentation + summarization pipeline into a single stream.

    The orchestrator owns the meeting_id lifecycle and the per-segment
    accumulation of chunks. It emits events in the documented order; the
    final event is always MEETING_COMPLETED carrying the full
    HierarchicalRecap.
    """

    def __init__(
        self,
        tiler: SlidingTextTilingService | None = None,
        chunker: ChunkingService | None = None,
        summarizer: HierarchicalSummarizationService | None = None,
    ) -> None:
        self.logger = get_logger("src.service.orchestrator")
        self.tiler = tiler or SlidingTextTilingService(SlidingTextTilingConfig())
        self.chunker = chunker or ChunkingService()
        self.summarizer = summarizer or HierarchicalSummarizationService()

    def process_stream(
        self, transcript: DialogueTranscript
    ) -> Iterator[OrchestratorEvent]:
        """Process a transcript; yield events as the pipeline produces them.

        Phase 1 — utterance intake: yields utterance-accepted events for
        every utterance after the first.

        Phase 2 — batch segmentation: runs SlidingTextTilingService.process()
        directly on the utterance texts to detect topic boundaries using
        multi-scale depth scoring and adaptive thresholding.

        Phase 3 — segment assembly: yields chunk-closed, segment-closed,
        and title-emitted for each detected segment. Yields meeting-completed
        at the end with the final HierarchicalRecap.
        """
        t0 = time.perf_counter()
        meeting_id = uuid4()
        n = len(transcript.utterances)
        if n == 0:
            self.logger.warning("process_stream called with empty transcript")
            raise LoggableError(
                "transcript has no utterances",
                fix="provide a TranscriptIngestionRequest with non-empty `utterances` or `flat_texts`",
            )
        self.logger.info(
            "orchestrator start n_utterances=%d meeting_id=%s",
            n, str(meeting_id),
        )
        segments: list[SegmentResult] = []

        try:
            yield from self._process_stream_body(
                transcript, t0, meeting_id, segments,
            )
        except LoggableError:
            raise
        except Exception as e:  # noqa: BLE001
            log_error_with_fix(
                self.logger, e,
                fix="check the traceback; common causes: invalid utterance "
                    "structure, model OOM, or input out of bounds",
            )
            raise

    def _process_stream_body(  # type: ignore[no-untyped-def]
        self, transcript, t0, meeting_id, segments,
    ):
        all_utterances = transcript.utterances

        # Phase 1: Utterance intake — emit utterance-accepted for every
        # utterance after the first (the first is the anchor).
        for idx, utt in enumerate(all_utterances[1:], start=1):
            yield OrchestratorEvent(
                type=RecapEventType.UTTERANCE_ACCEPTED,
                data={"index": utt.index, "speaker": utt.speaker, "text": utt.text},
            )

        # Phase 2: Batch segmentation using SlidingTextTilingService.
        # The service takes raw utterance texts (not pre-computed scores).
        utterance_texts = [u.text for u in all_utterances]
        seg_events = self.tiler.process(utterance_texts)

        # Build segment utterance ranges from boundaries.
        seg_ranges = [(e.utterances_start, e.utterances_end) for e in seg_events]

        self.logger.info(
            "segmentation complete n_segments=%d ranges=%s",
            len(seg_ranges), seg_ranges,
        )
        for i, (s, e) in enumerate(seg_ranges):
            utt_texts = [all_utterances[j].text[:50] for j in range(s, e + 1)]
            self.logger.info(
                "  segment %d: utt[%d..%d] (%d utts) %s",
                i + 1, s, e, e - s + 1, utt_texts,
            )

        # Phase 3: Build segments, emit events.
        for seg_idx, (start_utt, end_utt) in enumerate(seg_ranges):
            segment_utts = all_utterances[start_utt:end_utt + 1]
            seg = SegmentResult(
                title=f"Chapter {seg_idx + 1}",
                utterances_start=start_utt,
                utterances_end=end_utt,
            )

            for i in range(0, len(segment_utts), self.chunker.CHUNK_SIZE):
                chunk_utts = segment_utts[i:i + self.chunker.CHUNK_SIZE]
                chunk = Chunk(utterances=chunk_utts)
                chunk.rolling_summary = self.summarizer.abstractive(
                    chunk, chapter_number=seg_idx + 1, chunk_index=i // self.chunker.CHUNK_SIZE,
                )
                seg.chunks.append(chunk)
                self.logger.info(
                    "  chunk seg=%d utt[%d..%d] summary=\"%s\"",
                    seg_idx + 1,
                    chunk_utts[0].index, chunk_utts[-1].index,
                    chunk.rolling_summary,
                )
                yield OrchestratorEvent(
                    type=RecapEventType.CHUNK_CLOSED,
                    data={
                        "chunk_id": str(chunk.chunk_id),
                        "segment_id": str(seg.segment_id),
                        "utterances_start": chunk_utts[0].index,
                        "utterances_end": chunk_utts[-1].index,
                        "rolling_summary": chunk.rolling_summary,
                    },
                )

            yield OrchestratorEvent(
                type=RecapEventType.SEGMENT_CLOSED,
                data={
                    "segment_id": str(seg.segment_id),
                    "utterances_start": seg.utterances_start,
                    "utterances_end": seg.utterances_end,
                },
            )

            title = self.summarizer.title(seg, chapter_number=seg_idx + 1)
            seg.title = title
            segments.append(seg)
            self.logger.info(
                "  title seg=%d title=\"%s\"",
                seg_idx + 1, title,
            )
            yield OrchestratorEvent(
                type=RecapEventType.TITLE_EMITTED,
                data={"segment_id": str(seg.segment_id), "title": title},
            )

        processing_time_ms = int((time.perf_counter() - t0) * 1000)
        self.logger.info(
            "orchestrator done n_segments=%d n_chunks=%d processing_time_ms=%d",
            len(segments), sum(len(s.chunks) for s in segments), processing_time_ms,
        )
        recap = HierarchicalRecap(
            meeting_id=meeting_id,
            segments=segments,
            generated_at=datetime.now(timezone.utc),
            processing_time_ms=processing_time_ms,
        )
        yield OrchestratorEvent(
            type=RecapEventType.MEETING_COMPLETED,
            data={"hierarchical_recap": recap.model_dump(mode="json")},
        )

    def process_batch(
        self, transcript: DialogueTranscript
    ) -> HierarchicalRecap:
        """Process a transcript; return the final HierarchicalRecap."""
        recap_dict: dict[str, Any] = {}
        for event in self.process_stream(transcript):
            if event.type == RecapEventType.MEETING_COMPLETED:
                recap_dict = event.data["hierarchical_recap"]
        return HierarchicalRecap.model_validate(recap_dict)

    # --- Streaming / incremental interface ---

    def reset_incremental(self) -> None:
        """Reset internal state for a new incremental streaming session."""
        self._incremental_utterances: list[Utterance] = []
        self._incremental_segments: list[SegmentResult] = []
        self._incremental_meeting_id = uuid4()
        self._incremental_t0 = time.perf_counter()
        self._last_processed_count = 0
        self.tiler.reset()

    def accept_utterance(
        self, text: str, speaker: str, index: int,
    ) -> Iterator[OrchestratorEvent]:
        """Accept a single utterance from realtime ASR output.

        Feeds the utterance into SlidingTextTilingService (Code B streaming mode).
        Yields OrchestratorEvents whenever new boundaries are committed.
        """
        if not hasattr(self, "_incremental_utterances"):
            self.reset_incremental()

        utt = Utterance(speaker=speaker, text=text, index=index)
        self._incremental_utterances.append(utt)

        yield OrchestratorEvent(
            type=RecapEventType.UTTERANCE_ACCEPTED,
            data={"index": utt.index, "speaker": utt.speaker, "text": utt.text},
        )

        new_events = self.tiler.update(utt.text)
        if new_events:
            yield from self._process_streaming_segment_events(new_events)

    def _process_streaming_segment_events(
        self, seg_events: list[SegmentEvent],
    ) -> Iterator[OrchestratorEvent]:
        """Process newly committed SegmentEvents into chunks, abstractive summaries, and titles."""
        all_utterances = self._incremental_utterances

        for e in seg_events:
            seg_idx = len(self._incremental_segments)
            start_utt, end_utt = e.utterances_start, e.utterances_end

            segment_utts = [u for u in all_utterances if start_utt <= u.index <= end_utt]
            if not segment_utts:
                segment_utts = all_utterances[start_utt : end_utt + 1]

            seg = SegmentResult(
                title=f"Chapter {seg_idx + 1}",
                utterances_start=start_utt,
                utterances_end=end_utt,
            )

            for i in range(0, len(segment_utts), self.chunker.CHUNK_SIZE):
                chunk_utts = segment_utts[i : i + self.chunker.CHUNK_SIZE]
                chunk = Chunk(utterances=chunk_utts)
                chunk.rolling_summary = self.summarizer.abstractive(
                    chunk, chapter_number=seg_idx + 1, chunk_index=i // self.chunker.CHUNK_SIZE,
                )
                seg.chunks.append(chunk)
                yield OrchestratorEvent(
                    type=RecapEventType.CHUNK_CLOSED,
                    data={
                        "chunk_id": str(chunk.chunk_id),
                        "segment_id": str(seg.segment_id),
                        "utterances_start": chunk_utts[0].index,
                        "utterances_end": chunk_utts[-1].index,
                        "rolling_summary": chunk.rolling_summary,
                    },
                )

            yield OrchestratorEvent(
                type=RecapEventType.SEGMENT_CLOSED,
                data={
                    "segment_id": str(seg.segment_id),
                    "utterances_start": seg.utterances_start,
                    "utterances_end": seg.utterances_end,
                },
            )

            title = self.summarizer.title(seg, chapter_number=seg_idx + 1)
            seg.title = title
            self._incremental_segments.append(seg)
            yield OrchestratorEvent(
                type=RecapEventType.TITLE_EMITTED,
                data={"segment_id": str(seg.segment_id), "title": title},
            )

    def flush_and_finalize(self) -> Iterator[OrchestratorEvent]:
        """Process remaining utterances and emit meeting-completed."""
        if not hasattr(self, "_incremental_utterances"):
            return

        all_utterances = self._incremental_utterances
        if not all_utterances:
            return

        tail_events = self.tiler.flush()
        if tail_events:
            yield from self._process_streaming_segment_events(tail_events)

        processing_time_ms = int((time.perf_counter() - self._incremental_t0) * 1000)
        recap = HierarchicalRecap(
            meeting_id=self._incremental_meeting_id,
            segments=self._incremental_segments,
            generated_at=datetime.now(timezone.utc),
            processing_time_ms=processing_time_ms,
        )
        yield OrchestratorEvent(
            type=RecapEventType.MEETING_COMPLETED,
            data={"hierarchical_recap": recap.model_dump(mode="json")},
        )
