"""StreamingOrchestrator -- end-to-end meeting recap with 6 event types.

Wires CoherenceScorer + TextTilingService + ChunkingService +
HierarchicalSummarizationService into a single async generator that yields
incremental state events as the pipeline produces them.

Event types (per spec D5):
  - utterance-accepted: every new utterance after the first
  - depth-score-updated: new pair score from CoherenceScorer
  - segment-closed: TextTiling boundary crossed
  - chunk-closed: chunk filled (8 utt) or segment closed; rolling_summary is synchronous
  - title-emitted: segment closed; hierarchical_title returned (deferred at MVP via mock)
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
from uuid import UUID, uuid4

from src.config.text_tiling import TextTilingConfig
from src.service.chunking_service import ChunkingService
from src.service.coherence_scorer import CoherenceScorer
from src.service.hierarchical_summarization import HierarchicalSummarizationService
from src.service.text_tiling import SegmentEvent, TextTilingService
from src.types.hierarchical_recap import HierarchicalRecap, MeetingStatus
from src.types.segment import Chunk, SegmentResult
from src.logging import (
    LoggableError,
    get_logger,
    log_error_with_fix,
    request_context,
)
from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance


class RecapEventType(str, Enum):
    """The 6 canonical recap event types from spec D5."""

    UTTERANCE_ACCEPTED = "utterance-accepted"
    DEPTH_SCORE_UPDATED = "depth-score-updated"
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
        scorer: CoherenceScorer | None = None,
        tiler: TextTilingService | None = None,
        chunker: ChunkingService | None = None,
        summarizer: HierarchicalSummarizationService | None = None,
    ) -> None:
        self.logger = get_logger("src.service.orchestrator")
        self.scorer = scorer or CoherenceScorer()
        self.tiler = tiler or TextTilingService(TextTilingConfig())
        self.chunker = chunker or ChunkingService()
        self.summarizer = summarizer or HierarchicalSummarizationService()

    def process_stream(
        self, transcript: DialogueTranscript
    ) -> Iterator[OrchestratorEvent]:
        """Process a transcript; yield events as the pipeline produces them.

        On the first utterance, emits a depth-score-updated event for the
        first pair as soon as it is scored. Emits segment-closed when the
        TextTiling cutoff is crossed, then chunk-closed + title-emitted
        for each chunk and the segment title. Emits meeting-completed at
        the end with the final HierarchicalRecap.
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
        current_segment: SegmentResult | None = None
        pending_utts: list[Utterance] = []
        scores_buffer: list[float] = []
        chunk_counter = 0
        segment_counter = 0

        try:
            yield from self._process_stream_body(
                transcript, t0, meeting_id, segments, current_segment,
                pending_utts, scores_buffer, chunk_counter, segment_counter,
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
        self, transcript, t0, meeting_id, segments, current_segment,
        pending_utts, scores_buffer, chunk_counter, segment_counter,
    ):
        n = len(transcript.utterances)
        for idx, utt in enumerate(transcript.utterances):
            if idx == 0:
                # First utterance -- start the first segment
                current_segment = self._new_segment(segment_counter, idx, utt)
                segment_counter += 1
                pending_utts = [utt]
                continue

            # Emit utterance-accepted for subsequent utterances
            yield OrchestratorEvent(
                type=RecapEventType.UTTERANCE_ACCEPTED,
                data={"index": utt.index, "speaker": utt.speaker, "text": utt.text},
            )

            # Score the pair (prev, curr)
            prev = transcript.utterances[idx - 1]
            score = self.scorer.score_pair(prev.text, utt.text)
            scores_buffer.append(score)
            yield OrchestratorEvent(
                type=RecapEventType.DEPTH_SCORE_UPDATED,
                data={
                    "pair_index": idx - 1,
                    "score": score,
                    "pair": [prev.text, utt.text],
                },
            )

            # Add to current segment
            pending_utts.append(utt)
            if current_segment is not None:
                current_segment.utterances_end = utt.index

            # Check TextTiling: if the latest score crosses the cutoff, close
            # the segment. We run TextTiling on the full score buffer each
            # time; this is simple and correct, though a streaming variant
            # could optimize by maintaining a sliding window.
            boundary = self._detect_boundary(scores_buffer)
            if boundary is not None and boundary > 0:
                # `boundary` is the index of the utterance that starts the
                # next segment. Close the current segment at the utterance
                # immediately before it.
                current_segment.utterances_end = pending_utts[boundary - 1].index

                # Close chunks in current_segment up to (but not including) boundary.
                for chunk in self._flush_chunks_up_to(current_segment, pending_utts, boundary):
                    yield OrchestratorEvent(
                        type=RecapEventType.CHUNK_CLOSED,
                        data={
                            "chunk_id": str(chunk.chunk_id),
                            "segment_id": str(current_segment.segment_id),
                            "utterances_start": chunk.utterances[0].index,
                            "utterances_end": chunk.utterances[-1].index,
                            "rolling_summary": chunk.rolling_summary,
                        },
                    )
                # Emit segment-closed
                yield OrchestratorEvent(
                    type=RecapEventType.SEGMENT_CLOSED,
                    data={
                        "segment_id": str(current_segment.segment_id),
                        "utterances_start": current_segment.utterances_start,
                        "utterances_end": current_segment.utterances_end,
                    },
                )
                # Generate title (deferred semantically; here it's a quick mock call)
                title = self.summarizer.title(current_segment)
                current_segment.title = title
                segments.append(current_segment)
                yield OrchestratorEvent(
                    type=RecapEventType.TITLE_EMITTED,
                    data={"segment_id": str(current_segment.segment_id), "title": title},
                )
                # Start a new segment from the boundary
                current_segment = self._new_segment(
                    segment_counter, boundary, transcript.utterances[boundary]
                )
                segment_counter += 1
                pending_utts = pending_utts[boundary:]
                scores_buffer = []  # reset for new segment

        # After loop: close the trailing segment
        if current_segment is not None and pending_utts:
            # Flush remaining chunks
            for i in range(0, len(pending_utts), self.chunker.CHUNK_SIZE):
                chunk_utts = pending_utts[i : i + self.chunker.CHUNK_SIZE]
                if not chunk_utts:
                    continue
                chunk = Chunk(utterances=chunk_utts)
                chunk.rolling_summary = self.summarizer.abstractive(chunk)
                current_segment.chunks.append(chunk)
                yield OrchestratorEvent(
                    type=RecapEventType.CHUNK_CLOSED,
                    data={
                        "chunk_id": str(chunk.chunk_id),
                        "segment_id": str(current_segment.segment_id),
                        "utterances_start": chunk_utts[0].index,
                        "utterances_end": chunk_utts[-1].index,
                        "rolling_summary": chunk.rolling_summary,
                    },
                )
            # Emit final segment-closed
            yield OrchestratorEvent(
                type=RecapEventType.SEGMENT_CLOSED,
                data={
                    "segment_id": str(current_segment.segment_id),
                    "utterances_start": current_segment.utterances_start,
                    "utterances_end": current_segment.utterances_end,
                },
            )
            title = self.summarizer.title(current_segment)
            current_segment.title = title
            segments.append(current_segment)
            yield OrchestratorEvent(
                type=RecapEventType.TITLE_EMITTED,
                data={"segment_id": str(current_segment.segment_id), "title": title},
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

    def _new_segment(
        self, counter: int, start_idx: int, first_utt: Utterance
    ) -> SegmentResult:
        return SegmentResult(
            title=f"Chapter {counter + 1}",  # placeholder; filled when the segment closes
            chunks=[],
            utterances_start=first_utt.index,
            utterances_end=first_utt.index,
        )

    def _detect_boundary(self, scores: list[float]) -> int | None:
        """Return the boundary index (1-based position to close) if any.

        For a simple streaming implementation: if the latest score's depth
        is high enough to indicate a topic shift, return the index of the
        new segment's start. Uses TextTilingService's depth formula.
        """
        if len(scores) < 1:
            return None
        # Compute depth for the last score using paper-1 formula
        from src.service.text_tiling import depth_computing
        depths = depth_computing(scores)
        last_depth = float(depths[-1])
        # Use a simple threshold: depth > 0.3 indicates a shift
        # (TextTilingService's full threshold isn't used here because
        # we want a streaming decision per-pair, not a batch decision)
        if last_depth > 0.3:
            return len(scores)  # boundary at the next position
        return None

    def _flush_chunks_up_to(
        self,
        segment: SegmentResult,
        pending_utts: list[Utterance],
        boundary: int,
    ) -> list[Chunk]:
        """Flush complete chunks up to (but not including) boundary index."""
        flushed: list[Chunk] = []
        for i in range(0, boundary, self.chunker.CHUNK_SIZE):
            chunk_utts = pending_utts[i : i + self.chunker.CHUNK_SIZE]
            if not chunk_utts:
                continue
            chunk = Chunk(utterances=chunk_utts)
            chunk.rolling_summary = self.summarizer.abstractive(chunk)
            segment.chunks.append(chunk)
            flushed.append(chunk)
        return flushed
