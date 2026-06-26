#!/usr/bin/env python3
"""Evaluate hierarchical vs SS-DST on official QMSum JSON files.

No synthetic transcript and no mocked gold labels are used. The script reads the
official QMSum repository format:

  data/ALL/{train,val,test}/*.json

and uses:
- meeting_transcripts: real meeting transcript turns
- general_query_list[0].answer: human gold whole-meeting summary

The app's production prompts are Vietnamese, while QMSum gold summaries are
English. For ROUGE fairness, this script patches PromptLoader with English
prompts for both methods. The dataset and gold labels remain unchanged.
"""

from __future__ import annotations

import argparse
import json
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

OUT_DIR = ROOT / "eval" / "official_qmsum_ssdst_eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OFFICIAL_REPO = "https://github.com/Yale-LILY/QMSum.git"

EVAL_PROMPTS: dict[str, str] = {
    "system_prompt": """
You are a meeting recap engine. Return parseable JSON only, matching the requested schema. Write concise English summaries. Use only information supported by the input. Do not invent decisions, assignees, deadlines, numbers, causes, or results. Preserve important names and technical terms. If a required text field has no evidence, write exactly "none". Respect all IDs.
""".strip(),
    "hierarchical_title": """
Generate a short chapter title and a one-sentence English chapter summary.
Use only the segment utterances.

Input file: {input_name}
Chapter number: {chapter_number}
Segment utterances:
{segment_utterances}

Return strict JSON only:
{
  "title": "short English chapter title",
  "one_line_summary": "one English sentence summarizing the chapter"
}
""".strip(),
    "hierarchical_abstractive": """
Create one factual English note for each chunk in this meeting chapter.
Return exactly one note for every chunk_id in Required chunk_ids in order.
Do not add information outside the corresponding chunk.
Set contains_key_point/action_item according to evidence in the chunk.

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
      "summary": "Factual English note for this chunk.",
      "contains_key_point": true,
      "contains_action_item": false
    }
  ]
}
""".strip(),
    "ssdst_abstractive": """
Create one factual English note for this chunk using SS-DST.
You are given a dialogue belief state accumulated from previous chunks. Use it to resolve references and keep continuity, but do not invent information.
Return exactly one note for every chunk_id in Required chunk_ids in order.

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
      "summary": "Factual English note that uses the belief state to resolve references.",
      "contains_key_point": true,
      "contains_action_item": false
    }
  ]
}
""".strip(),
    "ssdst_state_update": """
Update the dialogue belief state after processing one chunk.
Return the NEW full belief state, not a diff, with exactly these keys:
current_topic, entities, decisions, open_actions, resolved_references.
Keep it short. Add only supported information. Resolve references if supported by previous state.

Chapter number: {chapter_number}
Chunk index: {chunk_index}
Previous belief state:
{previous_state}
Processed chunk utterances:
{chunk_text}
Chunk summary:
{chunk_summary}

Return strict JSON only:
{
  "current_topic": "short topic",
  "entities": ["entity 1"],
  "decisions": ["decision 1"],
  "open_actions": ["action 1"],
  "resolved_references": [{"pronoun": "it", "refers_to": "the referenced entity"}]
}
""".strip(),
}


def patch_english_prompts() -> None:
    """Force English evaluation prompts for valid ROUGE vs English QMSum gold."""
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


def ensure_qmsum_repo(path: Path | None) -> Path:
    if path and path.exists():
        return path
    dest = Path(tempfile.mkdtemp(prefix="qmsum_official_")) / "QMSum"
    subprocess.run(["git", "clone", "--depth", "1", OFFICIAL_REPO, str(dest)], check=True, stdout=subprocess.DEVNULL)
    return dest


def select_example(repo: Path, split: str, filename: str | None) -> tuple[Path, dict[str, Any]]:
    split_dir = repo / "data" / "ALL" / split
    if filename:
        p = split_dir / filename
        if not p.exists():
            raise SystemExit(f"Official QMSum file not found: {p}")
        return p, json.loads(p.read_text(encoding="utf-8"))

    candidates: list[tuple[int, Path, dict[str, Any]]] = []
    for p in split_dir.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        gqs = data.get("general_query_list") or []
        if not gqs:
            continue
        answer = " ".join(str(gqs[0].get("answer", "")).split())
        query = str(gqs[0].get("query", "")).strip().lower()
        if query == "summarize the whole meeting." and answer:
            candidates.append((len(data.get("meeting_transcripts") or []), p, data))
    if not candidates:
        raise SystemExit(f"No whole-meeting QMSum examples found in {split_dir}")
    _, p, data = sorted(candidates, key=lambda row: row[0])[0]
    return p, data


def qmsum_to_app_transcript(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for i, turn in enumerate(data.get("meeting_transcripts") or [], start=1):
        speaker = str(turn.get("speaker") or f"Speaker {i}").replace("\n", " ").strip() or f"Speaker {i}"
        content = " ".join(str(turn.get("content") or "").split())
        if content:
            lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def gold_general_summary(data: dict[str, Any]) -> tuple[str, str]:
    gq = (data.get("general_query_list") or [{}])[0]
    return str(gq.get("query", "")).strip(), " ".join(str(gq.get("answer", "")).split())


def build_runner() -> JsonCompletionRunner:
    return JsonCompletionRunner(CompletionClient(timeout_seconds=180.0), retry_attempts=2, observability=get_observability())


def run_method(method_name: str, transcript: str) -> dict[str, Any]:
    method = HierarchicalRecapMethod() if method_name == "hierarchical" else SsDstRecapMethod()
    utterances = parse_transcript(transcript)
    started = time.time()
    result = method.summarize(utterances, build_runner(), [load_local_model_target()], "official-qmsum.md")
    result["wall_seconds"] = round(time.time() - started, 2)
    result["utterance_count"] = len(utterances)
    result["model_run_count"] = len(result.get("model_runs", []))
    result["generated_text"] = flatten_recap_text(result)
    result["total_input_tokens"], result["total_output_tokens"] = sum_tokens(result)
    return result


def flatten_recap_text(result: dict[str, Any]) -> str:
    parts: list[str] = []
    for chapter in result.get("chapters", []):
        if chapter.get("title"):
            parts.append(str(chapter["title"]))
        if chapter.get("summary"):
            parts.append(str(chapter["summary"]))
        for chunk in chapter.get("chunks", []):
            for note in chunk.get("notes", []):
                text = str(note.get("summary", "")).strip()
                if text and text.lower() != "none":
                    parts.append(text)
    return "\n".join(parts)


def flatten_ssdst_structured_text(result: dict[str, Any]) -> str:
    parts = [result.get("generated_text", "")]
    for chapter in result.get("chapters", []):
        state = chapter.get("final_belief_state") or {}
        for key in ("decisions", "open_actions", "entities"):
            parts.extend(str(v) for v in (state.get(key) or []))
    return "\n".join(p for p in parts if p)


def sum_tokens(result: dict[str, Any]) -> tuple[int, int]:
    in_tok = out_tok = 0
    for run in result.get("model_runs", []):
        usage = run.get("usage_details", {}) or {}
        in_tok += int(usage.get("prompt_tokens", 0) or 0)
        out_tok += int(usage.get("completion_tokens", 0) or 0)
    return in_tok, out_tok


def rouge(gold: str, pred: str) -> dict[str, float]:
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    return {k: round(v.fmeasure, 4) for k, v in scorer.score(gold, pred).items()}


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": result.get("method"),
        "utterance_count": result.get("utterance_count"),
        "wall_seconds": result.get("wall_seconds"),
        "model_run_count": result.get("model_run_count"),
        "total_input_tokens": result.get("total_input_tokens"),
        "total_output_tokens": result.get("total_output_tokens"),
        "generated_text": result.get("generated_text"),
        "chapters": [
            {
                "chapter_number": ch.get("chapter_number"),
                "title": ch.get("title"),
                "summary": ch.get("summary"),
                "notes": [note.get("summary") for c in ch.get("chunks", []) for note in c.get("notes", [])],
                "final_belief_state": ch.get("final_belief_state"),
            }
            for ch in result.get("chapters", [])
        ],
    }


def write_report(payload: dict[str, Any]) -> None:
    m = payload["metrics"]
    report = f"""# Official QMSum SS-DST Evaluation Report

## Data source

- Official repository: `{OFFICIAL_REPO}`
- Official file: `{payload['official_file']}`
- Split: `{payload['split']}`
- Query: `{payload['query']}`
- Parsed utterances: `{payload['utterance_count']}`
- Gold summary source: `general_query_list[0].answer`
- Transcript source: `meeting_transcripts`

This evaluation uses official QMSum JSON data, not synthetic transcript and not mocked gold labels.

## Fairness note

QMSum gold summaries are English. The app production prompts ask for Vietnamese output. Therefore, for ROUGE fairness, both baseline `hierarchical` and `ssdst` are run with equivalent English prompts inside the evaluation script. The dataset and gold summaries are unchanged.

## ROUGE F1

| Method | ROUGE-1 | ROUGE-2 | ROUGE-L |
|---|---:|---:|---:|
| hierarchical | {m['hierarchical']['rouge']['rouge1']} | {m['hierarchical']['rouge']['rouge2']} | {m['hierarchical']['rouge']['rougeL']} |
| ssdst recap-only | {m['ssdst']['rouge']['rouge1']} | {m['ssdst']['rouge']['rouge2']} | {m['ssdst']['rouge']['rougeL']} |
| ssdst + structured state | {m['ssdst_structured']['rouge']['rouge1']} | {m['ssdst_structured']['rouge']['rouge2']} | {m['ssdst_structured']['rouge']['rougeL']} |

## Cost

| Method | LLM runs | Wall seconds | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| hierarchical | {m['hierarchical']['model_run_count']} | {m['hierarchical']['wall_seconds']} | {m['hierarchical']['input_tokens']} | {m['hierarchical']['output_tokens']} |
| ssdst | {m['ssdst']['model_run_count']} | {m['ssdst']['wall_seconds']} | {m['ssdst']['input_tokens']} | {m['ssdst']['output_tokens']} |

## Gold summary

```text
{payload['gold']}
```

## Generated summary: hierarchical

```text
{payload['results']['hierarchical']['generated_text']}
```

## Generated summary: ssdst

```text
{payload['results']['ssdst']['generated_text']}
```
"""
    (OUT_DIR / "official_qmsum_ssdst_eval_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None, help="Path to official QMSum repo; clone temp if omitted")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--file", default=None, help="Official QMSum JSON filename; default shortest whole-meeting example")
    args = parser.parse_args()

    repo = ensure_qmsum_repo(Path(args.repo) if args.repo else None)
    path, data = select_example(repo, args.split, args.file)
    query, gold = gold_general_summary(data)
    transcript = qmsum_to_app_transcript(data)
    utterances = parse_transcript(transcript)

    print(f"[official-qmsum] repo={repo}")
    print(f"[official-qmsum] file={path}")
    print(f"[official-qmsum] query={query}")
    print(f"[official-qmsum] utterances={len(utterances)} gold_words={len(gold.split())}")

    patch_english_prompts()
    results: dict[str, Any] = {}
    metrics: dict[str, Any] = {}
    for method_name in ["hierarchical", "ssdst"]:
        print(f"[official-qmsum] running {method_name}...")
        result = run_method(method_name, transcript)
        results[method_name] = compact_result(result)
        metrics[method_name] = {
            "rouge": rouge(gold, result["generated_text"]),
            "model_run_count": result["model_run_count"],
            "wall_seconds": result["wall_seconds"],
            "input_tokens": result["total_input_tokens"],
            "output_tokens": result["total_output_tokens"],
        }
        if method_name == "ssdst":
            metrics["ssdst_structured"] = {
                "rouge": rouge(gold, flatten_ssdst_structured_text(result)),
                "note": "recap text plus final belief-state decisions/open_actions/entities",
            }
        print(f"[official-qmsum] {method_name} rouge={metrics[method_name]['rouge']} cost runs={metrics[method_name]['model_run_count']} wall={metrics[method_name]['wall_seconds']}")

    payload = {
        "dataset": "Official QMSum",
        "repository": OFFICIAL_REPO,
        "official_file": str(path),
        "split": args.split,
        "query": query,
        "utterance_count": len(utterances),
        "gold": gold,
        "metrics": metrics,
        "results": results,
    }
    out_json = OUT_DIR / "official_qmsum_ssdst_eval_results.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(payload)
    print(f"[official-qmsum] wrote {out_json}")
    print(f"[official-qmsum] wrote {OUT_DIR / 'official_qmsum_ssdst_eval_report.md'}")


if __name__ == "__main__":
    main()
