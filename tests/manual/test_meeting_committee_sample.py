"""Manual end-to-end smoke test for the Types layer (model-001).

This is a runnable sanity check, NOT production code. It loads the FIRST
Vietnamese dialogue from `data/eval_vi/meeting_committee.json`, wraps it in
the new Pydantic types, and serializes the result to JSON.

Run with:

    python tests/manual/test_meeting_committee_sample.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.types import (
    Chunk,
    DialogueTranscript,
    HierarchicalRecap,
    SegmentResult,
    TranscriptIngestionRequest,
)

DATA_FILE = REPO_ROOT / "data" / "eval_vi" / "meeting_committee.json"
CHUNK_SIZE = Chunk.MAX_CHUNK_SIZE


def _build_transcript(sample: dict) -> DialogueTranscript:
    request = TranscriptIngestionRequest(
        meeting_title=f"Committee Meeting {sample['dial_id']}",
        flat_texts=sample["utterances_vi"],
        language="vi",
        metadata={"set": sample.get("set", "test")},
    )
    return request.materialize()


def _chunk_segment(segment_utterances: list) -> list[Chunk]:
    return [
        Chunk(utterances=segment_utterances[i : i + CHUNK_SIZE])
        for i in range(0, len(segment_utterances), CHUNK_SIZE)
    ]


def _build_recap(sample: dict) -> HierarchicalRecap:
    transcript = _build_transcript(sample)

    cursor = 0
    segments: list[SegmentResult] = []
    for index, length in enumerate(sample["segments"]):
        segment_utterances = transcript.utterances[cursor : cursor + length]
        segments.append(
            SegmentResult(
                title=f"Chapter {index + 1}",
                chunks=_chunk_segment(segment_utterances),
                utterances_start=cursor,
                utterances_end=cursor + length - 1,
            )
        )
        cursor += length

    return HierarchicalRecap(
        meeting_id=UUID(int=(sample["dial_id"] + 1) * (10**12)),
        segments=segments,
        meeting_title=transcript.meeting_title,
    )


def main() -> int:
    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}", file=sys.stderr)
        return 1

    with DATA_FILE.open("r", encoding="utf-8") as f:
        dialogues = json.load(f)
    if not dialogues:
        print("No dialogues found in data file.", file=sys.stderr)
        return 1

    sample = dialogues[0]
    recap = _build_recap(sample)

    print("=== Types-layer smoke test: first Vietnamese committee meeting ===")
    print(f"meeting_id     : {recap.meeting_id}")
    print(f"meeting_title  : {recap.meeting_title}")
    print(f"segments       : {recap.segment_count}")
    print(f"total_chunks   : {recap.total_chunks}")
    print(f"first segment  : '{recap.segments[0].title}' "
          f"({recap.segments[0].utterance_count} utts, "
          f"{recap.segments[0].chunk_count} chunks)")
    print(f"first chunk    : {len(recap.segments[0].chunks[0].utterances)} utts")

    out_file = REPO_ROOT / "docs" / "generated" / "model001_demo_recap.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(recap.model_dump_json(indent=2), encoding="utf-8")
    print(f"wrote         : {out_file.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
