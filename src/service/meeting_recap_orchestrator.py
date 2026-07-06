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
from src.service.text_tiling import TextTilingService
from src.types.hierarchical_recap import HierarchicalRecap
from src.types.segment import Chunk, SegmentResult
from src.logging import (
    LoggableError,
    get_logger,
    log_error_with_fix,
)
from src.types.transcript import DialogueTranscript


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

        Phase 1 — real-time scoring: yields utterance-accepted and
        depth-score-updated events for every utterance after the first.

        Phase 2 — batch segmentation: runs TextTilingService.process()
        over all accumulated scores to detect topic boundaries using the
        paper-1 depth formula and adaptive tau = mu - sigma/2 cutoff.

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
        n = len(transcript.utterances)
        all_utterances = transcript.utterances
        all_scores: list[float] = []
        for idx, utt in enumerate(all_utterances):
            if idx == 0:
                pending_utts = [utt]
                continue

            yield OrchestratorEvent(
                type=RecapEventType.UTTERANCE_ACCEPTED,
                data={"index": utt.index, "speaker": utt.speaker, "text": utt.text},
            )

            prev = all_utterances[idx - 1]
            score = self.scorer.score_pair(prev.text, utt.text)
            all_scores.append(score)
            self.logger.info(
                "coherence pair=%d score=%.4f  utt[%d]=\"%s\" -> utt[%d]=\"%s\"",
                idx - 1, score,
                idx - 1, prev.text[:60],
                idx, utt.text[:60],
            )
            yield OrchestratorEvent(
                type=RecapEventType.DEPTH_SCORE_UPDATED,
                data={
                    "pair_index": idx - 1,
                    "score": score,
                },
            )

            pending_utts.append(utt)

        # Phase 2: Batch segmentation using TextTilingService
        if n < 2:
            bounds: list[int] = []
        else:
            seg_events = self.tiler.process(all_scores, n)
            bounds = [e.boundary_index for e in seg_events if e.boundary_index >= 0]

        # Build segment utterance ranges from boundaries
        seg_ranges: list[tuple[int, int]] = []
        seg_start = 0
        for b in bounds:
            seg_ranges.append((seg_start, b))
            seg_start = b + 1
        if seg_start <= n - 1:
            seg_ranges.append((seg_start, n - 1))

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

        # Phase 3: Build segments, emit events
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


