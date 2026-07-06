"""Summary-only smoke test for dial_id=1 from meeting_committee.json.

WHAT THIS SCRIPT DOES
---------------------
Loads the second Vietnamese committee dialogue (dial_id=1) from
`data/eval_vi/meeting_committee.json`, treats the ground-truth
`segments` list `[16, 65, 12, 27, 10]` as the topic boundaries
(SKIP TextTiling / skip the segment-topic step), then runs the
REAL LLM backbone (Vistral/Gemma GGUF, set by MODEL_LOAD_LLM=1)
through:

  1. For each segment: build 8-utterance chunks.
  2. For each chunk: HierarchicalSummarizationService.abstractive
     (calls real LLM, parses JSON, returns rolling summary).
  3. After all chunks in a segment: HierarchicalSummarizationService.title
     (calls real LLM, parses JSON, returns chapter title).
  4. Collect HierarchicalRecap and write it to
     `docs/generated/eval_summary_dial1.json` and a readable
     Markdown report at `docs/generated/eval_summary_dial1.md`.

The script tail-logs to stdout (and `src.logging` writes to
`logs/run.log` automatically). We will tail the log while it runs
to confirm the real LLM is invoked per chunk and per segment, not
the mock.

USAGE
-----
    # Real LLM (default; uses cached GGUF):
    python scripts/eval_summary_dial1.py

    # Force mock backbone (offline CI / no GPU):
    MODEL_LOAD_LLM=0 python scripts/eval_summary_dial1.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# ---- Path bootstrap so we can import src.* regardless of CWD -------------
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Force real LLM unless explicitly opted-out via env var.
os.environ.setdefault("MODEL_LOAD_LLM", "1")

from src.logging import get_logger  # noqa: E402
from src.service.hierarchical_summarization import (  # noqa: E402
    HierarchicalSummarizationService,
)
from src.types import (  # noqa: E402
    Chunk,
    HierarchicalRecap,
    SegmentResult,
    Utterance,
)

logger = get_logger("scripts.eval_summary_dial1")

DATA_FILE = REPO_ROOT / "data" / "eval_vi" / "meeting_committee.json"
OUTPUT_JSON = REPO_ROOT / "docs" / "generated" / "eval_summary_dial1.json"
OUTPUT_MD = REPO_ROOT / "docs" / "generated" / "eval_summary_dial1.md"
TARGET_DIAL_ID = 1  # user spec: use dial_id=1 (segments=[16, 65, 12, 27, 10])
CHUNK_SIZE = Chunk.MAX_CHUNK_SIZE  # 8


def _speaker_for_index(i: int) -> str:
    """Generate a stable speaker label per utterance (S0, S1, ...)."""
    return f"S{i}"


def _build_utterances(texts: list[str]) -> list[Utterance]:
    return [
        Utterance(speaker=_speaker_for_index(i), text=t, index=i)
        for i, t in enumerate(texts)
    ]


def _chunk_segment(segment_utts: list[Utterance]) -> list[Chunk]:
    return [
        Chunk(utterances=segment_utts[i : i + CHUNK_SIZE])
        for i in range(0, len(segment_utts), CHUNK_SIZE)
    ]


def _format_markdown(recap: HierarchicalRecap, original_sample: dict) -> str:
    lines: list[str] = []
    title = recap.meeting_title or f"Committee Meeting dial_id={TARGET_DIAL_ID}"
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- meeting_id: `{recap.meeting_id}`")
    lines.append(f"- dial_id: {TARGET_DIAL_ID}")
    lines.append(f"- n_segments: {recap.segment_count}")
    lines.append(f"- n_chunks_total: {recap.total_chunks}")
    lines.append(f"- segment_sizes (ground truth): {original_sample.get('segments')}")
    if recap.processing_time_ms is not None:
        lines.append(f"- processing_time_ms: {recap.processing_time_ms}")
    lines.append("")
    for i, seg in enumerate(recap.segments, start=1):
        lines.append(f"## Chapter {i}: {seg.display_title}")
        lines.append(
            f"- utterances: [{seg.utterances_start}..{seg.utterances_end}] "
            f"({seg.utterance_count} utt, {seg.chunk_count} chunks)"
        )
        for cidx, chunk in enumerate(seg.chunks, start=1):
            lines.append(
                f"  - chunk {cidx} (utt [{chunk.utterances[0].index}.."
                f"{chunk.utterances[-1].index}], {len(chunk.utterances)} utt): "
                f"{chunk.rolling_summary or 'none'}"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    if not DATA_FILE.exists():
        logger.error("data file not found path=%s", DATA_FILE)
        return 1

    with DATA_FILE.open("r", encoding="utf-8") as f:
        dialogues = json.load(f)

    target = next((d for d in dialogues if d.get("dial_id") == TARGET_DIAL_ID), None)
    if target is None:
        logger.error("dial_id=%d not present in %s", TARGET_DIAL_ID, DATA_FILE.name)
        return 1

    texts: list[str] = target["utterances"]
    segments_sizes: list[int] = target.get("segments") or [len(texts)]
    logger.info(
        "loaded sample dial_id=%d n_utterances=%d segments=%s",
        TARGET_DIAL_ID, len(texts), segments_sizes,
    )
    if sum(segments_sizes) != len(texts):
        logger.error(
            "segments sum (%d) != n_utterances (%d); aborting",
            sum(segments_sizes), len(texts),
        )
        return 1

    utterances = _build_utterances(texts)

    # ---- Build segments from the GIVEN segments (skip TextTiling) ----------
    segments: list[SegmentResult] = []
    cursor = 0
    for seg_idx, seg_size in enumerate(segments_sizes, start=1):
        seg_utts = utterances[cursor : cursor + seg_size]
        cursor += seg_size
        chunks = _chunk_segment(seg_utts)
        segments.append(
            SegmentResult(
                title=f"Chapter {seg_idx}",
                chunks=chunks,
                utterances_start=seg_utts[0].index,
                utterances_end=seg_utts[-1].index,
            )
        )
    logger.info(
        "prepared %d segments with %d total chunks (skip TextTiling)",
        len(segments), sum(len(s.chunks) for s in segments),
    )

    # ---- Real LLM backbone -------------------------------------------------
    t0 = time.perf_counter()
    logger.info("loading HierarchicalSummarizationService (real LLM unless MODEL_LOAD_LLM=0)")
    summarizer = HierarchicalSummarizationService()
    load_time = time.perf_counter() - t0
    logger.info("summarization service ready in %.2fs", load_time)

    # ---- Per-chunk abstractive + per-segment title ------------------------
    t1 = time.perf_counter()
    total_chunks = 0
    for seg_idx, seg in enumerate(segments, start=1):
        seg_t0 = time.perf_counter()
        for cidx, chunk in enumerate(seg.chunks, start=1):
            utt_range = (chunk.utterances[0].index, chunk.utterances[-1].index)
            logger.info(
                "[seg %d/%d chunk %d/%d] utt[%d..%d] calling LLM (abstractive)...",
                seg_idx, len(segments), cidx, len(seg.chunks),
                utt_range[0], utt_range[1],
            )
            t_call = time.perf_counter()
            summary = summarizer.abstractive(
                chunk, chapter_number=seg_idx, chunk_index=cidx - 1,
            )
            chunk.rolling_summary = summary
            total_chunks += 1
            logger.info(
                "[seg %d/%d chunk %d/%d] abstractive ok in %.2fs summary=%r",
                seg_idx, len(segments), cidx, len(seg.chunks),
                time.perf_counter() - t_call, summary,
            )

        seg_utts_range = (seg.utterances_start, seg.utterances_end)
        logger.info(
            "[seg %d/%d] utt[%d..%d] calling LLM (title)...",
            seg_idx, len(segments), seg_utts_range[0], seg_utts_range[1],
        )
        t_title = time.perf_counter()
        title = summarizer.title(seg, chapter_number=seg_idx)
        seg.title = title
        logger.info(
            "[seg %d/%d] title ok in %.2fs title=%r",
            seg_idx, len(segments), time.perf_counter() - t_title, title,
        )
        logger.info(
            "[seg %d/%d] done in %.2fs",
            seg_idx, len(segments), time.perf_counter() - seg_t0,
        )

    processing_time_ms = int((time.perf_counter() - t1) * 1000)
    logger.info(
        "all segments summarized n_segments=%d n_chunks=%d elapsed_ms=%d",
        len(segments), total_chunks, processing_time_ms,
    )

    recap = HierarchicalRecap(
        meeting_title=f"Committee Meeting dial_id={TARGET_DIAL_ID}",
        segments=segments,
        processing_time_ms=processing_time_ms,
    )

    # ---- Persist output ----------------------------------------------------
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(recap.model_dump_json(indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(_format_markdown(recap, target), encoding="utf-8")
    logger.info("wrote recap json=%s md=%s", OUTPUT_JSON, OUTPUT_MD)

    # ---- Console summary ---------------------------------------------------
    print("=" * 78)
    print(f"dial_id={TARGET_DIAL_ID}  n_segments={recap.segment_count}  "
          f"n_chunks={recap.total_chunks}  processing_time_ms={processing_time_ms}")
    print("=" * 78)
    for i, seg in enumerate(recap.segments, start=1):
        print(f"\n[Chapter {i}] title={seg.display_title!r} "
              f"utt[{seg.utterances_start}..{seg.utterances_end}] "
              f"({seg.utterance_count} utt / {seg.chunk_count} chunks)")
        for cidx, chunk in enumerate(seg.chunks, start=1):
            print(f"   - chunk {cidx} utt[{chunk.utterances[0].index}.."
                  f"{chunk.utterances[-1].index}]: {chunk.rolling_summary!r}")
    print()
    print(f"saved: {OUTPUT_JSON.relative_to(REPO_ROOT)}")
    print(f"saved: {OUTPUT_MD.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
