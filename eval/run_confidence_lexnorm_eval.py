"""CLI: run confidence-guided lexnorm corrector over paired Sherpa/Soniox segments.

Usage from tools/09-meeting-recap-webapp/:

    python -m eval.run_confidence_lexnorm_eval \
        --sherpa-dir /home/quangnhvn34/dev/me/AIP491/data/processed/output_sherpa \
        --soniox-dir /home/quangnhvn34/dev/me/AIP491/data/processed/output_soniox \
        --output-dir eval/ \
        --ollama-model gemma4:12b-it-qat \
        [--limit N]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# Thêm PYTHONPATH để import load_segments và app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.lexnorm.corrector import OllamaClient, ModelUnavailableError
from app.services.lexnorm.prompt import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES
from app.services.lexnorm.types_ import Utterance, CorrectionResult, CorrectionResponse
from app.services.lexnorm.evaluator import LexnormEvaluator, classify_token_transition
from eval.load_segments import pair_sherpa_soniox


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run confidence-guided lexnorm corrector eval")
    parser.add_argument("--sherpa-dir", required=True, type=Path)
    parser.add_argument("--soniox-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--ollama-model", default="gemma4:12b-it-qat")
    parser.add_argument("--ollama-base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N pairs")
    parser.add_argument("--threshold", type=float, default=0.85, help="Confidence threshold below which to flag tokens")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Number of parallel Ollama calls per eval run",
    )
    return parser.parse_args()


# Mở rộng SYSTEM_PROMPT với hướng dẫn tối ưu hóa WER và cấu trúc JSON rút gọn
SYSTEM_PROMPT_WITH_CONFIDENCE = SYSTEM_PROMPT + (
    "\n\n## HUONG DAN VE PHAN KHU error_words:\n"
    "Khong can dua cac thay the viet hoa/viet thuong (casing) hoac them dau cau vao 'error_words'. "
    "Moi phan tu trong 'error_words' chi chua cac tu bi sai chinh ta hoac sai phien am (vi du: 'TRAC BOC' -> 'chat box'). "
    "Casing va dau cau chi can ap dung truc tiep vao 'llm_corrected'. "
    "Dieu nay giup JSON ngan ngon va khong bi cat cut."
    "\n\n## QUY TẮC BẮT BUỘC ĐỂ GIẢM WER:\n"
    "1. KHÔNG ĐƯỢC tự ý thêm bất kỳ từ nào không có trong bản nháp (Ví dụ: Không thêm 'bảng' vào trước 'B', giữ nguyên 'cái B').\n"
    "2. KHÔNG ĐƯỢC diễn giải hoặc mở rộng các từ viết tắt hay chữ số (Ví dụ: Giữ nguyên 'một' hay 'hai' thay vì viết 'một là', 'hai là').\n"
    "3. Giữ nguyên các tên riêng hoặc cụm từ nếu chúng có vẻ là tên người hoặc tên riêng (Ví dụ: 'Cam Trần' giữ nguyên, không sửa thành 'cam kết').\n"
    "4. Tuyệt đối tôn trọng cấu trúc từ của bản nháp, chỉ sửa chính tả của từ bị sai âm học."
    "\n\n## KINH NGHIEM DAC BIET:\n"
    "Neu trong prompt co muc '## ASR Low-Confidence Tokens', day la danh sach cac tu ma bo ma hoa am thanh bao cao "
    "la co kha nang bi nhan dang sai (do tu tin thap). Hay dac biet chu y doi chieu cac tu nay voi ngu canh cuoc hop va tu dien de "
    "hieu chinh chung cho dung (vi du: 'cell appin' -> 'sales admin', 'NASA Manila' -> 'Nelson Mandela', 'trac boc' -> 'chat box')."
)


def build_confidence_user_prompt(
    center: Utterance,
    context_utterances: list[Utterance],
    low_conf_info: str
) -> str:
    parts: list[str] = []
    parts.append("## Few-shot examples")
    for example in FEW_SHOT_EXAMPLES[:2]:
        parts.append("INPUT:")
        parts.append(json.dumps(example["input"], ensure_ascii=False, indent=2))
        parts.append("OUTPUT:")
        parts.append(example["output"])
        parts.append("---")

    parts.append("## Center utterance to correct")
    parts.append(f"U{center.index} [{center.speaker}]: {center.text}")
    
    if low_conf_info:
        parts.append("## ASR Low-Confidence Tokens (WARNING: These tokens have a high probability of being transcribed incorrectly. Check them against context and verify spelling):")
        parts.append(low_conf_info)
        parts.append("")

    parts.append("## Context utterances (window: 3 before + 3 after)")
    if context_utterances:
        for utterance in context_utterances:
            parts.append(f"U{utterance.index} [{utterance.speaker}]: {utterance.text}")
    else:
        parts.append("(none)")

    parts.append("## Output")
    parts.append(
        "Return ONLY a single JSON object that follows the schema in the system prompt. "
        "Do not include any prose, markdown fence, or explanation."
    )

    return "\n".join(parts)


def correct_utterance_with_confidence(
    client: OllamaClient,
    model: str,
    center: Utterance,
    context_utterances: list[Utterance],
    low_conf_info: str,
    max_tokens: int = 1024
) -> CorrectionResult:
    model_run: dict[str, Any] = {
        "target": model,
        "latency_ms": 0,
        "error": "",
    }
    if not center.text.strip():
        return CorrectionResult(
            utterance_id=center.index,
            raw_text=center.text,
            corrected_text="",
            accepted=True,
            rejection_reason="",
            model_run=model_run,
        )
    
    user_prompt = build_confidence_user_prompt(center, context_utterances, low_conf_info)
    schema = CorrectionResponse.model_json_schema()
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            started = time.time()
            # Under heavy memory swapping, strict grammar validation might trigger timeouts/aborts in Ollama.
            # Fall back to generic "json" mode on subsequent attempts to speed up and stabilize generation.
            fmt = schema if attempt == 1 else "json"
            payload = client.chat(
                system_prompt=SYSTEM_PROMPT_WITH_CONFIDENCE,
                user_prompt=user_prompt,
                model=model,
                max_tokens=max_tokens,
                response_schema=fmt,
            )
            latency = int((time.time() - started) * 1000)
            model_run["latency_ms"] += latency
        except ModelUnavailableError as exc:
            model_run["error"] = str(exc)
            return CorrectionResult(
                utterance_id=center.index,
                raw_text=center.text,
                corrected_text=center.text,
                accepted=False,
                rejection_reason=f"model_unavailable:{exc}",
                model_run=model_run,
            )
        except Exception as exc:
            model_run["error"] = f"attempt_{attempt}_http_error:{exc}"
            if attempt == max_attempts:
                return CorrectionResult(
                    utterance_id=center.index,
                    raw_text=center.text,
                    corrected_text=center.text,
                    accepted=False,
                    rejection_reason=f"http_error:{exc}",
                    model_run=model_run,
                )
            time.sleep(0.5 * attempt)
            continue

        message = payload.get("message", {}) if isinstance(payload, dict) else {}
        text = message.get("content", "") if isinstance(message, dict) else ""

        # Robust JSON extraction to handle markdown blocks or trailing text
        cleaned_text = text.strip()
        start_idx = cleaned_text.find('{')
        end_idx = cleaned_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned_text = cleaned_text[start_idx:end_idx+1]
        elif cleaned_text.startswith("```"):
            cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
            cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

        try:
            parsed = CorrectionResponse.model_validate_json(cleaned_text)
            return CorrectionResult(
                utterance_id=center.index,
                raw_text=center.text,
                corrected_text=parsed.llm_corrected,
                accepted=True,
                rejection_reason="",
                model_run=model_run,
            )
        except Exception as exc:
            # Fallback manual parsing if strict schema validation fails
            try:
                data = json.loads(cleaned_text)
                if isinstance(data, dict):
                    for key in ["llm_corrected", "corrected", "corrected_text", "text"]:
                        if key in data and isinstance(data[key], str) and data[key].strip():
                            return CorrectionResult(
                                utterance_id=center.index,
                                raw_text=center.text,
                                corrected_text=data[key].strip(),
                                accepted=True,
                                rejection_reason="",
                                model_run=model_run,
                            )
            except Exception:
                pass

            model_run["error"] = f"attempt_{attempt}_validation_error:{exc}"
            if attempt == max_attempts:
                return CorrectionResult(
                    utterance_id=center.index,
                    raw_text=center.text,
                    corrected_text=center.text,
                    accepted=False,
                    rejection_reason=f"validation_error:{exc}",
                    model_run=model_run,
                )
            time.sleep(0.5 * attempt)
            continue


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    args = _parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / "lexnorm_confidence_corrected.jsonl"
    
    # Load previously accepted records to skip them
    existing_accepted = {}
    if jsonl_path.exists():
        try:
            with jsonl_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("accepted") is True:
                            key = (record["video_id"], record["segment_number"])
                            existing_accepted[key] = record
                    except Exception:
                        pass
        except Exception:
            pass

    # Rewrite the file containing only the previously accepted records (clean up any rejected ones)
    if existing_accepted:
        with jsonl_path.open("w", encoding="utf-8") as f:
            for record in existing_accepted.values():
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"Loaded {len(existing_accepted)} previously accepted records. They will be skipped.")
    else:
        if jsonl_path.exists():
            jsonl_path.unlink()

    # Load paired segments
    pairs = pair_sherpa_soniox(args.sherpa_dir, args.soniox_dir)
    if args.limit is not None:
        pairs = pairs[: args.limit]

    print(f"Loaded {len(pairs)} pairs. Starting confidence-guided evaluation...")
    sys.stdout.flush()

    client = OllamaClient(base_url=args.ollama_base_url)

    # Khởi tạo danh sách Utterances để làm context
    lex_utterances = [
        Utterance(
            index=idx + 1,
            speaker=f"Speaker_{idx:03d}",
            start_time="",
            end_time="",
            text=pair.sherpa_transcript,
        )
        for idx, pair in enumerate(pairs)
    ]

    import threading
    from concurrent.futures import ThreadPoolExecutor

    # Hint Ollama server to allow parallel generations
    os.environ["OLLAMA_NUM_PARALLEL"] = str(args.max_workers)

    jsonl_lock = threading.Lock()
    results_by_idx = {}

    def process_one(idx: int) -> None:
        pair = pairs[idx]
        key = (pair.video_id, pair.segment_number)
        if key in existing_accepted:
            record = existing_accepted[key]
            results_by_idx[idx] = record
            print(f"[{idx+1}/{len(pairs)}] Cached: video={pair.video_id} seg={pair.segment_number} | accepted=True (Skipped)")
            sys.stdout.flush()
            return

        center = lex_utterances[idx]
        
        # Lấy context window (3 trước, 3 sau)
        start = max(0, idx - 3)
        end = min(len(lex_utterances), idx + 4)
        context = [u for u in lex_utterances[start:end] if u.index != center.index]

        # Trích lọc các token có độ tự tin thấp
        low_conf_words = []
        if pair.sherpa_tokens and pair.sherpa_confidences:
            for token, conf in zip(pair.sherpa_tokens, pair.sherpa_confidences):
                if conf < args.threshold:
                    clean_token = token.replace(" ", "").strip()
                    # Chỉ lấy các từ chứa ký tự chữ cái
                    if clean_token and re.match(r"^[a-zA-ZÀ-ỹ]+$", clean_token):
                        low_conf_words.append(f"'{clean_token}' ({int(conf * 100)}%)")

        low_conf_info = ", ".join(low_conf_words) if low_conf_words else ""
        
        res = correct_utterance_with_confidence(
            client=client,
            model=args.ollama_model,
            center=center,
            context_utterances=context,
            low_conf_info=low_conf_info
        )

        record = {
            "video_id": pair.video_id,
            "segment_number": pair.segment_number,
            "raw": res.raw_text,
            "truth": pair.soniox_transcript,
            "corrected": res.corrected_text,
            "accepted": res.accepted,
            "rejection_reason": res.rejection_reason,
            "model_run": res.model_run,
        }
        
        with jsonl_lock:
            _append_jsonl(jsonl_path, record)
            print(f"[{idx+1}/{len(pairs)}] Corrected: video={pair.video_id} seg={pair.segment_number} | accepted={res.accepted} | latency={res.model_run.get('latency_ms', 0)}ms")
            if low_conf_info:
                print(f"  Flagged low-conf tokens: {low_conf_info}")
            print(f"  ASR:   {res.raw_text}")
            print(f"  LLM:   {res.corrected_text}")
            sys.stdout.flush()

        results_by_idx[idx] = record

        # Thỉnh thoảng dọn cache mô hình (mỗi 10 phân đoạn)
        if (idx + 1) % 10 == 0:
            try:
                import requests
                requests.post(f"{args.ollama_base_url.rstrip('/')}/api/chat", json={"model": args.ollama_model, "keep_alive": 0}, timeout=5)
            except Exception:
                pass

    print(f"Running evaluation with {args.max_workers} workers...")
    sys.stdout.flush()

    started = time.time()
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        list(executor.map(process_one, range(len(pairs))))

    # Sắp xếp lại kết quả theo thứ tự gốc
    results = [results_by_idx[i] for i in range(len(pairs))]

    # 4. Đánh giá kết quả cuối cùng
    print("\n=== FINAL EVALUATION ===")
    raw_texts = [p.sherpa_transcript for p in pairs]
    truth_texts = [p.soniox_transcript for p in pairs]
    corrected_texts = [r["corrected"] for r in results]
    latency_values = [int(r["model_run"].get("latency_ms", 0)) for r in results]

    evaluator = LexnormEvaluator()
    metrics = evaluator.evaluate(
        raw_texts=raw_texts,
        corrected_texts=corrected_texts,
        truth_texts=truth_texts,
        latency_ms_values=latency_values,
    )

    print("\n--- RESULTS TABLE ---")
    print(f"| Method | WER | CER |")
    print(f"|---|---|---|")
    print(f"| Raw ASR (Sherpa) | {metrics['wer_raw']:.6f} | {metrics['cer_raw']:.6f} |")
    print(f"| Corrected (Confidence-Guided) | {metrics['wer_corrected']:.6f} | {metrics['cer_corrected']:.6f} |")
    print(f"| WER Delta | {metrics['wer_delta']:+.6f} (Better? {'Yes' if metrics['wer_delta'] < 0 else 'No'}) |")

    # Lưu metrics ra kết quả
    results_json_path = args.output_dir / "lexnorm_confidence_results.json"
    results_json_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved results to: {results_json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
