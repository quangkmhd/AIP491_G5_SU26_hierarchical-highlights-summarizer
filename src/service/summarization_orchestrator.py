from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterator
from uuid import uuid4

from src.service.hierarchical_summarization import HierarchicalSummarizationService
from src.service.multiscale_text_tiling import MultiscaleTextTilingService
from src.types.hierarchical_summary import HierarchicalSummary
from src.types.segment import Chunk, SegmentResult
from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance


class SummarizationEventType(str, Enum):
    """5 loại sự kiện chính trong luồng pipeline tóm tắt hội thoại."""

    UTTERANCE_ACCEPTED = "utterance-accepted"
    SEGMENT_CLOSED = "segment-closed"
    CHUNK_CLOSED = "chunk-closed"
    TITLE_EMITTED = "title-emitted"
    MEETING_COMPLETED = "meeting-completed"


class StreamingOrchestrator:
    """Bộ điều phối liên kết toàn bộ pipeline phân đoạn chủ đề và tóm tắt phân cấp."""

    CHUNK_SIZE: int = 8

    def __init__(
        self,
        tiler: MultiscaleTextTilingService | None = None,
        summarizer: HierarchicalSummarizationService | None = None,
        chunk_size: int = CHUNK_SIZE,
    ) -> None:
        """Khởi tạo các dịch vụ phân đoạn và tóm tắt."""
        self.tiler = tiler or MultiscaleTextTilingService()
        self.summarizer = summarizer or HierarchicalSummarizationService()
        self.chunk_size = chunk_size
        self._incremental_utterances: list[Utterance] = []
        self._incremental_segments: list[SegmentResult] = []
        self._incremental_meeting_id = uuid4()
        self._incremental_t0 = time.perf_counter()

    # --- 1. Xử lý toàn bộ cuộc họp (Batch Processing) ---

    def process_batch(
        self, transcript: DialogueTranscript
    ) -> HierarchicalSummary:
        """Xử lý toàn bộ bản ghi hội thoại dạng batch và trả về kết quả tóm tắt phân cấp."""
        t0 = time.perf_counter()
        all_utterances = transcript.utterances
        segments: list[SegmentResult] = []
        seg_ranges = self.tiler.process([u.text for u in all_utterances])
        list(self._build_segment_events(all_utterances, seg_ranges, segments))
        return HierarchicalSummary(
            meeting_id=uuid4(),
            meeting_title=transcript.meeting_title,
            segments=segments,
            generated_at=datetime.now(timezone.utc),
            processing_time_ms=int((time.perf_counter() - t0) * 1000),
        )

    # --- 2. Xử lý thời gian thực tăng tiến (Real-time Streaming) ---

    def accept_utterance(
        self, text: str, speaker: str = "Speaker 01", index: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Tiếp nhận một câu thoại real-time và đẩy vào pipeline phân đoạn/tóm tắt."""
        utt_idx = index if index is not None else len(self._incremental_utterances)
        utt = Utterance(speaker=speaker, text=text, index=utt_idx)
        self._incremental_utterances.append(utt)

        yield {
            "type": SummarizationEventType.UTTERANCE_ACCEPTED.value,
            "index": utt.index,
            "speaker": utt.speaker,
            "text": utt.text,
        }

        new_ranges = self.tiler.update(utt.text)
        if new_ranges:
            yield from self._build_segment_events(
                self._incremental_utterances, new_ranges, self._incremental_segments
            )

    def flush_and_finalize(self) -> Iterator[dict[str, Any]]:
        """Xả nốt các câu thoại cuối cùng và phát ra sự kiện hoàn thành cuộc họp."""
        if not self._incremental_utterances:
            return

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
        yield {
            "type": SummarizationEventType.MEETING_COMPLETED.value,
            "hierarchical_summary": summary.model_dump(mode="json"),
        }

    # --- 3. Hàm bổ trợ nội bộ (Internal Helper) ---

    def _build_segment_events(
        self,
        all_utterances: list[Utterance],
        seg_ranges: list[tuple[int, int]],
        segments_target: list[SegmentResult],
    ) -> Iterator[dict[str, Any]]:
        """Tóm tắt các khối thoại và phát các sự kiện CHUNK_CLOSED, SEGMENT_CLOSED, TITLE_EMITTED."""
        for start_utt, end_utt in seg_ranges:
            segment_utts = all_utterances[start_utt : end_utt + 1]
            seg = SegmentResult(utterances_start=start_utt, utterances_end=end_utt)

            for chunk_idx, i in enumerate(range(0, len(segment_utts), self.chunk_size)):
                chunk_utts = segment_utts[i : i + self.chunk_size]
                chunk = Chunk(utterances=chunk_utts)
                chunk.rolling_summary = self.summarizer.abstractive(chunk)
                seg.chunks.append(chunk)

                yield {
                    "type": SummarizationEventType.CHUNK_CLOSED.value,
                    "segment_id": str(seg.segment_id),
                    "chunk_id": str(chunk.chunk_id),
                    "chunk_index": chunk_idx,
                    "utterances_start": chunk_utts[0].index,
                    "utterances_end": chunk_utts[-1].index,
                    "rolling_summary": chunk.rolling_summary,
                }

            yield {
                "type": SummarizationEventType.SEGMENT_CLOSED.value,
                "segment_id": str(seg.segment_id),
                "utterances_start": seg.utterances_start,
                "utterances_end": seg.utterances_end,
            }

            seg.title = self.summarizer.title(seg)
            segments_target.append(seg)
            yield {
                "type": SummarizationEventType.TITLE_EMITTED.value,
                "segment_id": str(seg.segment_id),
                "title": seg.title,
            }
