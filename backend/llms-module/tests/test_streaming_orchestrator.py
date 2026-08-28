from service.summarization_orchestrator import (
    StreamingOrchestrator,
    SummarizationEventType,
)


class BoundaryAfterSecondUtterance:
    def __init__(self) -> None:
        self.count = 0

    def reset(self) -> None:
        self.count = 0

    def update(self, text: str) -> list[tuple[int, int]]:
        self.count += 1
        return [(0, 1)] if self.count == 2 else []

    def flush(self) -> list[tuple[int, int]]:
        return []


class TailOnlyTiler:
    def reset(self) -> None:
        pass

    def update(self, text: str) -> list[tuple[int, int]]:
        return []

    def flush(self) -> list[tuple[int, int]]:
        return [(0, 0)]


class DeterministicSummarizer:
    def abstractive(self, chunk) -> str:
        return " | ".join(utterance.text for utterance in chunk.utterances)

    def title(self, segment) -> str:
        return "Topic"


def test_streaming_ranges_are_local_positions_but_events_use_external_indexes() -> None:
    orchestrator = StreamingOrchestrator(
        tiler=BoundaryAfterSecondUtterance(),
        summarizer=DeterministicSummarizer(),
    )

    list(orchestrator.accept_utterance("first", "S1", 10))
    events = list(orchestrator.accept_utterance("second", "S2", 11))

    segment = next(
        event for event in events if event.type == SummarizationEventType.SEGMENT_CLOSED
    )
    chunk = next(
        event for event in events if event.type == SummarizationEventType.CHUNK_CLOSED
    )
    assert segment.data["utterances_start"] == 10
    assert segment.data["utterances_end"] == 11
    assert chunk.data["utterances_start"] == 10
    assert chunk.data["utterances_end"] == 11
    assert chunk.data["rolling_summary"] == "first | second"


def test_flush_is_idempotent_after_meeting_completed() -> None:
    orchestrator = StreamingOrchestrator(
        tiler=TailOnlyTiler(),
        summarizer=DeterministicSummarizer(),
    )
    list(orchestrator.accept_utterance("tail", "S1", 0))

    first_flush = list(orchestrator.flush_and_finalize())
    second_flush = list(orchestrator.flush_and_finalize())

    assert [event.type for event in first_flush].count(
        SummarizationEventType.MEETING_COMPLETED
    ) == 1
    assert second_flush == []
