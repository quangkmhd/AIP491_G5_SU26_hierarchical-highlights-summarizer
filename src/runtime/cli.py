"""CLI runner for batch or stream recap generation.

Usage:
    python -m src.runtime.cli process <transcript.json>
    python -m src.runtime.cli stream  <transcript.json>
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import TextIO

from src.logging import get_logger, log_error_with_fix, request_context
from src.service import StreamingOrchestrator
from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance

logger = get_logger("src.runtime.cli")

def _load_transcript(file: TextIO) -> DialogueTranscript:
    """Đọc dữ liệu bản ghi từ file JSON và chuyển đổi thành đối tượng DialogueTranscript."""
    raw = json.load(file)
    if isinstance(raw, dict):
        # Single transcript object
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        path = getattr(file, "name", "<stdin>")
        raise ValueError(f"{path} must contain a non-empty JSON array of transcripts")

    # Xử lý bản ghi cuộc họp đầu tiên trong mảng dữ liệu
    item = raw[0]
    utterances_raw = item.get("utterances") or item.get("flat_texts") or []
    utts = [
        Utterance(
            speaker=u.get("speaker", f"S{i + 1}") if isinstance(u, dict) else f"S{i + 1}",
            text=u.get("text", u) if isinstance(u, dict) else u,
            index=u.get("index", i) if isinstance(u, dict) else i,
        )
        for i, u in enumerate(utterances_raw)
    ]
    return DialogueTranscript(utterances=utts, meeting_title=item.get("meeting_title"))


def cmd_process(args: argparse.Namespace) -> int:
    """Thực thi lệnh xử lý batch cho file bản ghi cuộc họp và in ra kết quả."""
    logger.info("cli process start file=%s output=%s", args.file.name, args.output or "-")
    transcript = _load_transcript(args.file)
    orchestrator = StreamingOrchestrator()
    recap = orchestrator.process_batch(transcript)
    output = recap.model_dump(mode="json")
    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote recap to {args.output}")
    else:
        print(f"meeting_id: {output['meeting_id']}")
        print(f"segments:   {len(output['segments'])}")
        print(f"chunks:     {sum(len(s['chunks']) for s in output['segments'])}")
        print(f"time_ms:    {output['processing_time_ms']}")
    logger.info(
        "cli process done meeting_id=%s segments=%d",
        output["meeting_id"],
        len(output["segments"]),
    )
    return 0


def cmd_stream(args: argparse.Namespace) -> int:
    """Thực thi lệnh xử lý stream phát sự kiện trực tiếp cho bản ghi cuộc họp."""
    if getattr(args, "pretty", False):
        import logging
        logging.getLogger().setLevel(logging.ERROR)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.ERROR)

    logger.info("cli stream start file=%s output=%s", args.file.name, args.output or "-")
    transcript = _load_transcript(args.file)
    orchestrator = StreamingOrchestrator()
    seg_count = 0
    final_recap: dict | None = None
    
    # Theo dõi trạng thái phục vụ in định dạng đẹp (pretty print)
    segment_id_to_num: dict[str, int] = {}
    segment_chunk_counts: dict[str, int] = {}

    for event in orchestrator.process_stream(transcript):
        if event.type.value == "segment-closed":
            seg_count += 1
        # Capture the final recap from the meeting-completed event
        if event.type.value == "meeting-completed":
            final_recap = event.data["hierarchical_recap"]
        
        if getattr(args, "pretty", False):
            if event.type.value == "chunk-closed":
                seg_id = event.data.get("segment_id")
                if seg_id:
                    if seg_id not in segment_id_to_num:
                        segment_id_to_num[seg_id] = len(segment_id_to_num) + 1
                    segment_chunk_counts[seg_id] = segment_chunk_counts.get(seg_id, 0) + 1
                    summary = event.data.get("rolling_summary")
                    print(f"Tóm tắt chunk: {summary}")
                    sys.stdout.flush()
            elif event.type.value == "title-emitted":
                title = event.data.get("title")
                print(f"Chủ đề: {title}\n" + "-" * 40)
                sys.stdout.flush()
        else:
            # Đầu ra định dạng NDJSON: mỗi sự kiện xuất ra trên một dòng JSON
            print(json.dumps({"type": event.type.value, "payload": event.data}, default=str))

    if args.output and final_recap is not None:
        Path(args.output).write_text(
            json.dumps(final_recap, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if not getattr(args, "pretty", False):
        print(f"# stream finished: {seg_count} segments", file=sys.stderr)
    logger.info("cli stream done segments=%d output=%s", seg_count, args.output or "-")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Xây dựng và cấu hình bộ đọc tham số dòng lệnh ArgumentParser."""
    parser = argparse.ArgumentParser(prog="src.runtime.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_process = sub.add_parser("process", help="Process a transcript, print summary")
    p_process.add_argument("file", type=argparse.FileType("r"), help="Path to transcript JSON")
    p_process.add_argument("--output", "-o", type=str, help="Path to write full recap JSON")
    p_process.set_defaults(func=cmd_process)

    p_stream = sub.add_parser("stream", help="Stream recap events as NDJSON")
    p_stream.add_argument("file", type=argparse.FileType("r"), help="Path to transcript JSON")
    p_stream.add_argument("--output", "-o", type=str, help="Path to write final recap JSON")
    p_stream.add_argument("--pretty", action="store_true", help="Print pretty human-readable stream directly to terminal")
    p_stream.set_defaults(func=cmd_stream)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Điểm nhập chính (entry point) để thực thi CLI runner."""
    parser = build_parser()
    args = parser.parse_args(argv)
    request_id = uuid.uuid4().hex[:12]
    with request_context(request_id=request_id, event=f"cli {args.command}"):
        try:
            return args.func(args)
        except (json.JSONDecodeError, ValueError) as exc:
            fix = _suggest_fix_for_cli_error(exc)
            log_error_with_fix(logger, exc, fix=fix)
            print(f"Error: {exc}", file=sys.stderr)
            print(f"Fix: {fix}", file=sys.stderr)
            return 2
        finally:
            file_obj = getattr(args, "file", None)
            if file_obj is not None and hasattr(file_obj, "close"):
                file_obj.close()


def _suggest_fix_for_cli_error(exc: BaseException) -> str:
    """Đề xuất hướng khắc phục lỗi tương ứng cho các ngoại lệ phát sinh khi chạy CLI."""
    msg = str(exc).lower()
    if isinstance(exc, json.JSONDecodeError):
        return "provide a valid UTF-8 JSON file containing a transcript array"
    if "json array" in msg or "transcripts" in msg:
        return "wrap the transcript object in a non-empty JSON array, or pass a single transcript JSON object"
    if "utterance" in msg or "flat_texts" in msg:
        return "include at least one utterance item in `utterances` or `flat_texts`"
    return "check the input file shape against the CLI transcript JSON format"


if __name__ == "__main__":
    sys.exit(main())
