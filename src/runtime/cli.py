"""CLI runner for batch or stream recap generation.

Usage:
    python -m src.runtime.cli process <transcript.json>
    python -m src.runtime.cli stream  <transcript.json>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.service import StreamingOrchestrator
from src.types.transcript import DialogueTranscript
from src.types.utterance import Utterance


def _load_transcript(file) -> DialogueTranscript:
    raw = json.load(file)
    if isinstance(raw, dict):
        # Single transcript object
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise ValueError("Input file must contain a JSON array of transcripts")

    # For MVP: process only the first transcript
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
    return 0


def cmd_stream(args: argparse.Namespace) -> int:
    transcript = _load_transcript(args.file)
    orchestrator = StreamingOrchestrator()
    seg_count = 0
    final_recap: dict | None = None
    for event in orchestrator.process_stream(transcript):
        if event.type.value == "segment-closed":
            seg_count += 1
        # Capture the final recap from the meeting-completed event
        if event.type.value == "meeting-completed":
            final_recap = event.data["hierarchical_recap"]
        # NDJSON output: one event per line
        print(json.dumps({"type": event.type.value, "payload": event.data}, default=str))
    if args.output and final_recap is not None:
        Path(args.output).write_text(
            json.dumps(final_recap, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    print(f"# stream finished: {seg_count} segments", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="src.runtime.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_process = sub.add_parser("process", help="Process a transcript, print summary")
    p_process.add_argument("file", type=argparse.FileType("r"), help="Path to transcript JSON")
    p_process.add_argument("--output", "-o", type=str, help="Path to write full recap JSON")
    p_process.set_defaults(func=cmd_process)

    p_stream = sub.add_parser("stream", help="Stream recap events as NDJSON")
    p_stream.add_argument("file", type=argparse.FileType("r"), help="Path to transcript JSON")
    p_stream.add_argument("--output", "-o", type=str, help="Path to write final recap JSON")
    p_stream.set_defaults(func=cmd_stream)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
