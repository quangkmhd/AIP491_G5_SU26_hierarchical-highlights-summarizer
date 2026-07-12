#!/usr/bin/env python3
import json
import re
from pathlib import Path

def clean_text(text):
    """Normalize text for matching: lowercase, remove non-alphanumeric, strip fillers and speaker tags."""
    # Remove Speaker labels (e.g., 'Speaker A:')
    text = re.sub(r'(?i)speaker\s+[a-z\d]:', ' ', text)
    # Remove HF/AMI specific placeholders like {vocalsound}, {disfmarker}, {gap}
    text = re.sub(r'\{[a-zA-Z_]+\}', ' ', text)
    # Lowercase and keep only letters and numbers
    text = text.lower()
    words = re.findall(r'[a-z0-9]+', text)
    return words

def main():
    eval_file = Path("data/eval/meeting_ami.json")
    test_file = Path("data/knkarthick_ami/test.json")

    if not eval_file.exists():
        print(f"Error: {eval_file} does not exist.")
        return
    if not test_file.exists():
        print(f"Error: {test_file} does not exist.")
        return

    # Load eval dataset (JSON array)
    print("Loading eval/meeting_ami.json...")
    with open(eval_file, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    # Load knkarthick test dataset (JSON Lines)
    print("Loading knkarthick_ami/test.json...")
    test_data = []
    with open(test_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                test_data.append(json.loads(line))

    print(f"Total meetings in eval/meeting_ami.json: {len(eval_data)}")
    print(f"Total meetings in knkarthick_ami/test.json: {len(test_data)}")
    print("-" * 60)

    # Pre-clean eval data words
    eval_words_list = []
    for idx, item in enumerate(eval_data):
        eval_text = " ".join(item["utterances"])
        eval_words_list.append((idx, item["dial_id"], set(clean_text(eval_text))))

    # Match each test.json dialogue to eval_data
    matches = []
    print("Comparing dialogues to find matches...\n")
    for test_idx, test_item in enumerate(test_data):
        test_words = set(clean_text(test_item["dialogue"]))
        
        best_match_idx = -1
        best_match_dial_id = -1
        best_overlap_pct = 0.0
        
        for eval_idx, eval_dial_id, eval_words in eval_words_list:
            if not test_words or not eval_words:
                continue
            
            overlap = len(test_words & eval_words)
            # Similarity score: overlap relative to the smaller set
            pct = overlap / min(len(test_words), len(eval_words))
            
            if pct > best_overlap_pct:
                best_overlap_pct = pct
                best_match_idx = eval_idx
                best_match_dial_id = eval_dial_id

        matches.append({
            "test_idx": test_idx,
            "test_id": test_item["id"],
            "eval_idx": best_match_idx,
            "eval_dial_id": best_match_dial_id,
            "similarity": best_overlap_pct
        })
        
        print(f"Test item [{test_idx}] (id={test_item['id']}) matches "
              f"Eval item [{best_match_idx}] (dial_id={best_match_dial_id}) "
              f"with similarity score: {best_overlap_pct * 100:.2f}%")

    print("\n" + "=" * 60)
    print("SUMMARY OF MATCHING")
    print("=" * 60)
    matched_high = sum(1 for m in matches if m["similarity"] > 0.8)
    print(f"Total matched (similarity > 80%): {matched_high} / {len(test_data)}")

if __name__ == "__main__":
    main()
