from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterator
from uuid import uuid4

from src.service.chunking_service import ChunkingService
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


class OrchestratorEvent:
    """Đối tượng chứa thông tin sự kiện trong luồng tóm tắt."""

    def __init__(self, type: str, data: dict[str, Any] | None = None) -> None:
        self.type = type
        self.data = data if data is not None else {}


class StreamingOrchestrator:
    """Bộ điều phối liên kết toàn bộ pipeline phân đoạn chủ đề và tóm tắt phân cấp."""

    def __init__(
        self,
        tiler: MultiscaleTextTilingService | None = None,
        chunker: ChunkingService | None = None,
        summarizer: HierarchicalSummarizationService | None = None,
    ) -> None:
        """Khởi tạo các dịch vụ phân đoạn, chia khối và tóm tắt."""
        self.tiler = tiler or MultiscaleTextTilingService()
        self.chunker = chunker or ChunkingService()
        self.summarizer = summarizer or HierarchicalSummarizationService()

    def process_stream(
        self, transcript: DialogueTranscript
    ) -> Iterator[OrchestratorEvent]:
        """Xử lý bản ghi hội thoại và phát ra các sự kiện theo luồng."""
        t0 = time.perf_counter()
        meeting_id = uuid4()
        n = len(transcript.utterances)
        if n == 0:
            raise ValueError("transcript has no utterances")
        segments: list[SegmentResult] = []

        all_utterances = transcript.utterances

        # 1. Phát sự kiện tiếp nhận câu thoại
        for idx, utt in enumerate(all_utterances[1:], start=1):
            yield OrchestratorEvent(
                type=SummarizationEventType.UTTERANCE_ACCEPTED,
                data={"index": utt.index, "speaker": utt.speaker, "text": utt.text},
            )

        # 2. Phân đoạn chủ đề TextTiling
        utterance_texts = [u.text for u in all_utterances]
        seg_ranges = self.tiler.process(utterance_texts)

        # 3. Tóm tắt từng khối và sinh tiêu đề từng phân đoạn
        for seg_idx, (start_utt, end_utt) in enumerate(seg_ranges):
            segment_utts = all_utterances[start_utt : end_utt + 1]
            seg = SegmentResult(
                title=f"Chapter {seg_idx + 1}",
                utterances_start=start_utt,
                utterances_end=end_utt,
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
            segments.append(seg)
            yield OrchestratorEvent(
                type=SummarizationEventType.TITLE_EMITTED,
                data={"segment_id": str(seg.segment_id), "title": title},
            )

        # 4. Hoàn tất cuộc họp và đóng gói kết quả
        processing_time_ms = int((time.perf_counter() - t0) * 1000)
        summary = HierarchicalSummary(
            meeting_id=meeting_id,
            segments=segments,
            generated_at=datetime.now(timezone.utc),
            processing_time_ms=processing_time_ms,
        )
        yield OrchestratorEvent(
            type=SummarizationEventType.MEETING_COMPLETED,
            data={"hierarchical_summary": summary.model_dump(mode="json")},
        )

    def process_batch(
        self, transcript: DialogueTranscript
    ) -> HierarchicalSummary:
        """Xử lý toàn bộ bản ghi hội thoại dạng batch và trả về kết quả tóm tắt phân cấp."""
        summary_dict: dict[str, Any] = {}
        for event in self.process_stream(transcript):
            if event.type == SummarizationEventType.MEETING_COMPLETED:
                summary_dict = event.data["hierarchical_summary"]
        return HierarchicalSummary.model_validate(summary_dict)

    # --- Giao diện xử lý tăng tiến / streaming real-time ---

    def reset_incremental(self) -> None:
        """Đặt lại trạng thái xử lý tăng tiến cho một phiên làm việc streaming mới."""
        self._incremental_utterances: list[Utterance] = []
        self._incremental_segments: list[SegmentResult] = []
        self._incremental_meeting_id = uuid4()
        self._incremental_t0 = time.perf_counter()
        self.tiler.reset()

    def accept_utterance(
        self, text: str, speaker: str, index: int,
    ) -> Iterator[OrchestratorEvent]:
        """Tiếp nhận một câu thoại real-time và đẩy vào pipeline phân đoạn/tóm tắt."""
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
            yield from self._process_streaming_segment_events(new_ranges)

    def _process_streaming_segment_events(
        self, seg_ranges: list[tuple[int, int]],
    ) -> Iterator[OrchestratorEvent]:
        """Xử lý các phạm vi phân đoạn trong streaming để tạo khối, tóm tắt và sinh tiêu đề."""
        all_utterances = self._incremental_utterances

        for start_utt, end_utt in seg_ranges:
            seg_idx = len(self._incremental_segments)

            segment_utts = [u for u in all_utterances if start_utt <= u.index <= end_utt]
            if not segment_utts:
                segment_utts = all_utterances[start_utt : end_utt + 1]

            seg = SegmentResult(
                title=f"Chapter {seg_idx + 1}",
                utterances_start=start_utt,
                utterances_end=end_utt,
            )

            for chunk_idx, i in enumerate(range(0, len(segment_utts), self.chunker.CHUNK_SIZE)):
                chunk_utts = segment_utts[i : i + self.chunker.CHUNK_SIZE]
                chunk = Chunk(utterances=chunk_utts)
                chunk.rolling_summary = self.summarizer.abstractive(chunk)
                seg.chunks.append(chunk)

                yield OrchestratorEvent(
                    type=SummarizationEventType.CHUNK_CLOSED,
                    data={
                        "chunk_id": str(chunk.chunk_id),
                        "segment_id": str(seg.segment_id),
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
            self._incremental_segments.append(seg)
            yield OrchestratorEvent(
                type=SummarizationEventType.TITLE_EMITTED,
                data={"segment_id": str(seg.segment_id), "title": title},
            )

    def flush_and_finalize(self) -> Iterator[OrchestratorEvent]:
        """Xả nốt các câu thoại cuối cùng và phát ra sự kiện hoàn thành cuộc họp."""
        if not hasattr(self, "_incremental_utterances"):
            return

        all_utterances = self._incremental_utterances
        if not all_utterances:
            return

        tail_ranges = self.tiler.flush()
        if tail_ranges:
            yield from self._process_streaming_segment_events(tail_ranges)

        processing_time_ms = int((time.perf_counter() - self._incremental_t0) * 1000)
        summary = HierarchicalSummary(
            meeting_id=self._incremental_meeting_id,
            segments=self._incremental_segments,
            generated_at=datetime.now(timezone.utc),
            processing_time_ms=processing_time_ms,
        )
        yield OrchestratorEvent(
            type=SummarizationEventType.MEETING_COMPLETED,
            data={"hierarchical_summary": summary.model_dump(mode="json")},
        )
