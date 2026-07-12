#!/usr/bin/env python3
import json
import os
import sys
import re
from pathlib import Path
from tqdm import tqdm
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_NAME = "tencent/Hy-MT2-1.8B"
BATCH_SIZE = 20  # Batch size 28 to use around 6.5GB VRAM and translate everything in one batch.

TRANSLATE_PROMPT = (
    "Translate the following text into Vietnamese. "
    "Note that you should **only output the translated result without any additional explanation**:\n\n"
    "{source_text}"
)

def clean_text(text):
    """Normalize text for matching: lowercase, remove non-alphanumeric, strip fillers and speaker tags."""
    text = re.sub(r'(?i)speaker\s+[a-z\d]:', ' ', text)
    text = re.sub(r'\{[a-zA-Z_]+\}', ' ', text)
    text = text.lower()
    words = re.findall(r'[a-z0-9]+', text)
    return words

def build_messages(source_text):
    return [
        {"role": "user", "content": TRANSLATE_PROMPT.format(source_text=source_text)}
    ]

def translate_batch(texts, model, tokenizer, device="cuda"):
    """Translate a batch of texts using Hy-MT2-1.8B."""
    prompts = []
    for text in texts:
        messages = build_messages(text)
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        prompts.append(prompt)

    inputs = tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=1024,  # Summaries can be long, so 1024 is safer.
    ).to(device)
    inputs.pop("token_type_ids", None)

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=512,  # Summaries might require up to 512 tokens.
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    input_lengths = inputs["input_ids"].shape[1]
    new_tokens = generated_ids[:, input_lengths:]
    results = tokenizer.batch_decode(new_tokens, skip_special_tokens=True)
    return [r.strip() for r in results]

def translate_with_oom_fallback(batch, model, tokenizer, device="cuda"):
    """Translates a list of texts, automatically reducing batch size on CUDA OOM."""
    if not batch:
        return []
    
    try:
        return translate_batch(batch, model, tokenizer, device=device)
    except torch.OutOfMemoryError as e:
        if device == "cuda":
            torch.cuda.empty_cache()
        if len(batch) <= 1:
            print(f"OOM error even with batch size 1! Text: {batch[0][:100]}...")
            raise e
        mid = len(batch) // 2
        print(f"\n[OOM] CUDA out of memory. Splitting batch of size {len(batch)} -> {mid} and {len(batch) - mid}...")
        first_half = translate_with_oom_fallback(batch[:mid], model, tokenizer, device=device)
        second_half = translate_with_oom_fallback(batch[mid:], model, tokenizer, device=device)
        return first_half + second_half
    except Exception as e:
        if "out of memory" in str(e).lower():
            if device == "cuda":
                torch.cuda.empty_cache()
            if len(batch) <= 1:
                raise e
            mid = len(batch) // 2
            print(f"\n[OOM] CUDA out of memory. Splitting batch of size {len(batch)} -> {mid} and {len(batch) - mid}...")
            first_half = translate_with_oom_fallback(batch[:mid], model, tokenizer, device=device)
            second_half = translate_with_oom_fallback(batch[mid:], model, tokenizer, device=device)
            return first_half + second_half
        else:
            raise e

def main():
    eval_file = Path("data/eval_vi/meeting_ami.json")
    test_file = Path("data/knkarthick_ami/test.json")

    if not eval_file.exists():
        print(f"Error: {eval_file} does not exist.")
        sys.exit(1)
    if not test_file.exists():
        print(f"Error: {test_file} does not exist.")
        sys.exit(1)

    print("Loading eval_vi/meeting_ami.json...")
    with open(eval_file, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    print("Loading knkarthick_ami/test.json...")
    test_data = []
    with open(test_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                test_data.append(json.loads(line))

    print(f"Total meetings in eval_vi/meeting_ami.json: {len(eval_data)}")
    print(f"Total meetings in knkarthick_ami/test.json: {len(test_data)}")
    print("-" * 60)

    # 1. Map test.json entries to eval_vi/meeting_ami.json entries using text similarity
    print("Finding matching entries...")
    eval_words_list = []
    for idx, item in enumerate(eval_data):
        # We can clean either 'utterances' or 'utterances_en' if present.
        # Let's use 'utterances_en' if it exists, otherwise 'utterances'
        ref_utts = item.get("utterances_en") or item.get("utterances")
        eval_text = " ".join(ref_utts)
        eval_words_list.append((idx, item["dial_id"], set(clean_text(eval_text))))

    # Match mappings
    matches = {} # test_idx -> (eval_idx, dial_id, similarity)
    for test_idx, test_item in enumerate(test_data):
        test_words = set(clean_text(test_item["dialogue"]))
        best_match_idx = -1
        best_match_dial_id = -1
        best_overlap_pct = 0.0
        
        for eval_idx, eval_dial_id, eval_words in eval_words_list:
            if not test_words or not eval_words:
                continue
            overlap = len(test_words & eval_words)
            pct = overlap / min(len(test_words), len(eval_words))
            if pct > best_overlap_pct:
                best_overlap_pct = pct
                best_match_idx = eval_idx
                best_match_dial_id = eval_dial_id

        if best_overlap_pct > 0.8:
            matches[test_idx] = (best_match_idx, best_match_dial_id, best_overlap_pct)
        else:
            print(f"Warning: Low similarity ({best_overlap_pct:.2f}) for test_idx={test_idx}")

    print(f"Mapped {len(matches)} out of {len(test_data)} test entries successfully.")

    # 2. Initialize the translation model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    print(f"Loading translation model: {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
    )
    model.eval()

    # 3. Translate in batches
    test_indices = list(matches.keys())
    summaries_to_translate = [test_data[i]["summary"] for i in test_indices]
    translated_summaries = []

    print("Translating summaries to Vietnamese...")
    for i in tqdm(range(0, len(summaries_to_translate), BATCH_SIZE)):
        batch = summaries_to_translate[i : i + BATCH_SIZE]
        translations = translate_with_oom_fallback(batch, model, tokenizer, device=device)
        translated_summaries.extend(translations)

    # 4. Write back to eval_vi/meeting_ami.json
    print("Updating eval_vi/meeting_ami.json with summaries...")
    
    # Initialize empty keys for all entries
    for item in eval_data:
        item["summary"] = None
        item["summary_vi"] = None

    # Populate matching entries
    for idx, test_idx in enumerate(test_indices):
        eval_idx, dial_id, _ = matches[test_idx]
        original_summary = summaries_to_translate[idx]
        vi_summary = translated_summaries[idx]
        
        eval_data[eval_idx]["summary"] = original_summary
        eval_data[eval_idx]["summary_vi"] = vi_summary

    # Safe atomic save
    temp_file = eval_file.with_suffix(".json.tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(eval_data, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, eval_file)

    print(f"Successfully saved updated data to {eval_file}")

if __name__ == "__main__":
    main()
