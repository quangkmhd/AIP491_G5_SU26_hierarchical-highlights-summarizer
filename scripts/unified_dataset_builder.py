#!/usr/bin/env python3
"""
Script gom tất cả dữ liệu từ các bộ dataset hội thoại tiếng Anh trong dialog_datasets
vào một cấu trúc JSON thô thống nhất.
"""

import argparse
import glob
import json
import logging
import os
import sys
import csv
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_multiwoz(data_path, max_dials=None):
    """Parse dataset MultiWOZ 2.1."""
    dialogues = []
    if not os.path.exists(data_path):
        logger.warning(f"Không tìm thấy MultiWOZ tại: {data_path}")
        return dialogues

    logger.info(f"Đang parse MultiWOZ từ: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for dial_id, dial_data in data.items():
        if max_dials and count >= max_dials:
            break

        # Xác định topic thô
        topic = "general"
        goal = dial_data.get("goal", {})
        for domain, info in goal.items():
            if domain not in ["topic", "message"] and isinstance(info, dict) and info:
                topic = domain
                break

        # Trích xuất các câu thoại
        utterances = []
        for i, turn in enumerate(dial_data.get("log", [])):
            text = turn.get("text", "").strip()
            if not text:
                continue
            speaker = "USER" if i % 2 == 0 else "ASSISTANT"
            utterances.append({"speaker": speaker, "text": text})

        if utterances:
            dialogues.append({
                "dialogue_id": f"multiwoz_{dial_id}",
                "dataset_source": "multiwoz",
                "topic_title": topic,
                "utterances": utterances
            })
            count += 1

    logger.info(f"Đã parse thành công {len(dialogues)} hội thoại từ MultiWOZ.")
    return dialogues


def parse_kvret(dir_path, max_dials=None):
    """Parse dataset KVRET (Stanford In-Car Assistant)."""
    dialogues = []
    if not os.path.exists(dir_path):
        logger.warning(f"Không tìm thấy KVRET tại: {dir_path}")
        return dialogues

    logger.info(f"Đang parse KVRET từ: {dir_path}")
    json_files = glob.glob(os.path.join(dir_path, "kvret_*.json"))
    
    count = 0
    for file_path in json_files:
        if "entities" in file_path:
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            if max_dials and count >= max_dials:
                break

            dial_id = item.get("scenario", {}).get("uuid", f"kvret_dial_{count}")
            topic = item.get("scenario", {}).get("kb", {}).get("kb_title", "general")
            
            utterances = []
            for turn in item.get("dialogue", []):
                speaker = turn.get("turn", "").upper()
                if speaker == "DRIVER":
                    speaker = "USER"
                elif speaker == "ASSISTANT":
                    speaker = "ASSISTANT"
                else:
                    speaker = "USER"

                text = turn.get("data", {}).get("utterance", "").strip()
                if text:
                    utterances.append({"speaker": speaker, "text": text})

            if utterances:
                dialogues.append({
                    "dialogue_id": f"kvret_{dial_id}",
                    "dataset_source": "kvret",
                    "topic_title": topic,
                    "utterances": utterances
                })
                count += 1

    logger.info(f"Đã parse thành công {len(dialogues)} hội thoại từ KVRET.")
    return dialogues


def parse_taskmaster(dir_path, max_dials=None):
    """Parse dataset Taskmaster (TM-1-2019)."""
    dialogues = []
    if not os.path.exists(dir_path):
        logger.warning(f"Không tìm thấy Taskmaster tại: {dir_path}")
        return dialogues

    logger.info(f"Đang parse Taskmaster từ: {dir_path}")
    json_files = glob.glob(os.path.join(dir_path, "**/*.json"), recursive=True)
    
    count = 0
    for file_path in json_files:
        if "ontology" in file_path:
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                logger.error(f"Lỗi khi đọc file {file_path}: {e}")
                continue

            items = data if isinstance(data, list) else [data]

            for item in items:
                if max_dials and count >= max_dials:
                    break

                dial_id = item.get("conversation_id", f"tm_{count}")
                topic = item.get("instruction_id", "general")
                
                utterances = []
                for turn in item.get("utterances", []):
                    speaker = turn.get("speaker", "").upper()
                    if speaker not in ["USER", "ASSISTANT"]:
                        speaker = "USER"
                    
                    text = turn.get("text", "").strip()
                    if text:
                        utterances.append({"speaker": speaker, "text": text})

                if utterances:
                    dialogues.append({
                        "dialogue_id": f"taskmaster_{dial_id}",
                        "dataset_source": "taskmaster",
                        "topic_title": topic,
                        "utterances": utterances
                    })
                    count += 1

    logger.info(f"Đã parse thành công {len(dialogues)} hội thoại từ Taskmaster.")
    return dialogues


def parse_camrest(data_path, max_dials=None):
    """Parse dataset CamRest676."""
    dialogues = []
    if not os.path.exists(data_path):
        logger.warning(f"Không tìm thấy CamRest676 tại: {data_path}")
        return dialogues

    logger.info(f"Đang parse CamRest676 từ: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for i, item in enumerate(data):
        if max_dials and count >= max_dials:
            break

        dial_id = f"camrest_{i}"
        topic = "restaurant_reservation"
        
        utterances = []
        for turn in item.get("dial", []):
            usr_text = turn.get("usr", {}).get("transcript", "").strip()
            sys_text = turn.get("sys", {}).get("sent", "").strip()
            
            if usr_text:
                utterances.append({"speaker": "USER", "text": usr_text})
            if sys_text:
                utterances.append({"speaker": "ASSISTANT", "text": sys_text})

        if utterances:
            dialogues.append({
                "dialogue_id": dial_id,
                "dataset_source": "camrest",
                "topic_title": topic,
                "utterances": utterances
            })
            count += 1

    logger.info(f"Đã parse thành công {len(dialogues)} hội thoại từ CamRest676.")
    return dialogues


def parse_schema(dir_path, max_dials=None):
    """Parse Schema-Guided Dialogue dataset."""
    dialogues = []
    if not os.path.exists(dir_path):
        logger.warning(f"Không tìm thấy Schema tại: {dir_path}")
        return dialogues

    logger.info(f"Đang parse Schema từ: {dir_path}")
    json_files = glob.glob(os.path.join(dir_path, "**/*.json"), recursive=True)
    
    count = 0
    for file_path in json_files:
        if "schema.json" in file_path or "mapping.json" in file_path:
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

            for item in data:
                if max_dials and count >= max_dials:
                    break

                dial_id = item.get("dialogue_id", f"schema_{count}")
                services = item.get("services", ["general"])
                topic = services[0] if services else "general"
                
                utterances = []
                for turn in item.get("turns", []):
                    speaker = turn.get("speaker", "").upper()
                    if speaker == "SYSTEM":
                        speaker = "ASSISTANT"
                    elif speaker != "ASSISTANT":
                        speaker = "USER"
                        
                    text = turn.get("utterance", "").strip()
                    if text:
                        utterances.append({"speaker": speaker, "text": text})

                if utterances:
                    dialogues.append({
                        "dialogue_id": f"schema_{dial_id}",
                        "dataset_source": "schema",
                        "topic_title": topic,
                        "utterances": utterances
                    })
                    count += 1

    logger.info(f"Đã parse thành công {len(dialogues)} hội thoại từ Schema.")
    return dialogues


# --- CÁC PARSER MỚI BỔ SUNG ---

def parse_ccpe(data_path, max_dials=None):
    """Parse dataset CCPE-M-2019."""
    dialogues = []
    if not os.path.exists(data_path):
        logger.warning(f"Không tìm thấy CCPE tại: {data_path}")
        return dialogues

    logger.info(f"Đang parse CCPE từ: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for item in data:
        if max_dials and count >= max_dials:
            break

        dial_id = item.get("conversationId", f"ccpe_{count}")
        topic = "movie_recommendation"
        
        utterances = []
        for turn in item.get("utterances", []):
            speaker = turn.get("speaker", "").upper()
            if speaker not in ["USER", "ASSISTANT"]:
                speaker = "USER"
            
            text = turn.get("text", "").strip()
            if text:
                utterances.append({"speaker": speaker, "text": text})

        if utterances:
            dialogues.append({
                "dialogue_id": f"ccpe_{dial_id}",
                "dataset_source": "ccpe",
                "topic_title": topic,
                "utterances": utterances
            })
            count += 1

    logger.info(f"Đã parse thành công {len(dialogues)} hội thoại từ CCPE.")
    return dialogues


def parse_e2e_challenge(dir_path, max_dials=None):
    """Parse dataset e2e_dialog_challenge từ các file .tsv."""
    dialogues = []
    if not os.path.exists(dir_path):
        logger.warning(f"Không tìm thấy e2e_dialog_challenge tại: {dir_path}")
        return dialogues

    logger.info(f"Đang parse e2e_dialog_challenge từ: {dir_path}")
    tsv_files = glob.glob(os.path.join(dir_path, "**/*_all.tsv"), recursive=True)
    
    count = 0
    for file_path in tsv_files:
        topic = "general"
        filename = os.path.basename(file_path)
        if "taxi" in filename:
            topic = "taxi_booking"
        elif "restaurant" in filename:
            topic = "restaurant_reservation"
        elif "movie" in filename:
            topic = "movie_booking"

        # Đọc file TSV và gom nhóm theo session.ID
        session_turns = {}
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                session_id = row.get("session.ID")
                if not session_id:
                    continue
                
                speaker = row.get("Message.From", "user").upper()
                if speaker not in ["USER", "ASSISTANT"]:
                    speaker = "ASSISTANT" if speaker == "AGENT" else "USER"
                
                text = row.get("Message.Text", "").strip()
                if text:
                    if session_id not in session_turns:
                        session_turns[session_id] = []
                    session_turns[session_id].append({"speaker": speaker, "text": text})

        for session_id, utterances in session_turns.items():
            if max_dials and count >= max_dials:
                break

            dialogues.append({
                "dialogue_id": f"e2e_{topic}_{session_id}",
                "dataset_source": "e2e_challenge",
                "topic_title": topic,
                "utterances": utterances
            })
            count += 1

    logger.info(f"Đã parse thành công {len(dialogues)} hội thoại từ e2e_dialog_challenge.")
    return dialogues


def parse_metalwoz(dir_path, max_dials=None):
    """Parse dataset metalwoz (JSON Lines txt files)."""
    dialogues = []
    if not os.path.exists(dir_path):
        logger.warning(f"Không tìm thấy metalwoz tại: {dir_path}")
        return dialogues

    logger.info(f"Đang parse metalwoz từ: {dir_path}")
    txt_files = glob.glob(os.path.join(dir_path, "**/*.txt"), recursive=True)
    
    count = 0
    for file_path in txt_files:
        if max_dials and count >= max_dials:
            break

        # Đọc từng dòng JSONL
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if max_dials and count >= max_dials:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                
                dial_id = item.get("id", f"metalwoz_{count}")
                topic = item.get("domain", "general").lower()
                
                utterances = []
                # turns là list các câu thoại xen kẽ (chẵn: ASSISTANT, lẻ: USER)
                for i, text in enumerate(item.get("turns", [])):
                    text = text.strip()
                    if text:
                        speaker = "ASSISTANT" if i % 2 == 0 else "USER"
                        utterances.append({"speaker": speaker, "text": text})
                
                if utterances:
                    dialogues.append({
                        "dialogue_id": f"metalwoz_{dial_id}",
                        "dataset_source": "metalwoz",
                        "topic_title": topic,
                        "utterances": utterances
                    })
                    count += 1

    logger.info(f"Đã parse thành công {len(dialogues)} hội thoại từ metalwoz.")
    return dialogues


def parse_frames(data_path, max_dials=None):
    """Parse dataset frames.json."""
    dialogues = []
    if not os.path.exists(data_path):
        logger.warning(f"Không tìm thấy frames.json tại: {data_path}")
        return dialogues

    logger.info(f"Đang parse frames.json từ: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for item in data:
        if max_dials and count >= max_dials:
            break

        dial_id = item.get("id", f"frames_{count}")
        topic = "travel_booking"
        
        utterances = []
        for turn in item.get("turns", []):
            author = turn.get("author", "user").upper()
            speaker = "ASSISTANT" if author == "WIZARD" else "USER"
            
            text = turn.get("text", "").strip()
            if text:
                utterances.append({"speaker": speaker, "text": text})

        if utterances:
            dialogues.append({
                "dialogue_id": f"frames_{dial_id}",
                "dataset_source": "frames",
                "topic_title": topic,
                "utterances": utterances
            })
            count += 1

    logger.info(f"Đã parse thành công {len(dialogues)} hội thoại từ frames.")
    return dialogues


def main():
    parser = argparse.ArgumentParser(description="Gom tất cả các bộ dataset hội thoại tiếng Anh")
    parser.add_argument(
        "--datasets_dir",
        type=str,
        default="/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/dialog_datasets/dialog_datasets",
        help="Đường dẫn đến thư mục chứa các dataset gốc",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/train/unified_raw_dialogues.json",
        help="File JSON đầu ra chứa dữ liệu gom thống nhất",
    )
    parser.add_argument(
        "--max_dialogues_per_dataset",
        type=int,
        default=None,
        help="Số lượng hội thoại tối đa để parse từ mỗi dataset (dùng cho test/demo)",
    )
    args = parser.parse_args()

    all_dialogues = []

    # 1. Parse MultiWOZ-2.1
    multiwoz_path = os.path.join(args.datasets_dir, "MultiWOZ-2.1", "data.json")
    all_dialogues.extend(parse_multiwoz(multiwoz_path, args.max_dialogues_per_dataset))

    # 2. Parse KVRET
    kvret_dir = os.path.join(args.datasets_dir, "kvret")
    all_dialogues.extend(parse_kvret(kvret_dir, args.max_dialogues_per_dataset))

    # 3. Parse Taskmaster (TM-1-2019)
    taskmaster_dir = os.path.join(args.datasets_dir, "Taskmaster", "TM-1-2019")
    all_dialogues.extend(parse_taskmaster(taskmaster_dir, args.max_dialogues_per_dataset))

    # 4. Parse CamRest676
    camrest_path = os.path.join(args.datasets_dir, "CamRest676", "CamRest676.json")
    all_dialogues.extend(parse_camrest(camrest_path, args.max_dialogues_per_dataset))

    # 5. Parse Schema-Guided Dialogue
    schema_dir = os.path.join(args.datasets_dir, "Schema")
    all_dialogues.extend(parse_schema(schema_dir, args.max_dialogues_per_dataset))

    # 6. Parse CCPE-M-2019
    ccpe_path = os.path.join(args.datasets_dir, "CCPE-M-2019", "data.json")
    all_dialogues.extend(parse_ccpe(ccpe_path, args.max_dialogues_per_dataset))

    # 7. Parse e2e_dialog_challenge
    e2e_dir = os.path.join(args.datasets_dir, "e2e_dialog_challenge", "data")
    all_dialogues.extend(parse_e2e_challenge(e2e_dir, args.max_dialogues_per_dataset))

    # 8. Parse metalwoz
    metalwoz_dir = os.path.join(args.datasets_dir, "metalwoz", "dialogues")
    all_dialogues.extend(parse_metalwoz(metalwoz_dir, args.max_dialogues_per_dataset))

    # 9. Parse frames.json
    frames_path = os.path.join(args.datasets_dir, "frames.json")
    all_dialogues.extend(parse_frames(frames_path, args.max_dialogues_per_dataset))

    if not all_dialogues:
        logger.error("Không parse được bất kỳ hội thoại nào. Vui lòng kiểm tra lại đường dẫn dataset gốc.")
        sys.exit(1)

    # Đảm bảo thư mục đầu ra tồn tại
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

    logger.info(f"Đang ghi tổng cộng {len(all_dialogues)} hội thoại vào file: {args.output_file}")
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(all_dialogues, f, ensure_ascii=False, indent=2)

    logger.info("Hoàn tất gom dữ liệu thô thành công!")


if __name__ == "__main__":
    main()
