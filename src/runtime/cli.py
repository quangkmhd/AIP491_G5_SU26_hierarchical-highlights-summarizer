from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from src.service import StreamingOrchestrator
from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance


def _load_transcript(file: TextIO) -> DialogueTranscript:
    """Đọc dữ liệu bản ghi từ file JSON và chuyển đổi thành đối tượng DialogueTranscript."""
    raw = json.load(file)
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        path = getattr(file, "name", "<stdin>")
        raise ValueError(f"{path} must contain a non-empty JSON array of transcripts")

    item = raw[0]
    utterances_raw = item.get("utterances") or []
    utts = [
        Utterance(
            speaker=u.get("speaker", f"no.{i}") if isinstance(u, dict) else f"no.{i}",
            text=u.get("text", u) if isinstance(u, dict) else u,
            index=u.get("index", i) if isinstance(u, dict) else i,
        )
        for i, u in enumerate(utterances_raw)
    ]
    return DialogueTranscript(utterances=utts, meeting_title=item.get("meeting_title"))


def cmd_process(args: argparse.Namespace) -> int:
    """Thực thi lệnh xử lý batch cho file bản ghi cuộc họp và in ra kết quả."""
    transcript = _load_transcript(args.file)
    summary = StreamingOrchestrator().process_batch(transcript)
    output = summary.model_dump(mode="json")

    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote summary to {args.output}")
    else:
        print(f"meeting_id: {output['meeting_id']}")
        print(f"segments:   {len(output['segments'])}")
        print(f"chunks:     {sum(len(s['chunks']) for s in output['segments'])}")
        print(f"time_ms:    {output['processing_time_ms']}")
    return 0


def cmd_stream(args: argparse.Namespace) -> int:
    """Thực thi lệnh xử lý stream phát sự kiện trực tiếp cho bản ghi cuộc họp."""
    transcript = _load_transcript(args.file)
    orchestrator = StreamingOrchestrator()
    seg_count = 0
    final_summary: dict | None = None

    def _stream_events():
        for utt in transcript.utterances:
            yield from orchestrator.accept_utterance(text=utt.text, speaker=utt.speaker, index=utt.index)
        yield from orchestrator.flush_and_finalize()

    for event in _stream_events():
        evt_type = event.get("type")
        if evt_type == "segment-closed":
            seg_count += 1
        if evt_type == "meeting-completed":
            final_summary = event.get("hierarchical_summary")

        if getattr(args, "pretty", False):
            if evt_type == "chunk-closed":
                print(f"Tóm tắt chunk: {event.get('rolling_summary')}")
                sys.stdout.flush()
            elif evt_type == "title-emitted":
                print(f"Chủ đề: {event.get('title')}\n" + "-" * 40)
                sys.stdout.flush()
        else:
            print(json.dumps(event, default=str))

    if args.output and final_summary is not None:
        Path(args.output).write_text(
            json.dumps(final_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if not getattr(args, "pretty", False):
        print(f"# stream finished: {seg_count} segments", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Xây dựng và cấu hình bộ đọc tham số dòng lệnh ArgumentParser."""
    parser = argparse.ArgumentParser(prog="src.runtime.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_process = sub.add_parser("process", help="Process a transcript, print summary")
    p_process.add_argument("file", type=argparse.FileType("r"), help="Path to transcript JSON")
    p_process.add_argument("--output", "-o", type=str, help="Path to write full summary JSON")
    p_process.set_defaults(func=cmd_process)

    p_stream = sub.add_parser("stream", help="Stream summary events as NDJSON")
    p_stream.add_argument("file", type=argparse.FileType("r"), help="Path to transcript JSON")
    p_stream.add_argument("--output", "-o", type=str, help="Path to write final summary JSON")
    p_stream.add_argument("--pretty", action="store_true", help="Print pretty human-readable stream directly to terminal")
    p_stream.set_defaults(func=cmd_stream)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Điểm nhập chính (entry point) để thực thi CLI runner."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    finally:
        file_obj = getattr(args, "file", None)
        if file_obj is not None and hasattr(file_obj, "close"):
            file_obj.close()


if __name__ == "__main__":
    sys.exit(main())
