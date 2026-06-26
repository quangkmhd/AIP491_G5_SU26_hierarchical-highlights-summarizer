#!/usr/bin/env python3
"""Run full official QMSum test evaluation with resume support.

This is the no-mock, no-synthetic evaluation requested by the user. It iterates
over all official QMSum test JSON files that contain `general_query_list[0]` and
compares the app's `hierarchical` and `ssdst` methods against the human gold
whole-meeting summary via ROUGE.

The script writes one JSON result per meeting as soon as it finishes so it can
resume after interruption.
"""

from __future__ import annotations

import argparse
import json
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
OUT_DIR = ROOT / "eval" / "official_qmsum_full_eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Compact English eval prompts: QMSum gold summaries are English; app production
# prompts are Vietnamese. Both methods get the same English prompts for fair ROUGE.
EVAL_PROMPTS: dict[str, str] = {
    "system_prompt": "Return valid JSON only. Write concise English meeting summaries. Use only information supported by the input. Do not invent facts. Respect all IDs.",
    "hierarchical_title": """Generate a short English chapter title and one sentence summary.\nInput file: {input_name}\nChapter number: {chapter_number}\nSegment utterances:\n{segment_utterances}\nReturn strict JSON only:\n{\n  \"title\": \"short title\",\n  \"one_line_summary\": \"one sentence summary\"\n}\n""",
    "hierarchical_abstractive": """Create exactly one factual English note for each chunk_id in order. Use only that chunk.\nInput file: {input_name}\nChapter number: {chapter_number}\nRequired chunk_ids in order:\n{required_chunk_ids}\n8-utterance chunks:\n{prompt_chunks}\nReturn strict JSON only:\n{\n  \"notes\": [\n    {\n      \"chunk_id\": \"{example_chunk_id}\",\n      \"summary\": \"Factual English note.\",\n      \"contains_key_point\": true,\n      \"contains_action_item\": false\n    }\n  ]\n}\n""",
    "ssdst_abstractive": """Create exactly one factual English note for each chunk_id in order. Use the dialogue belief state to resolve references and preserve continuity. Do not invent facts.\nInput file: {input_name}\nChapter number: {chapter_number}\nChunk index in chapter: {chunk_index}\nDialogue belief state accumulated from previous chunks:\n{belief_state}\nRequired chunk_ids in order:\n{required_chunk_ids}\n8-utterance chunks:\n{prompt_chunks}\nReturn strict JSON only:\n{\n  \"notes\": [\n    {\n      \"chunk_id\": \"{example_chunk_id}\",\n      \"summary\": \"Factual English note.\",\n      \"contains_key_point\": true,\n      \"contains_action_item\": false\n    }\n  ]\n}\n""",
    "ssdst_state_update": """Update the dialogue belief state after this chunk. Return the NEW full state. Keep it short and supported.\nChapter number: {chapter_number}\nChunk index: {chunk_index}\nPrevious belief state:\n{previous_state}\nProcessed chunk utterances:\n{chunk_text}\nChunk summary:\n{chunk_summary}\nReturn strict JSON only:\n{\n  \"current_topic\": \"short topic\",\n  \"entities\": [\"entity\"],\n  \"decisions\": [\"decision\"],\n  \"open_actions\": [\"action\"],\n  \"resolved_references\": [{\"pronoun\": \"it\", \"refers_to\": \"entity\"}]\n}\n""",
}


def patch_prompts() -> None:
    """Force English evaluation prompts.

    PromptLoader normally reloads app/prompts.yaml when _loaded_path/_mtime do
    not match the real prompt file. Earlier versions only assigned _prompts,
    which allowed load_prompts() to reload the Vietnamese production prompts.
    Monkey-patching load_prompts/get_prompt here keeps QMSum evaluation outputs
    in English so ROUGE against English gold summaries is valid.
    """
    PromptLoader._prompts = dict(EVAL_PROMPTS)

    @classmethod
    def load_eval_prompts(cls, path=None):  # type: ignore[no-untyped-def]
        return cls._prompts

    @classmethod
    def get_eval_prompt(cls, key: str) -> str:
        if key not in cls._prompts:
            raise KeyError(f"Prompt key '{key}' not found in eval prompts")
        return cls._prompts[key]

    PromptLoader.load_prompts = load_eval_prompts  # type: ignore[method-assign]
    PromptLoader.get_prompt = get_eval_prompt  # type: ignore[method-assign]


def ensure_repo(path: str | None) -> Path:
    if path and Path(path).exists():
        return Path(path)
    dest = Path(tempfile.mkdtemp(prefix="qmsum_official_full_")) / "QMSum"
    subprocess.run(["git", "clone", "--depth", "1", OFFICIAL_REPO, str(dest)], check=True, stdout=subprocess.DEVNULL)
    return dest


def transcript_from_qmsum(data: dict[str, Any]) -> str:
    lines = []
    for i, turn in enumerate(data.get("meeting_transcripts") or [], start=1):
        speaker = " ".join(str(turn.get("speaker") or f"Speaker {i}").split())
        content = " ".join(str(turn.get("content") or "").split())
        if content:
            lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def gold_query_answer(data: dict[str, Any]) -> tuple[str, str]:
    gq = (data.get("general_query_list") or [{}])[0]
    return str(gq.get("query", "")).strip(), " ".join(str(gq.get("answer", "")).split())


def build_runner() -> JsonCompletionRunner:
    return JsonCompletionRunner(CompletionClient(timeout_seconds=180.0), retry_attempts=2, observability=get_observability())


def run_method(method_name: str, transcript: str) -> dict[str, Any]:
    method = HierarchicalRecapMethod() if method_name == "hierarchical" else SsDstRecapMethod()
    utt = parse_transcript(transcript)
    started = time.time()
    result = method.summarize(utt, build_runner(), [load_local_model_target()], "official-qmsum-full.md")
    result["wall_seconds"] = round(time.time() - started, 2)
    result["utterance_count"] = len(utt)
    result["model_run_count"] = len(result.get("model_runs", []))
    result["generated_text"] = flatten_text(result)
    result["total_input_tokens"], result["total_output_tokens"] = sum_tokens(result)
    return result


def flatten_text(result: dict[str, Any]) -> str:
    parts = []
    for ch in result.get("chapters", []):
        parts.extend(str(ch.get(k, "")) for k in ("title", "summary") if ch.get(k))
        for c in ch.get("chunks", []):
            for n in c.get("notes", []):
                s = str(n.get("summary", "")).strip()
                if s and s.lower() != "none":
                    parts.append(s)
    return "\n".join(parts)


def sum_tokens(result: dict[str, Any]) -> tuple[int, int]:
    inp = out = 0
    for run in result.get("model_runs", []):
        u = run.get("usage_details", {}) or {}
        inp += int(u.get("prompt_tokens", 0) or 0)
        out += int(u.get("completion_tokens", 0) or 0)
    return inp, out


def rouge(gold: str, pred: str) -> dict[str, float]:
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    return {k: round(v.fmeasure, 4) for k, v in scorer.score(gold, pred).items()}


def compact(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "wall_seconds": result["wall_seconds"],
        "model_run_count": result["model_run_count"],
        "input_tokens": result["total_input_tokens"],
        "output_tokens": result["total_output_tokens"],
        "generated_text": result["generated_text"],
    }


def list_examples(repo: Path, split: str) -> list[Path]:
    paths = []
    for p in sorted((repo / "data" / "ALL" / split).glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        query, answer = gold_query_answer(data)
        if query.strip().lower() == "summarize the whole meeting." and answer:
            paths.append(p)
    return sorted(paths, key=lambda p: len(json.loads(p.read_text(encoding="utf-8")).get("meeting_transcripts") or []))


def aggregate() -> dict[str, Any]:
    rows = []
    for p in sorted((OUT_DIR / "per_sample").glob("*.json")):
        rows.append(json.loads(p.read_text(encoding="utf-8")))
    agg: dict[str, Any] = {"completed": len(rows), "methods": {}}
    for method in ["hierarchical", "ssdst"]:
        vals = {"rouge1": [], "rouge2": [], "rougeL": [], "wall_seconds": [], "model_run_count": [], "input_tokens": [], "output_tokens": []}
        for r in rows:
            if method not in r.get("metrics", {}):
                continue
            m = r["metrics"][method]
            for k in ["rouge1", "rouge2", "rougeL"]:
                vals[k].append(m["rouge"][k])
            for k in ["wall_seconds", "model_run_count", "input_tokens", "output_tokens"]:
                vals[k].append(m[k])
        agg["methods"][method] = {
            k: {"mean": round(statistics.mean(v), 4), "stdev": round(statistics.pstdev(v), 4)} if v else None
            for k, v in vals.items()
        }
    if agg["methods"].get("hierarchical") and agg["methods"].get("ssdst"):
        agg["delta_mean"] = {}
        for k in ["rouge1", "rouge2", "rougeL"]:
            h = agg["methods"]["hierarchical"][k]["mean"]
            s = agg["methods"]["ssdst"][k]["mean"]
            agg["delta_mean"][k] = {"absolute": round(s - h, 4), "relative_percent": round(((s - h) / h * 100), 2) if h else None}
    (OUT_DIR / "aggregate.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    return agg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=None)
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit", type=int, default=0, help="0 means all")
    ap.add_argument("--resume", action="store_true", default=True)
    args = ap.parse_args()

    repo = ensure_repo(args.repo)
    patch_prompts()
    per_dir = OUT_DIR / "per_sample"
    per_dir.mkdir(parents=True, exist_ok=True)

    examples = list_examples(repo, args.split)
    if args.limit:
        examples = examples[: args.limit]
    print(f"[full-qmsum] repo={repo} split={args.split} examples={len(examples)} out={OUT_DIR}")

    for idx, path in enumerate(examples, start=1):
        out_path = per_dir / f"{path.stem}.json"
        if args.resume and out_path.exists():
            print(f"[full-qmsum] skip existing {idx}/{len(examples)} {path.name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        query, gold = gold_query_answer(data)
        transcript = transcript_from_qmsum(data)
        utt_count = len(parse_transcript(transcript))
        print(f"[full-qmsum] start {idx}/{len(examples)} {path.name} utterances={utt_count} gold_words={len(gold.split())}", flush=True)
        record = {"file": str(path), "name": path.name, "split": args.split, "query": query, "utterance_count": utt_count, "gold": gold, "metrics": {}, "results": {}}
        for method in ["hierarchical", "ssdst"]:
            print(f"[full-qmsum]   running {method}", flush=True)
            try:
                result = run_method(method, transcript)
                record["metrics"][method] = {
                    "rouge": rouge(gold, result["generated_text"]),
                    "wall_seconds": result["wall_seconds"],
                    "model_run_count": result["model_run_count"],
                    "input_tokens": result["total_input_tokens"],
                    "output_tokens": result["total_output_tokens"],
                }
                record["results"][method] = compact(result)
                print(f"[full-qmsum]   {method} rouge={record['metrics'][method]['rouge']} wall={result['wall_seconds']}", flush=True)
            except Exception as exc:  # noqa: BLE001
                record["metrics"][method] = {"error": str(exc)}
                print(f"[full-qmsum]   {method} ERROR {exc}", flush=True)
        out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        agg = aggregate()
        print(f"[full-qmsum] completed={agg['completed']} aggregate_delta={agg.get('delta_mean')}", flush=True)

    agg = aggregate()
    print(json.dumps(agg, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
