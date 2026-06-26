#!/usr/bin/env python3
"""Evaluate hierarchical vs SS-DST on real QMSum data.

This script intentionally does NOT use the synthetic SS-DST transcript. It loads
real QMSum examples from HuggingFace (`pszemraj/qmsum-cleaned`) and evaluates
model outputs against the dataset gold summaries with ROUGE.

Important fairness note:
- The production app prompts are Vietnamese, while QMSum gold summaries are
  English. ROUGE across languages is invalid.
- For this evaluation only, we patch PromptLoader with English equivalents of
  the relevant prompts so BOTH baseline (`hierarchical`) and SS-DST (`ssdst`)
  generate English summaries. This evaluates the algorithmic contribution
  (stateful vs stateless chunking) on a standard English benchmark.
- Dataset transcript/gold are not mocked or hand-created.

Default sample selection:
- split=train
- id=tr-gq-960
- query="Summarize the whole meeting."
This is the shortest QMSum whole-meeting example with a non-empty gold summary,
so it is closest to the generic recap task implemented by this app and cheap
enough to run through a local LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datasets import load_dataset  # noqa: E402
from rouge_score import rouge_scorer  # noqa: E402

from app.methods.hierarchical_recap import HierarchicalRecapMethod  # noqa: E402
from app.methods.ssdst_recap import SsDstRecapMethod  # noqa: E402
from app.services.completion_client import CompletionClient, JsonCompletionRunner  # noqa: E402
from app.services.model_targets import load_local_model_target  # noqa: E402
from app.services.observability import get_observability  # noqa: E402
from app.services.prompt_loader import PromptLoader  # noqa: E402
from app.services.transcript_parser import parse_transcript  # noqa: E402

OUT_DIR = ROOT / "eval" / "qmsum_ssdst_eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EVAL_PROMPTS: dict[str, str] = {
    "system_prompt": """
You are a meeting recap engine. Your only task is to read meeting transcript chunks and return valid JSON matching the requested schema.

Mandatory rules:
- Return parseable JSON only. No Markdown, no code fences, no greetings, no explanations.
- Write recap content in natural English, concise, third person.
- Preserve important technical terms, speaker names, metrics, file paths, and timestamps if they appear in the input.
- Use only information supported by the input. Do not invent decisions, assignees, deadlines, numbers, causes, or results.
- If a required text field has no evidence, write exactly "none".
- Respect all IDs in the input. Do not create new utterance_id, chunk_id, chapter numbers, speaker names, or timestamps.
""".strip(),
    "hierarchical_title": """
You are performing a hierarchical title pass for one meeting chapter.

Goal:
- Generate a short chapter title and one sentence describing the chapter's main content.

Rules:
- Use only `Segment utterances`.
- `title` should be 4-10 English words, specific to the chapter.
- `one_line_summary` must be one sentence, max about 35 words.
- Do not add action items, deadlines, or outcomes unless the segment supports them.

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
You are performing a hierarchical abstractive pass for one or more chunks in the same meeting chapter.

Goal:
- Create one factual note for each chunk so the webapp can assemble a chapterized meeting recap.

Coverage rules:
- Return exactly one note for each `chunk_id` in `Required chunk_ids in order`.
- Do not omit, rename, or create chunk IDs.
- Keep notes in the same order as `Required chunk_ids in order`.

Writing rules:
- `summary` must be English, third person, 1-3 sentences, and reflect the main content of that chunk.
- Set `contains_key_point` true if the chunk contains a decision, conclusion, scope, architecture, risk, blocker, or important result.
- Set `contains_action_item` true if the chunk contains a task, assignment, follow-up, test, report, fix, deployment, or deadline.
- Do not add information outside the corresponding chunk.

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
You are performing an SS-DST (State-Space Dialogue State Tracking) abstractive pass for one chunk in a meeting chapter.

Unlike normal hierarchical summarization, you are NOT summarizing this chunk in isolation. You are given a dialogue belief state accumulated from previous chunks in the same chapter. Use it to:
- Resolve pronouns and references such as "it", "that issue", "the previous point".
- Avoid repeating information already captured in the state; focus on new or updated information in the current chunk.
- Write a factual, coherent English note, third person, 1-3 sentences.

Coverage rules:
- Return exactly one note for each `chunk_id` in `Required chunk_ids in order`.
- Do not omit, rename, or create chunk IDs.

Writing rules:
- `summary` may use entities/decisions from the belief state to make references explicit.
- Set `contains_key_point` true if the chunk contains a decision, conclusion, scope, architecture, risk, blocker, or important result.
- Set `contains_action_item` true if the chunk contains a task, assignment, follow-up, test, report, fix, deployment, or deadline.
- Use only the chunk and belief state. Do not invent information.

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
You are performing SS-DST state update: update the dialogue belief state after processing one chunk.

The belief state is rolling memory: new_state = update(previous_state, new_chunk). Keep it short by:
- Adding only new entities, decisions, and open actions from this chunk.
- Updating existing items rather than duplicating them.
- Applying a forgetting gate: if the state grows too long, keep decisions and open_actions first, then the most important active entities.
- Resolving references: if the chunk says "it", "that", or a similar reference and the previous state contains a likely antecedent, write it in resolved_references.

Return the NEW full belief state, not a diff, with exactly these keys:
- `current_topic`: short phrase.
- `entities`: important active entities/people/systems.
- `decisions`: decisions or conclusions reached so far.
- `open_actions`: unresolved action items with assignee if supported.
- `resolved_references`: array of {"pronoun": "...", "refers_to": "..."}.

If a key has no content, return an empty array (or "" for current_topic). Do not invent information.

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
  "entities": ["entity 1", "entity 2"],
  "decisions": ["decision 1"],
  "open_actions": ["action 1"],
  "resolved_references": [{"pronoun": "it", "refers_to": "the Kafka cluster"}]
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


def load_qmsum_example(split: str, dataset_id: str | None) -> dict[str, Any]:
    ds = load_dataset("pszemraj/qmsum-cleaned", split=split)
    if dataset_id:
        for row in ds:
            if row["id"] == dataset_id:
                return row
        raise SystemExit(f"Could not find QMSum id={dataset_id!r} in split={split!r}")

    # Pick the shortest whole-meeting example with non-empty gold output.
    candidates = []
    for row in ds:
        if not str(row.get("output", "")).strip():
            continue
        query = str(row["input"]).splitlines()[0].strip().lower()
        if query == "summarize the whole meeting.":
            candidates.append(row)
    if not candidates:
        raise SystemExit("No non-empty whole-meeting QMSum sample found")
    return min(candidates, key=lambda row: int(row.get("input_token_count") or 10**9))


def split_query_and_transcript(example: dict[str, Any]) -> tuple[str, str, str]:
    lines = str(example["input"]).splitlines()
    query = lines[0].strip() if lines else ""
    transcript = "\n".join(lines[1:]).strip()
    gold = str(example["output"]).strip()
    return query, transcript, gold


def build_runner() -> JsonCompletionRunner:
    return JsonCompletionRunner(
        CompletionClient(timeout_seconds=180.0),
        retry_attempts=2,
        observability=get_observability(),
    )


def run_method(method_name: str, transcript: str) -> dict[str, Any]:
    method = HierarchicalRecapMethod() if method_name == "hierarchical" else SsDstRecapMethod()
    runner = build_runner()
    targets = [load_local_model_target()]
    utterances = parse_transcript(transcript)
    started = time.time()
    result = method.summarize(utterances, runner, targets, "qmsum-eval.md")
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
        # Give SS-DST credit only for human-visible structured state by adding it
        # to a separate field later; generated_text remains recap-only fair text.
    return "\n".join(parts)


def flatten_ssdst_structured_text(result: dict[str, Any]) -> str:
    parts = [result.get("generated_text", "")]
    for chapter in result.get("chapters", []):
        state = chapter.get("final_belief_state") or {}
        for key in ("decisions", "open_actions", "entities"):
            vals = state.get(key) or []
            if vals:
                parts.extend(str(v) for v in vals)
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
    scores = scorer.score(gold, pred)
    return {name: round(score.fmeasure, 4) for name, score in scores.items()}


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
    metrics = payload["metrics"]
    report = f"""# QMSum SS-DST Evaluation Report

## Data source

- Dataset: HuggingFace `pszemraj/qmsum-cleaned`
- Original benchmark: QMSum meeting summarization
- Split: `{payload['split']}`
- Example id: `{payload['id']}`
- Query: `{payload['query']}`
- Input token count from dataset: `{payload['input_token_count']}`
- Gold output token count from dataset: `{payload['output_token_count']}`
- Parsed utterances: `{payload['utterance_count']}`

This is real QMSum data, not synthetic and not mocked. The selected example is a whole-meeting query, which best matches the generic recap behavior of the app.

## Fairness note

QMSum gold summaries are English. The app's production prompts ask for Vietnamese output, so ROUGE against QMSum would be invalid if we used production Vietnamese prompts. For this benchmark only, both `hierarchical` and `ssdst` are run with equivalent English prompts. The data and gold labels remain unchanged.

## ROUGE results (F1)

| Method | ROUGE-1 | ROUGE-2 | ROUGE-L |
|---|---:|---:|---:|
| hierarchical | {metrics['hierarchical']['rouge']['rouge1']} | {metrics['hierarchical']['rouge']['rouge2']} | {metrics['hierarchical']['rouge']['rougeL']} |
| ssdst recap-only | {metrics['ssdst']['rouge']['rouge1']} | {metrics['ssdst']['rouge']['rouge2']} | {metrics['ssdst']['rouge']['rougeL']} |
| ssdst + structured state | {metrics['ssdst_structured']['rouge']['rouge1']} | {metrics['ssdst_structured']['rouge']['rouge2']} | {metrics['ssdst_structured']['rouge']['rougeL']} |

## Cost

| Method | LLM runs | Wall seconds | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| hierarchical | {metrics['hierarchical']['model_run_count']} | {metrics['hierarchical']['wall_seconds']} | {metrics['hierarchical']['input_tokens']} | {metrics['hierarchical']['output_tokens']} |
| ssdst | {metrics['ssdst']['model_run_count']} | {metrics['ssdst']['wall_seconds']} | {metrics['ssdst']['input_tokens']} | {metrics['ssdst']['output_tokens']} |

## Interpretation

- This benchmark is stricter and more standard than the earlier synthetic SS-DST proof-of-concept.
- Because QMSum is query-focused while the app methods are generic recap methods, ROUGE is informative but not a perfect task match.
- The `ssdst + structured state` row shows whether SS-DST's additional structured decisions/actions/entities help align with the gold summary when exposed as output text.
- Cost must be reported alongside quality because SS-DST adds state-update calls and usually increases latency/tokens.

## Gold summary

```text
{payload['gold']}
```

## Generated summaries

### hierarchical

```text
{payload['results']['hierarchical']['generated_text']}
```

### ssdst recap-only

```text
{payload['results']['ssdst']['generated_text']}
```

### ssdst final belief states

```json
{json.dumps([ch.get('final_belief_state') for ch in payload['results']['ssdst']['chapters']], ensure_ascii=False, indent=2)}
```
"""
    (OUT_DIR / "qmsum_ssdst_eval_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="train")
    parser.add_argument("--id", default=None, help="QMSum example id; default selects shortest whole-meeting sample")
    args = parser.parse_args()

    example = load_qmsum_example(args.split, args.id)
    query, transcript, gold = split_query_and_transcript(example)
    utterances = parse_transcript(transcript)
    print(f"[qmsum-eval] dataset=pszemraj/qmsum-cleaned split={args.split} id={example['id']}")
    print(f"[qmsum-eval] query={query}")
    print(f"[qmsum-eval] utterances={len(utterances)} input_tokens={example.get('input_token_count')} gold_tokens={example.get('output_token_count')}")

    patch_english_prompts()
    results: dict[str, Any] = {}
    metrics: dict[str, Any] = {}

    for method_name in ["hierarchical", "ssdst"]:
        print(f"[qmsum-eval] running {method_name}...")
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
            structured_text = flatten_ssdst_structured_text(result)
            metrics["ssdst_structured"] = {
                "rouge": rouge(gold, structured_text),
                "note": "recap text plus final belief-state decisions/open_actions/entities",
            }
        print(f"[qmsum-eval] {method_name} rouge={metrics[method_name]['rouge']} cost runs={metrics[method_name]['model_run_count']} wall={metrics[method_name]['wall_seconds']}")

    payload = {
        "dataset": "pszemraj/qmsum-cleaned",
        "split": args.split,
        "id": example["id"],
        "query": query,
        "input_token_count": example.get("input_token_count"),
        "output_token_count": example.get("output_token_count"),
        "utterance_count": len(utterances),
        "gold": gold,
        "metrics": metrics,
        "results": results,
    }

    (OUT_DIR / "qmsum_ssdst_eval_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(payload)
    print(f"[qmsum-eval] wrote {OUT_DIR / 'qmsum_ssdst_eval_results.json'}")
    print(f"[qmsum-eval] wrote {OUT_DIR / 'qmsum_ssdst_eval_report.md'}")


if __name__ == "__main__":
    main()
