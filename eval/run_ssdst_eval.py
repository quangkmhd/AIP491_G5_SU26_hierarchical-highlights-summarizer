#!/usr/bin/env python3
"""SS-DST vs hierarchical baseline evaluation harness.

Runs both ``hierarchical`` (baseline: chunks summarized in isolated parallel)
and ``ssdst`` (contribution: chunks summarized sequentially with a rolling
dialogue belief state) on a controlled meeting transcript that is engineered
to expose the baseline's coreference/decision-fragmentation weakness, using the
live local Ollama model configured for the webapp.

Produces three artifacts under ``eval/ssdst_eval/``:
  - ssdst_eval_raw.json   : full model outputs for both methods
  - ssdst_eval_metrics.json : computed comparison metrics
  - ssdst_eval_report.md  : human-readable Vietnamese report

The transcript deliberately splits a single decision across chunks 1, 2 and 3
and uses pronouns / deictic references ("nó", "pipeline đó", "API vừa nói")
that only resolve with cross-chunk memory.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure the webapp package is importable when run as a script.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.methods.hierarchical_recap import HierarchicalRecapMethod  # noqa: E402
from app.methods.ssdst_recap import SsDstRecapMethod  # noqa: E402
from app.services.completion_client import CompletionClient, JsonCompletionRunner  # noqa: E402
from app.services.observability import get_observability  # noqa: E402
from app.services.model_targets import load_local_model_target  # noqa: E402

OUT_DIR = ROOT / "eval" / "ssdst_eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# A controlled meeting transcript. 24 utterances => 3 chunks of 8 within a
# single chapter (small enough to keep eval cheap, large enough to span chunks).
# The decision ("chốt kiến trúc microservices + dùng Kafka cho pipeline") is
# introduced in chunk 1, referenced by pronoun in chunk 2, and finalized with
# an action item in chunk 3. Baseline isolation should fragment this; SS-DST
# should carry the entity/decision through the belief state.
TRANSCRIPT = """Kim Anh (00:00 - 00:30): Hôm nay chúng ta bàn về kiến trúc cho hệ thống mới. Mình đề xuất dùng microservices thay vì monolith.
Tuấn (00:30 - 01:00): Ủng hộ. Nhưng cần chọn message broker cho pipeline. Mình nghĩ Kafka hợp lý.
Kim Anh (01:00 - 01:30): Đồng ý. Vậy chốt kiến trúc microservices và dùng Kafka cho pipeline đó nhé.
Lan (01:30 - 02:00): Cần lưu ý, nó yêu cầu team ops phải cấu hình cluster. Ai phụ trách phần này?
Tuấn (02:00 - 02:30): Để mình phụ trách cluster Kafka. Nhưng cần thêm người review cấu hình bảo mật.
Lan (02:30 - 03:00): Mình sẽ review cấu hình bảo mật cho nó. Deadline cuối tuần này nhé.
Kim Anh (03:00 - 03:30): Tốt. Vậy pipeline đó sẽ dùng schema registry. Cần định nghĩa schema cho từng service.
Tuấn (03:30 - 04:00): Mình sẽ draft schema đầu tiên cho service order. Nhưng cần thống nhất naming convention trước.
Lan (04:00 - 04:30): Đề xuất dùng snake_case cho tất cả schema fields. Thế thì consistent.
Kim Anh (04:30 - 05:00): Chốt snake_case. Còn API vừa nói, cần versioning từ đầu. Dùng URL versioning.
Tuấn (05:00 - 05:30): API gateway nên đứng trước các service. Mình sẽ setup gateway demo.
Lan (05:30 - 06:00): Gateway đó cần rate limiting. Mình thêm plugin rate limit.
Kim Anh (06:00 - 06:30): Được. Tổng kết lại: kiến trúc microservices, Kafka cho pipeline, gateway có rate limit.
Tuấn (06:30 - 07:00): Mình phụ trách Kafka cluster và gateway demo. Deadline cuối tuần.
Lan (07:00 - 07:30): Mình review bảo mật Kafka và thêm rate limit cho gateway. Cùng deadline.
Kim Anh (07:30 - 08:00): Cần viết tài liệu architecture decision record cho từng quyết định.
Tuấn (08:00 - 08:30): Mình sẽ viết ADR cho microservices và Kafka. Hai bản.
Lan (08:30 - 09:00): Mình viết ADR cho API gateway và schema registry. Còn naming convention thì ai?
Kim Anh (09:00 - 09:30): Mình viết ADR cho naming convention snake_case. Vậy đủ bốn ADR.
Tuấn (09:30 - 10:00): Cuối cùng, cần setup CI/CD cho tất cả service. Mình phụ trợ phần này.
Lan (10:00 - 10:30): CI/CD phải chạy test schema compatibility. Mình thêm bước kiểm tra.
Kim Anh (10:30 - 11:00): Chốt lại, tuần sau review tất cả ADR và demo gateway. Kết thúc họp.
"""


def build_runner() -> JsonCompletionRunner:
    settings_timeout = 120.0
    try:
        from app.config import AppSettings

        settings_timeout = float(AppSettings().request_timeout_seconds)
    except Exception:
        pass
    return JsonCompletionRunner(
        CompletionClient(timeout_seconds=settings_timeout),
        retry_attempts=2,
        observability=get_observability(),
    )


def run_method(method_name: str, transcript: str) -> dict[str, Any]:
    runner = build_runner()
    targets = [load_local_model_target()]
    method = HierarchicalRecapMethod() if method_name == "hierarchical" else SsDstRecapMethod()
    started = time.time()
    result = method.summarize(
        _parse_to_utterances(transcript),
        runner,
        targets,
        "ssdst-eval.md",
    )
    wall = round(time.time() - started, 2)
    result["wall_seconds"] = wall
    result["model_run_count"] = len(result.get("model_runs", []))
    result["total_input_tokens"], result["total_output_tokens"] = _sum_tokens(result)
    return result


def _parse_to_utterances(transcript: str):
    from app.services.transcript_parser import parse_transcript

    return parse_transcript(transcript)


def _sum_tokens(result: dict[str, Any]) -> tuple[int, int]:
    in_tok = 0
    out_tok = 0
    for run in result.get("model_runs", []):
        usage = run.get("usage_details", {}) or {}
        in_tok += int(usage.get("prompt_tokens", 0) or 0)
        out_tok += int(usage.get("completion_tokens", 0) or 0)
    return in_tok, out_tok


def collect_notes(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten all chunk notes across chapters."""
    notes = []
    for chapter in result.get("chapters", []):
        for chunk in chapter.get("chunks", []):
            for note in chunk.get("notes", []):
                notes.append(
                    {
                        "chapter": chapter.get("chapter_number"),
                        "chunk_id": chunk.get("chunk_id"),
                        "summary": note.get("summary", ""),
                        "contains_key_point": note.get("contains_key_point", False),
                        "contains_action_item": note.get("contains_action_item", False),
                    }
                )
    return notes


# --- Reference / gold signals the methods should recover ---
GOLD_DECISIONS = ["microservices", "kafka", "gateway", "rate limit", "snake_case"]
GOLD_ACTIONS = ["adr", "cluster", "schema", "ci/cd", "deadline"]
GOLD_ENTITIES = ["kafka", "gateway", "pipeline", "api", "schema"]


def compute_metrics(notes: list[dict[str, Any]], result: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(n["summary"].lower() for n in notes)

    def hit(terms: list[str]) -> dict[str, Any]:
        hits = [t for t in terms if t in text]
        return {"recall": round(len(hits) / len(terms), 4), "hit": hits, "miss": [t for t in terms if t not in text]}

    # Coreference resolution proxy: count notes that mention a gold entity
    # WITHOUT re-introducing it from scratch (i.e. referencing prior context).
    # We approximate "dangling reference" heuristics: pronouns/deictic markers
    # left un-resolved in a note.
    dangling_markers = [" nó ", " đó ", " vừa nói ", "cái này", "vừa rồi"]
    dangling_count = sum(1 for n in notes if any(m in f" {n['summary'].lower()} " for m in dangling_markers))

    # Cross-chunk decision continuity: does any single note tie Kafka + pipeline
    # + microservices together (sign the decision survived chunking)?
    continuity_terms = ["kafka", "pipeline", "microservices"]
    continuity_notes = [
        n["summary"]
        for n in notes
        if sum(t in n["summary"].lower() for t in continuity_terms) >= 2
    ]

    return {
        "note_count": len(notes),
        "gold_decision_recall": hit(GOLD_DECISIONS),
        "gold_action_recall": hit(GOLD_ACTIONS),
        "gold_entity_recall": hit(GOLD_ENTITIES),
        "dangling_reference_notes": dangling_count,
        "cross_chunk_continuity_notes": continuity_notes,
        "model_run_count": result.get("model_run_count", 0),
        "wall_seconds": result.get("wall_seconds", 0),
        "input_tokens": result.get("total_input_tokens", 0),
        "output_tokens": result.get("total_output_tokens", 0),
    }


def main() -> None:
    print(f"[ssdst-eval] transcript utterances: {len(_parse_to_utterances(TRANSCRIPT))}")
    print(f"[ssdst-eval] model: {load_local_model_target().model}")

    raw: dict[str, Any] = {}
    metrics: dict[str, Any] = {}

    for method_name in ("hierarchical", "ssdst"):
        print(f"\n[ssdst-eval] running {method_name} ...")
        t0 = time.time()
        try:
            result = run_method(method_name, TRANSCRIPT)
        except Exception as exc:  # noqa: BLE001
            print(f"[ssdst-eval] {method_name} FAILED: {exc}")
            raw[method_name] = {"error": str(exc)}
            metrics[method_name] = {"error": str(exc)}
            continue
        print(f"[ssdst-eval] {method_name} done in {round(time.time()-t0,1)}s, runs={result.get('model_run_count')}")
        notes = collect_notes(result)
        raw[method_name] = {
            "wall_seconds": result.get("wall_seconds"),
            "model_run_count": result.get("model_run_count"),
            "input_tokens": result.get("total_input_tokens"),
            "output_tokens": result.get("total_output_tokens"),
            "chapters": [
                {
                    "chapter_number": ch.get("chapter_number"),
                    "title": ch.get("title"),
                    "summary": ch.get("summary"),
                    "chunks": [
                        {"chunk_id": c.get("chunk_id"), "notes": c.get("notes", [])}
                        for c in ch.get("chunks", [])
                    ],
                    "final_belief_state": ch.get("final_belief_state"),
                }
                for ch in result.get("chapters", [])
            ],
            "notes": notes,
        }
        metrics[method_name] = compute_metrics(notes, result)

    (OUT_DIR / "ssdst_eval_raw.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "ssdst_eval_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[ssdst-eval] wrote raw + metrics to {OUT_DIR}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
