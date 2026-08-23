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
    """Load transcript data from a JSON file and convert into a DialogueTranscript object."""
    raw = json.load(file)
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        path = getattr(file, "name", "<stdin>")
        raise ValueError(f"{path} must contain a non-empty JSON array of transcripts")

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
    """Execute batch processing for a meeting transcript file and output results."""
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
    """Execute stream processing to emit real-time events for a meeting transcript."""
    transcript = _load_transcript(args.file)
    orchestrator = StreamingOrchestrator()
    seg_count = 0
    final_summary: dict | None = None

    for event in orchestrator.process_stream(transcript):
        if event.type.value == "segment-closed":
            seg_count += 1
        if event.type.value == "meeting-completed":
            final_summary = event.data.get("hierarchical_summary")

        if getattr(args, "pretty", False):
            if event.type.value == "chunk-closed":
                print(f"Chunk Summary: {event.data.get('rolling_summary')}")
                sys.stdout.flush()
            elif event.type.value == "title-emitted":
                print(f"Topic: {event.data.get('title')}\n" + "-" * 40)
                sys.stdout.flush()
        else:
            print(json.dumps({"type": event.type.value, "payload": event.data}, default=str))

    if args.output and final_summary is not None:
        Path(args.output).write_text(
            json.dumps(final_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    if not getattr(args, "pretty", False):
        print(f"# stream finished: {seg_count} segments", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and configure the ArgumentParser for command-line arguments."""
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
    """Main entry point to execute the CLI runner."""
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
