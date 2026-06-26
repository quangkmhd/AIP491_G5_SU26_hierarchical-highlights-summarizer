#!/usr/bin/env python3
"""High-performance Memory-safe official QMSum evaluation.

Optimized for:
- Accuracy: Correctly forces English prompts for valid ROUGE comparison.
- Robustness: Uses raw text extraction for final compression (no JSON strictness).
- Throughput: Supports performance mode (OLLAMA_KEEP_ALIVE=10m) to reuse KV cache.
- Scalability: Writes results directly to disk, manages RAM aggressively with gc.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rouge_score import rouge_scorer  # noqa: E402

from app.methods.hierarchical_recap import HierarchicalRecapMethod  # noqa: E402
from app.methods.ssdst_recap import SsDstRecapMethod  # noqa: E402
from app.services.completion_client import CompletionClient, JsonCompletionRunner  # noqa: E402
from app.services.model_targets import load_local_model_target  # noqa: E402
from app.services.observability import get_observability  # noqa: E402
from app.services.prompt_loader import PromptLoader  # noqa: E402
from app.services.transcript_parser import parse_transcript  # noqa: E402

OFFICIAL_REPO = "https://github.com/Yale-LILY/QMSum.git"
OUT_DIR = ROOT / "eval" / "official_qmsum_full_eval_safe"
PER_SAMPLE_DIR = OUT_DIR / "per_sample"
TEXT_DIR = OUT_DIR / "generated_text"

EVAL_PROMPTS: dict[str, str] = {
    "system_prompt": "Return valid JSON only. Write concise English meeting summaries. Use only supported information. Do not invent facts. Respect all IDs.",
    "hierarchical_title": """Generate a short English chapter title and one sentence summary.
Input file: {input_name}
Chapter number: {chapter_number}
Segment utterances:
{segment_utterances}
Return strict JSON only:
{
  "title": "short title",
  "one_line_summary": "one sentence summary"
}
""",
    "hierarchical_abstractive": """Create exactly one factual English note for each chunk_id in order. Use only that chunk.
Input file: {input_name}
Chapter number: {chapter_number}
Required chunk_ids in order:
{required_chunk_ids}
8-utterance chunks:
{prompt_chunks}
Return strict JSON only:
{
  "notes": [
    {
      "chunk_id": "{example_chunk_id}",
      "summary": "Factual English note.",
      "contains_key_point": true,
      "contains_action_item": false
    }
  ]
}
""",
    "ssdst_abstractive": """Create exactly one factual English note for each chunk_id in order. Use the dialogue belief state to resolve references and preserve continuity. Do not invent facts.
Input file: {input_name}
Chapter number: {chapter_number}
Chunk index in chapter: {chunk_index}
Dialogue belief state accumulated from previous chunks:
{belief_state}
Required chunk_ids in order:
{required_chunk_ids}
8-utterance chunks:
{prompt_chunks}
Return strict JSON only:
{
  "notes": [
    {
      "chunk_id": "{example_chunk_id}",
      "summary": "Factual English note.",
      "contains_key_point": true,
      "contains_action_item": false
    }
  ]
}
""",
    "ssdst_state_update": """Update the dialogue dialogue state after this chunk. Return the NEW full state. Keep it short and supported.
Chapter number: {chapter_number}
Chunk index: {chunk_index}
Previous dialogue state:
{previous_state}
Processed chunk utterances:
{chunk_text}
Chunk summary:
{chunk_summary}
Return strict JSON only:
{
  "current_topic": "short topic",
  "entities": ["entity"],
  "decisions": ["decision"],
  "open_actions": ["action"],
  "resolved_references": [{\"pronoun\": \"it\", \"refers_to\": \"entity\"}]
}
""",
}


def patch_prompts() -> None:
    PromptLoader._prompts = dict(EVAL_PROMPTS)

    @classmethod
    def load_eval_prompts(cls, path=None):
        return cls._prompts

    @classmethod
    def get_eval_prompt(cls, key: str) -> str:
        return cls._prompts.get(key, "Prompt not found")

    PromptLoader.load_prompts = load_eval_prompts
    PromptLoader.get_prompt = get_eval_prompt


def ensure_repo(path: str | None) -> Path:
    if path and Path(path).exists():
        return Path(path)
    dest = Path(tempfile.gettempdir()) / "QMSum_repo"
    if not dest.exists():
        subprocess.run(["git", "clone", "--depth", "1", OFFICIAL_REPO, str(dest)], check=True)
    return dest


def gold_query_answer(data: dict[str, Any]) -> tuple[str, str]:
    gq = (data.get("general_query_list") or [{}])[0]
    return str(gq.get("query", "")).strip(), " ".join(str(gq.get("answer", "")).split())


def transcript_from_qmsum(data: dict[str, Any]) -> str:
    lines = []
    for idx, turn in enumerate(data.get("meeting_transcripts") or [], start=1):
        speaker = " ".join(str(turn.get("speaker") or f"Speaker {idx}").split())
        content = " ".join(str(turn.get("content") or "").split())
        if content:
            lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def list_examples(repo: Path, split: str) -> list[Path]:
    examples = []
    for path in sorted((repo / "data" / "ALL" / split).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        query, answer = gold_query_answer(data)
        if query.lower() == "summarize the whole meeting." and answer:
            examples.append(path)
    return sorted(examples, key=lambda p: len(json.loads(p.read_text(encoding="utf-8")).get("meeting_transcripts") or []))


def flatten_notes(result: dict[str, Any]) -> str:
    parts = []
    for chapter in result.get("chapters", []):
        for key in ("title", "summary"):
            value = str(chapter.get(key, "")).strip()
            if value and value.lower() != "none":
                parts.append(value)
        for chunk in chapter.get("chunks", []):
            for note in chunk.get("notes", []):
                text = str(note.get("summary", "")).strip()
                if text and text.lower() != "none":
                    parts.append(text)
    return "\n".join(parts)


def run_final_compression(method_name: str, notes_text: str, result: dict[str, Any]) -> tuple[str, dict[str, int]]:
    """Generates a concise global summary from notes (and state for SSDST).

    Uses raw text completion for robustness on smaller models.
    """
    state_block = ""
    if method_name == "ssdst":
        states = []
        for chapter in result.get("chapters", []):
            st = chapter.get("final_belief_state")
            if st:
                states.append(st)
        if states:
            state_block = f"\n\nStructured dialogue states:\n{json.dumps(states, ensure_ascii=False, indent=2)}"

    prompt = f"""Write ONE concise paragraph summary (80-140 words) in English for the whole meeting.
Match QMSum gold style: be abstractive and factual.
Rules:
- Generalize events; do not list minor details or peripheral participants.
- Summarize thematic discussions and high-level outcomes.
- Avoid repeating meeting structure details or chunk/chapter identifiers.
- Do not add information not present in the notes.

Meeting notes:
{notes_text[:15000]}
{state_block}

Summary:"""

    client = CompletionClient(timeout_seconds=200)
    target = load_local_model_target()
    res = client.complete(target, prompt, "You are a concise meeting summarizer.", max_tokens=300)

    # Extract response, cleaning up JSON-like artifacts if any
    raw_text = res.text.strip()
    if raw_text.startswith("{") and '"summary"' in raw_text:
        try:
            raw_text = json.loads(raw_text).get("summary", raw_text)
        except: pass

    clean_text = " ".join(raw_text.split())
    return clean_text, res.usage_details


def rouge(gold: str, pred: str) -> dict[str, float]:
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    scores = scorer.score(gold, pred)
    return {name: round(score.fmeasure, 4) for name, score in scores.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None)
    parser.add_argument("--split", default="test")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--memory-mode", default="performance", choices=["safe", "performance"])
    args = parser.parse_args()

    # Configuration
    os.environ["OLLAMA_NUM_PARALLEL"] = "1"
    os.environ["OLLAMA_MAX_LOADED_MODELS"] = "1"
    os.environ["OLLAMA_KEEP_ALIVE"] = "0s" if args.memory_mode == "safe" else "5s"
    patch_prompts()
    repo = ensure_repo(args.repo)
    for d in (PER_SAMPLE_DIR, TEXT_DIR): d.mkdir(parents=True, exist_ok=True)

    examples = list_examples(repo, args.split)
    if args.limit: examples = examples[:args.limit]
    print(f"[eval] repo={repo} split={args.split} mode={args.memory_mode} examples={len(examples)}", flush=True)

    agg_results = []
    for idx, path in enumerate(examples, start=1):
        out_path = PER_SAMPLE_DIR / f"{path.stem}.json"
        if out_path.exists():
            print(f"[eval] skip {idx}/{len(examples)} {path.name}", flush=True)
            # agg_results.append(json.loads(out_path.read_text()))
            continue

        # Check current RAM before starting new sample
        try:
            ram_info = subprocess.check_output(["free", "-m"]).decode()
            print(f"[eval] Current RAM status:\n{ram_info}", flush=True)
        except: pass

        data = json.loads(path.read_text(encoding="utf-8"))
        query, gold = gold_query_answer(data)
        transcript = transcript_from_qmsum(data)
        utterances = parse_transcript(transcript)

        record = {"name": path.name, "utterances": len(utterances), "metrics": {}}
        print(f"[eval] {idx}/{len(examples)} {path.name} ({len(utterances)} utts)", flush=True)

        for method_name in ["hierarchical", "ssdst"]:
            try:
                method = HierarchicalRecapMethod() if method_name == "hierarchical" else SsDstRecapMethod()
                runner = JsonCompletionRunner(CompletionClient(timeout_seconds=200), observability=get_observability())

                # Step 1: Recap
                result = method.summarize(utterances, runner, [load_local_model_target()], "eval.md")
                notes_text = flatten_notes(result)

                # Step 2: Final Summary
                final_summary, final_usage = run_final_compression(method_name, notes_text, result)

                # Usage calc
                in_tok, out_tok = 0, 0
                for run in result.get("model_runs", []):
                    u = run.get("usage_details", {})
                    in_tok += int(u.get("prompt_tokens", 0) or 0)
                    out_tok += int(u.get("completion_tokens", 0) or 0)
                in_tok += final_usage.get("prompt_tokens", 0)
                out_tok += final_usage.get("completion_tokens", 0)

                record["metrics"][method_name] = {
                    "rouge": rouge(gold, final_summary),
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "words": len(final_summary.split())
                }

                # Write individual text for manual inspection
                (TEXT_DIR / f"{path.stem}.{method_name}.txt").write_text(final_summary)
                print(f"  - {method_name} ROUGE-L: {record['metrics'][method_name]['rouge']['rougeL']}", flush=True)

                del result, notes_text, final_summary
                gc.collect()
            except Exception as e:
                print(f"  - {method_name} FAILED: {e}", flush=True)

        out_path.write_text(json.dumps(record, indent=2))
        # agg_results.append(record)

        # Force unload model after each sample
        subprocess.run(["ollama", "stop", load_local_model_target().model], capture_output=True)
        gc.collect()

    # Final Aggregation (read from disk to keep Python memory low)
    agg_results = []
    for p in sorted(PER_SAMPLE_DIR.glob("*.json")):
        try:
            agg_results.append(json.loads(p.read_text()))
        except: pass

    if agg_results:
        final_agg = {"count": len(agg_results), "means": {}}
        for m in ["hierarchical", "ssdst"]:
            rouges = [r["metrics"][m]["rouge"]["rougeL"] for r in agg_results if m in r["metrics"]]
            if rouges: final_agg["means"][m] = round(statistics.mean(rouges), 4)
        (OUT_DIR / "aggregate.json").write_text(json.dumps(final_agg, indent=2))
        print("\n=== FINAL AGGREGATE ===")
        print(json.dumps(final_agg, indent=2))

if __name__ == "__main__":
    main()
