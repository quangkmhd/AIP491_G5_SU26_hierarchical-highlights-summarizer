"""Command-Line Interface (CLI) runner for Text Summarization & Topic Segmentation.

Calls the running FastAPI API / WebSocket microservice endpoints (http://localhost:8000),
or runs locally when --local flag is provided.
"""

from __future__ import annotations
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, TextIO
import urllib.request
import urllib.error

# Configure logger for readable CLI execution
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("llms_module.cli")

# Optional imports for local execution mode
try:
    from service import StreamingOrchestrator
    from schemas_dto.transcript import DialogueTranscript
    from schemas_dto.utterance import Utterance
    HAS_LOCAL_ENGINE = True
except ImportError:
    HAS_LOCAL_ENGINE = False


def _parse_transcript_file(file: TextIO) -> tuple[str, list[dict[str, Any]]]:
    """Parse JSON transcript file and return meeting_title and list of utterance dicts."""
    file_path = getattr(file, "name", "<stdin>")
    logger.info(f"Loading transcript file: {file_path}")

    raw = json.load(file)
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{file_path} must contain a non-empty JSON array of transcripts")

    item = raw[0]
    meeting_title = item.get("meeting_title", "Meeting Transcript")
    utterances_raw = item.get("utterances") or item.get("flat_texts") or []

    utterances = [
        {
            "speaker": u.get("speaker", f"S{i + 1}") if isinstance(u, dict) else f"S{i + 1}",
            "text": u.get("text", u) if isinstance(u, dict) else str(u),
            "index": u.get("index", i) if isinstance(u, dict) else i,
        }
        for i, u in enumerate(utterances_raw)
    ]
    logger.info(f"Parsed meeting '{meeting_title}' with {len(utterances)} utterances.")
    return meeting_title, utterances


def cmd_process(args: argparse.Namespace) -> int:
    """Execute batch processing by sending HTTP POST request to API endpoint (or --local)."""
    if getattr(args, "verbose", False):
        logging.getLogger().setLevel(logging.DEBUG)

    meeting_title, utterances = _parse_transcript_file(args.file)
    start_time = time.time()

    if getattr(args, "local", False):
        logger.info("Executing in LOCAL mode using in-process PyTorch model loader...")
        if not HAS_LOCAL_ENGINE:
            logger.error("Local AI engine dependencies not found for --local mode.")
            return 1
        utts = [Utterance(speaker=u["speaker"], text=u["text"], index=u["index"]) for u in utterances]
        transcript = DialogueTranscript(utterances=utts, meeting_title=meeting_title)
        summary = StreamingOrchestrator().process_batch(transcript)
        output = summary.model_dump(mode="json")
    else:
        # Call running FastAPI API endpoint (Default)
        api_url = getattr(args, "api_url", "http://localhost:8000/api/v1/meetings/process")
        logger.info(f"Sending HTTP POST request to API endpoint: {api_url}")

        payload = {
            "meeting_title": meeting_title,
            "language": "vi",
            "utterances": utterances,
        }
        req_data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                if response.status == 200:
                    resp_bytes = response.read()
                    output = json.loads(resp_bytes.decode("utf-8"))
                    elapsed = round(time.time() - start_time, 2)
                    logger.info(f"API request completed successfully in {elapsed}s (HTTP 200).")
                else:
                    logger.error(f"API returned HTTP status {response.status}")
                    return 1
        except urllib.error.URLError as exc:
            logger.error(f"Failed to connect to API endpoint {api_url}: {exc}")
            logger.warning("Make sure Uvicorn server is running on port 8000, or pass --local flag.")
            return 1

    segments = output.get("segments", [])
    total_chunks = sum(len(s.get("chunks", [])) for s in segments)
    logger.info(f"Hierarchical Summary: {len(segments)} topic segments, {total_chunks} chunk summaries.")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Wrote summary to {args.output}")
    else:
        logger.info(f"Meeting ID:      {output.get('meeting_id')}")
        logger.info(f"Total Segments:  {len(segments)}")
        logger.info(f"Total Chunks:    {total_chunks}")
        logger.info(f"Processing Time: {output.get('processing_time_ms')} ms")

    return 0


async def _stream_websocket_async(args: argparse.Namespace, meeting_title: str, utterances: list[dict[str, Any]]) -> int:
    """Stream utterances via WebSocket endpoint and display live events."""
    try:
        import websockets
    except ImportError:
        logger.error("'websockets' library is required for WebSocket streaming.")
        return 1

    ws_url = getattr(args, "ws_url", "ws://localhost:8000/ws")
    logger.info(f"Connecting to WebSocket endpoint: {ws_url}")

    seg_count = 0
    final_summary: dict[str, Any] | None = None

    try:
        async with websockets.connect(ws_url) as ws:
            logger.info(f"Connected. Streaming {len(utterances)} utterances to server...")
            # Send each utterance
            for u in utterances:
                msg = {
                    "type": "utterance",
                    "speaker": u["speaker"],
                    "text": u["text"],
                    "index": u["index"],
                }
                await ws.send(json.dumps(msg, ensure_ascii=False))
                await asyncio.sleep(0.02)

            logger.info("Sent all utterances. Sending flush signal...")
            await ws.send(json.dumps({"type": "flush"}))

            # Receive events
            while True:
                try:
                    resp_str = await ws.recv()
                    event = json.loads(resp_str)
                    evt_type = event.get("type", "")

                    if evt_type in {"title-emitted", "segment-closed"}:
                        seg_count += 1

                    if evt_type == "meeting-completed":
                        final_summary = event.get("hierarchical_summary")

                    if getattr(args, "pretty", False):
                        if evt_type == "chunk-closed":
                            summary_text = event.get("rolling_summary") or event.get("chunk_summary", "")
                            logger.info(f"[Chunk Summary] {summary_text}")
                        elif evt_type == "title-emitted":
                            title_text = event.get("title") or event.get("chapter_title", "")
                            logger.info(f"[Topic Chapter] {title_text}\n" + "-" * 50)
                    else:
                        logger.info(f"Event [{evt_type}]: {json.dumps(event, ensure_ascii=False)}")

                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket connection closed by server.")
                    break

    except Exception as exc:
        logger.error(f"WebSocket streaming error connecting to {ws_url}: {exc}")
        logger.warning("Make sure Uvicorn server is running on port 8000, or pass --local flag.")
        return 1

    if args.output and final_summary is not None:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(final_summary, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Saved final streaming summary to: {args.output}")

    if not getattr(args, "pretty", False):
        logger.info(f"Stream finished successfully with {seg_count} segments.")
    return 0


def cmd_stream(args: argparse.Namespace) -> int:
    """Execute stream processing by connecting to WebSocket endpoint (or --local)."""
    if getattr(args, "verbose", False):
        logging.getLogger().setLevel(logging.DEBUG)

    meeting_title, utterances = _parse_transcript_file(args.file)

    if getattr(args, "local", False):
        logger.info("Executing stream in LOCAL mode using in-process PyTorch model loader...")
        if not HAS_LOCAL_ENGINE:
            logger.error("Local AI engine dependencies not found for --local mode.")
            return 1
        utts = [Utterance(speaker=u["speaker"], text=u["text"], index=u["index"]) for u in utterances]
        transcript = DialogueTranscript(utterances=utts, meeting_title=meeting_title)
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
                    logger.info(f"[Chunk Summary] {event.data.get('rolling_summary')}")
                elif event.type.value == "title-emitted":
                    logger.info(f"[Topic Chapter] {event.data.get('title')}\n" + "-" * 50)
            else:
                logger.info(f"Event [{event.type.value}]: {json.dumps(event.data, default=str, ensure_ascii=False)}")

        if args.output and final_summary is not None:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(final_summary, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Saved local streaming summary to: {args.output}")

        if not getattr(args, "pretty", False):
            logger.info(f"Stream finished with {seg_count} segments.")
        return 0
    else:
        # Default: Stream via WebSocket endpoint
        return asyncio.run(_stream_websocket_async(args, meeting_title, utterances))


def build_parser() -> argparse.ArgumentParser:
    """Build and configure ArgumentParser for CLI runner."""
    parser = argparse.ArgumentParser(prog="runtime.cli", description="CLI runner for meeting summarization")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p_process = sub.add_parser("process", help="Process transcript via HTTP API endpoint")
    p_process.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="Path to transcript JSON file")
    p_process.add_argument("--output", "-o", type=str, help="Path to write full summary JSON")
    p_process.add_argument("--api-url", type=str, default="http://localhost:8000/api/v1/meetings/process", help="API endpoint URL")
    p_process.add_argument("--local", action="store_true", help="Run local PyTorch engine instead of calling API server")
    p_process.set_defaults(func=cmd_process)

    p_stream = sub.add_parser("stream", help="Stream summary events via WebSocket endpoint")
    p_stream.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="Path to transcript JSON file")
    p_stream.add_argument("--output", "-o", type=str, help="Path to write final summary JSON")
    p_stream.add_argument("--pretty", action="store_true", help="Print pretty human-readable stream directly to terminal")
    p_stream.add_argument("--ws-url", type=str, default="ws://localhost:8000/ws", help="WebSocket endpoint URL")
    p_stream.add_argument("--local", action="store_true", help="Run local PyTorch engine instead of calling WebSocket server")
    p_stream.set_defaults(func=cmd_stream)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point to execute CLI runner."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error(f"Execution failed: {exc}")
        return 2
    finally:
        file_obj = getattr(args, "file", None)
        if file_obj is not None and hasattr(file_obj, "close"):
            file_obj.close()


if __name__ == "__main__":
    sys.exit(main())
