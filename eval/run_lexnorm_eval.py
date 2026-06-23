"""CLI: run the lexnorm corrector over paired Sherpa/Soniox segments and write artifacts.

Usage from tools/09-meeting-recap-webapp/:

    python -m eval.run_lexnorm_eval \\
        --sherpa-dir /home/quangnhvn34/dev/me/AIP491/data/processed/output_sherpa \\
        --soniox-dir /home/quangnhvn34/dev/me/AIP491/data/processed/output_soniox \\
        --output-dir eval/ \\
        --ollama-model gemma4:12b-it-qat \\
        [--limit N] \\
        [--mode {ollama,fixture}]

Modes:
- ollama (default): call real Ollama at $RECAP_NORMALIZE_BASE_URL.
- fixture: use a canned corrector that returns the input unchanged; useful
  for smoke tests when Ollama is not available.

Outputs (under --output-dir):
- lexnorm_corrected_transcript.jsonl (incremental, resumable)
- lexnorm_results.json (final metrics)
- lexnorm_eval_report.md (final markdown report)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any

from app.services.lexnorm.corrector import (
    OllamaClient,
    TranscriptCorrector,
    TranscriptNormalizer,
)
from app.services.lexnorm.evaluator import LexnormEvaluator, classify_token_transition

from eval.build_transcript import synthesize_transcript
from eval.load_segments import pair_sherpa_soniox


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lexnorm corrector eval on Sherpa/Soniox segments")
    parser.add_argument("--sherpa-dir", required=True, type=Path)
    parser.add_argument("--soniox-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--ollama-model", default="gemma4:12b-it-qat")
    parser.add_argument("--ollama-base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N pairs")
    parser.add_argument(
        "--mode",
        choices=("ollama", "fixture"),
        default="ollama",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Number of parallel Ollama calls per eval run",
    )
    return parser.parse_args()


class _FixtureOllamaClient:
    """Canned Ollama client: returns the input as a no-op JSON correction."""

    def chat(self, *, system_prompt: str, user_prompt: str, model: str, max_tokens: int) -> dict:
        match = re.search(r"## Center utterance to correct\s+U\d+\s*\[[^\]]+\]:\s*(.+)", user_prompt)
        text = match.group(1).strip() if match else user_prompt
        return {
            "message": {
                "content": json.dumps(
                    {"error_words": [], "llm_corrected": text},
                    ensure_ascii=False,
                )
            },
            "model": model,
        }


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_report(path: Path, *, run_config: dict, metrics: dict, examples: dict) -> None:
    lines: list[str] = []
    lines.append("# Lexical Normalization Evaluation Report")
    lines.append("")
    lines.append("## Run Configuration")
    lines.append("")
    for key, value in run_config.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Overall Metrics")
    lines.append("")
    lines.append("| Metric | Raw | Corrected | Delta | Better? |")
    lines.append("| :--- | ---: | ---: | ---: | :---: |")
    lines.append(
        f"| WER | {metrics['wer_raw']:.6f} | {metrics['wer_corrected']:.6f} | "
        f"{metrics['wer_delta']:+.6f} | {'yes' if metrics['wer_delta'] < 0 else 'no'} |"
    )
    lines.append(
        f"| CER | {metrics['cer_raw']:.6f} | {metrics['cer_corrected']:.6f} | "
        f"{metrics['cer_delta']:+.6f} | {'yes' if metrics['cer_delta'] < 0 else 'no'} |"
    )
    lines.append("")
    lines.append("## Confusion Matrix")
    lines.append("")
    lines.append("| Category | Count | Meaning |")
    lines.append("| :--- | ---: | :--- |")
    lines.append(f"| TP | {metrics['tp']} | ASR wrong, corrector fixed correctly |")
    lines.append(f"| FN | {metrics['fn']} | ASR wrong, corrector left wrong |")
    lines.append(f"| FP1 | {metrics['fp1']} | ASR correct, corrector broke it |")
    lines.append(f"| FP2 | {metrics['fp2']} | ASR wrong, corrector changed to a different wrong value |")
    lines.append("")
    lines.append(
        f"Total utterances: {metrics['total_tokens']}, "
        f"total latency: {metrics['latency_ms_total']} ms, "
        f"mean latency: {metrics['latency_ms_mean']} ms"
    )
    lines.append("")
    lines.append("## Representative Examples")
    lines.append("")
    for category, items in examples.items():
        lines.append(f"### {category} Examples (top {len(items)})")
        lines.append("")
        for item in items:
            lines.append(f"- video_id={item.get('video_id')} seg={item.get('segment_number')}")
            lines.append(f"  - raw: `{item.get('raw')}`")
            lines.append(f"  - corrected: `{item.get('corrected')}`")
            lines.append(f"  - truth: `{item.get('truth')}`")
            lines.append(f"  - reason: `{item.get('rejection_reason', '')}`")
        lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    better = metrics["wer_delta"] < 0 and metrics["cer_delta"] < 0
    lines.append(f"- WER improved: {'yes' if metrics['wer_delta'] < 0 else 'no'}.")
    lines.append(f"- CER improved: {'yes' if metrics['cer_delta'] < 0 else 'no'}.")
    lines.append(
        f"- Go/no-go for summary eval phase 2: {'GO' if better else 'NO-GO, tune prompt first'}."
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = _parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / "lexnorm_corrected_transcript.jsonl"
    
    # Check if there is an existing JSONL file for resume
    skipped_indices = set()
    existing_log = []
    if jsonl_path.exists():
        try:
            with jsonl_path.open("r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    skipped_indices.add(line_idx + 1)
                    existing_log.append({
                        "utterance_id": line_idx + 1,
                        "raw": record["raw"],
                        "corrected": record["corrected"],
                        "accepted": record["accepted"],
                        "rejection_reason": record["rejection_reason"],
                        "model_run": record["model_run"],
                    })
            print(f"[SYSTEM] Found existing log file. Resuming from segment {len(skipped_indices) + 1}.")
            sys.stdout.flush()
        except Exception as e:
            print(f"[WARNING] Failed to read existing log for resume: {e}. Starting from scratch.")
            sys.stdout.flush()
            jsonl_path.unlink(missing_ok=True)
            skipped_indices = set()
            existing_log = []

    # Hint Ollama server to allow up to `max_workers` parallel generations.
    # Ollama reads OLLAMA_NUM_PARALLEL on each /api/chat call.
    import os
    os.environ.setdefault("OLLAMA_NUM_PARALLEL", str(max(1, args.max_workers)))

    pairs = pair_sherpa_soniox(args.sherpa_dir, args.soniox_dir)
    if args.limit is not None:
        pairs = pairs[: args.limit]

    if args.mode == "ollama":
        client: Any = OllamaClient(base_url=args.ollama_base_url)
    else:
        client = _FixtureOllamaClient()

    corrector = TranscriptCorrector(ollama_client=client, model=args.ollama_model)  # type: ignore[arg-type]
    normalizer = TranscriptNormalizer(corrector=corrector, max_workers=args.max_workers)

    jsonl_lock = threading.Lock()

    def flush_correction(correction_entry: dict) -> None:
        # Map using utterance_id (which is 1-based index corresponding to pairs)
        idx = correction_entry["utterance_id"] - 1
        if idx < 0 or idx >= len(pairs):
            return
        pair = pairs[idx]
        record = {
            "video_id": pair.video_id,
            "segment_number": pair.segment_number,
            "raw": correction_entry["raw"],
            "truth": pair.soniox_transcript,
            "corrected": correction_entry["corrected"],
            "accepted": correction_entry["accepted"],
            "rejection_reason": correction_entry["rejection_reason"],
            "model_run": correction_entry["model_run"],
        }
        with jsonl_lock:
            _append_jsonl(jsonl_path, record)
        
        # In log ra terminal để theo dõi real-time
        print(f"[{idx + 1}/{len(pairs)}] Corrected: video={pair.video_id} seg={pair.segment_number} | accepted={correction_entry['accepted']} | latency={correction_entry['model_run'].get('latency_ms', 0)}ms")
        sys.stdout.flush()

        # Unload model from Ollama every 4 segments to free up memory cache and prevent thrashing
        if (idx + 1) % 4 == 0:
            print(f"[SYSTEM] Periodically unloading Ollama model to clear memory cache at segment {idx + 1}...")
            sys.stdout.flush()
            try:
                import requests
                # Send unload request
                requests.post(f"{args.ollama_base_url.rstrip('/')}/api/chat", json={"model": args.ollama_model, "keep_alive": 0}, timeout=5)
            except Exception as e:
                print(f"[WARNING] Failed to periodically unload Ollama model: {e}")
                sys.stdout.flush()

    from app.services.lexnorm.types_ import Utterance as _LexUtterance
    lex_utterances: list[_LexUtterance] = [
        _LexUtterance(
            index=idx + 1,
            speaker=f"Speaker_{idx:03d}",
            start_time="",
            end_time="",
            text=pair.sherpa_transcript,
        )
        for idx, pair in enumerate(pairs)
    ]

    started = time.time()
    log_new = []

    def on_result(r) -> None:
        entry = {
            "utterance_id": r.utterance_id,
            "raw": r.raw_text,
            "corrected": r.corrected_text,
            "accepted": r.accepted,
            "rejection_reason": r.rejection_reason,
            "model_run": r.model_run,
        }
        log_new.append(entry)
        flush_correction(entry)

    results = corrector.correct_transcript(
        lex_utterances,
        max_workers=args.max_workers,
        on_result=on_result,
        skipped_indices=skipped_indices,
    )
    elapsed = time.time() - started
    
    
    log = existing_log + log_new
    log.sort(key=lambda x: x["utterance_id"])

    raw_texts = [p.sherpa_transcript for p in pairs]
    truth_texts = [p.soniox_transcript for p in pairs]
    corrected_texts = [p["corrected"] for p in log]
    latency_values = [int(p["model_run"].get("latency_ms", 0)) for p in log]

    evaluator = LexnormEvaluator()
    metrics = evaluator.evaluate(
        raw_texts=raw_texts,
        corrected_texts=corrected_texts,
        truth_texts=truth_texts,
        latency_ms_values=latency_values,
    )

    examples: dict[str, list[dict]] = {"TP": [], "FN": [], "FP1": [], "FP2": []}
    for log_entry, pair in zip(log, pairs):
        category = classify_token_transition(
            raw=log_entry["raw"], corrected=log_entry["corrected"], truth=pair.soniox_transcript
        )
        if len(examples[category]) >= 20:
            continue
        examples[category].append(
            {
                "video_id": pair.video_id,
                "segment_number": pair.segment_number,
                "raw": log_entry["raw"],
                "corrected": log_entry["corrected"],
                "truth": pair.soniox_transcript,
                "rejection_reason": log_entry.get("rejection_reason", ""),
            }
        )

    json_path = args.output_dir / "lexnorm_results.json"
    json_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    run_config = {
        "sherpa_dir": str(args.sherpa_dir),
        "soniox_dir": str(args.soniox_dir),
        "ollama_model": args.ollama_model,
        "ollama_base_url": args.ollama_base_url,
        "mode": args.mode,
        "limit": args.limit if args.limit is not None else "all",
        "max_workers": args.max_workers,
        "pair_count": len(pairs),
        "wall_seconds": round(elapsed, 3),
    }
    report_path = args.output_dir / "lexnorm_eval_report.md"
    _write_report(report_path, run_config=run_config, metrics=metrics, examples=examples)

    print(f"Wrote {jsonl_path}, {json_path}, {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
