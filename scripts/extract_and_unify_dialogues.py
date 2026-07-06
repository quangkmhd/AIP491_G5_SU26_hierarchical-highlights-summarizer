#!/usr/bin/env python3
"""
Script trích xuất tất cả các cuộc hội thoại (dialogues/transcripts) từ 4 nguồn dataset:
MultiWOZ, KVRET, Taskmaster, và MetalWOZ.
Chuyển đổi tất cả về một định dạng JSON thống nhất (Unified Format) để dễ dàng gửi qua
AI mạng (Gemini, GPT) tóm tắt và đặt tiêu đề.
"""

import argparse
import glob
import json
import os
import sys

DATASETS_DIR = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/dialog_datasets/dialog_datasets"
OUTPUT_DIR = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/train"

def parse_args():
    parser = argparse.ArgumentParser(description="Extract and Unify Dialogues from TOD Datasets")
    parser.add_argument(
        "--output_file",
        type=str,
        default=os.path.join(OUTPUT_DIR, "unified_dialogues.json"),
        help="Đường dẫn lưu file JSON kết quả thống nhất",
    )
    parser.add_argument(
        "--max_per_dataset",
        type=int,
        default=None,
        help="Số lượng hội thoại tối đa trích xuất cho mỗi bộ dữ liệu (để tránh dung lượng file quá lớn, mặc định là trích xuất toàn bộ)",
    )
    return parser.parse_args()


def extract_multiwoz(datasets_dir, max_count=None):
    """Trích xuất từ MultiWOZ-2.1 data.json"""
    fpath = os.path.join(datasets_dir, "MultiWOZ-2.1", "data.json")
    if not os.path.exists(fpath):
        fpath = os.path.join(datasets_dir, "MultiWOZ-2.0", "data.json")
        
    if not os.path.exists(fpath):
        print(f"[Warning] Không tìm thấy dữ liệu MultiWOZ tại: {fpath}")
        return []

    print(f"Đang trích xuất MultiWOZ từ: {fpath}")
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    unified = []
    count = 0
    for dial_id, content in data.items():
        if max_count and count >= max_count:
            break

        # Log chứa lịch sử các turn
        log = content.get("log", [])
        if not log:
            continue

        dialogue_lines = []
        for idx, turn in enumerate(log):
            # Trong MultiWOZ, lượt chẵn thường là User, lượt lẻ là System/Agent
            speaker = "USER" if idx % 2 == 0 else "SYSTEM"
            text = turn.get("text", "").strip()
            if text:
                dialogue_lines.append(f"{speaker}: {text}")

        if not dialogue_lines:
            continue

        domains = content.get("domains", [])
        domain_str = ", ".join(domains) if isinstance(domains, list) else str(domains)

        unified.append({
            "dialogue_id": f"multiwoz_{dial_id.replace('.json', '')}",
            "dataset_name": "MultiWOZ-2.1",
            "domain": domain_str,
            "dialogue_text": "\n".join(dialogue_lines)
        })
        count += 1

    print(f"  -> Trích xuất thành công {len(unified)} hội thoại từ MultiWOZ.")
    return unified


def extract_kvret(datasets_dir, max_count=None):
    """Trích xuất từ KVRET (Stanford In-Car Assistant) public JSON files"""
    kvret_dir = os.path.join(datasets_dir, "kvret")
    if not os.path.exists(kvret_dir):
        print(f"[Warning] Không tìm thấy thư mục KVRET tại: {kvret_dir}")
        return []

    print(f"Đang trích xuất KVRET từ: {kvret_dir}")
    json_files = glob.glob(os.path.join(kvret_dir, "kvret_*.json"))
    # Loại trừ entities file
    json_files = [f for f in json_files if "entities" not in f]

    unified = []
    count = 0
    for fpath in json_files:
        if max_count and count >= max_count:
            break
            
        with open(fpath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"Lỗi khi đọc file {fpath}: {e}")
                continue

            for idx, session in enumerate(data):
                if max_count and count >= max_count:
                    break

                dialogue = session.get("dialogue", [])
                scenario = session.get("scenario", {})
                intent = scenario.get("task", {}).get("intent", "unknown")
                uuid = scenario.get("uuid", f"session_{idx}")

                dialogue_lines = []
                for turn in dialogue:
                    speaker = turn.get("turn", "unknown").upper()
                    text = turn.get("data", {}).get("utterance", "").strip()
                    if text:
                        dialogue_lines.append(f"{speaker}: {text}")

                if not dialogue_lines:
                    continue

                unified.append({
                    "dialogue_id": f"kvret_{uuid}",
                    "dataset_name": "KVRET",
                    "domain": intent,
                    "dialogue_text": "\n".join(dialogue_lines)
                })
                count += 1

    print(f"  -> Trích xuất thành công {len(unified)} hội thoại từ KVRET.")
    return unified


def extract_taskmaster(datasets_dir, max_count=None):
    """Trích xuất từ Taskmaster (TM-1-2019)"""
    tm_dir = os.path.join(datasets_dir, "Taskmaster", "TM-1-2019")
    if not os.path.exists(tm_dir):
        print(f"[Warning] Không tìm thấy thư mục Taskmaster tại: {tm_dir}")
        return []

    print(f"Đang trích xuất Taskmaster từ: {tm_dir}")
    json_files = [
        os.path.join(tm_dir, "self-dialogs.json"),
        os.path.join(tm_dir, "woz-dialogs.json"),
        os.path.join(tm_dir, "sample.json"),
    ]

    unified = []
    count = 0
    for fpath in json_files:
        if not os.path.exists(fpath):
            continue
        if max_count and count >= max_count:
            break

        with open(fpath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"Lỗi khi đọc file {fpath}: {e}")
                continue

            # Nếu là single object (như sample.json), bọc lại thành list
            if isinstance(data, dict):
                data = [data]

            for session in data:
                if max_count and count >= max_count:
                    break

                conv_id = session.get("conversation_id", "")
                domain = session.get("instruction_id", "unknown")
                utterances = session.get("utterances", [])

                dialogue_lines = []
                for turn in utterances:
                    speaker = turn.get("speaker", "unknown").upper()
                    text = turn.get("text", "").strip()
                    if text:
                        dialogue_lines.append(f"{speaker}: {text}")

                if not dialogue_lines:
                    continue

                unified.append({
                    "dialogue_id": f"taskmaster_{conv_id}",
                    "dataset_name": "Taskmaster-1",
                    "domain": domain,
                    "dialogue_text": "\n".join(dialogue_lines)
                })
                count += 1

    print(f"  -> Trích xuất thành công {len(unified)} hội thoại từ Taskmaster.")
    return unified


def extract_metalwoz(datasets_dir, max_count=None):
    """Trích xuất từ MetalWOZ (bao gồm cả các file zip vừa giải nén)"""
    metalwoz_dir = os.path.join(datasets_dir, "metalwoz")
    if not os.path.exists(metalwoz_dir):
        print(f"[Warning] Không tìm thấy thư mục MetalWOZ tại: {metalwoz_dir}")
        return []

    print(f"Đang trích xuất MetalWOZ từ: {metalwoz_dir}")
    
    # Quét tất cả các file .txt chứa dữ liệu dialogues trong metalwoz
    txt_files = glob.glob(os.path.join(metalwoz_dir, "**/*.txt"), recursive=True)
    
    unified = []
    count = 0
    for fpath in txt_files:
        if "tasks.txt" in fpath or "LOOK_UP_INFO.txt" in fpath:
            continue  # Bỏ qua file meta-data
        if max_count and count >= max_count:
            break

        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if max_count and count >= max_count:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    session = json.loads(line)
                except Exception:
                    continue

                conv_id = session.get("id", "")
                domain = session.get("domain", "unknown")
                turns = session.get("turns", [])

                dialogue_lines = []
                for idx, turn_text in enumerate(turns):
                    # Lượt chẵn là Agent/System, lượt lẻ là User
                    speaker = "SYSTEM" if idx % 2 == 0 else "USER"
                    text = turn_text.strip()
                    if text:
                        dialogue_lines.append(f"{speaker}: {text}")

                if not dialogue_lines:
                    continue

                unified.append({
                    "dialogue_id": f"metalwoz_{conv_id}",
                    "dataset_name": "MetalWOZ",
                    "domain": domain,
                    "dialogue_text": "\n".join(dialogue_lines)
                })
                count += 1

    print(f"  -> Trích xuất thành công {len(unified)} hội thoại từ MetalWOZ.")
    return unified


def main():
    args = parse_args()
    
    # Tạo thư mục output nếu chưa tồn tại
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

    all_unified = []
    
    # 1. MultiWOZ
    all_unified.extend(extract_multiwoz(DATASETS_DIR, args.max_per_dataset))
    
    # 2. KVRET
    all_unified.extend(extract_kvret(DATASETS_DIR, args.max_per_dataset))
    
    # 3. Taskmaster
    all_unified.extend(extract_taskmaster(DATASETS_DIR, args.max_per_dataset))
    
    # 4. MetalWOZ
    all_unified.extend(extract_metalwoz(DATASETS_DIR, args.max_per_dataset))

    print(f"\nTổng hợp tất cả các nguồn: {len(all_unified)} cuộc hội thoại.")
    
    # Ghi file kết quả
    print(f"Đang ghi dữ liệu thống nhất về: {args.output_file}")
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(all_unified, f, indent=2, ensure_ascii=False)
        
    print("Hoàn tất chuyển đổi dữ liệu thành công!")


if __name__ == "__main__":
    main()
