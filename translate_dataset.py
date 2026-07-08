import json
import os
import torch
import gc
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Configuration
INPUT_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/train/unified_raw_dialogues.json"
OUTPUT_FILE = "/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/train/unified_raw_dialogues_vi.jsonl"
MODEL_NAME = "vinai/vinai-translate-en2vi-v2"
# Target VRAM in bytes (7GB)
TARGET_VRAM = 7 * 1024 * 1024 * 1024 

def get_vram_usage():
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated()
    return 0

def load_data():
    print(f"Loading data from {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def get_processed_count():
    if not os.path.exists(OUTPUT_FILE):
        return 0
    count = 0
    print(f"Checking existing output file to resume...")
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for _ in f:
            count += 1
    print(f"Resuming from index {count}")
    return count

def translate_batch(model, tokenizer, texts, device):
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs, 
            max_length=256,
            num_beams=4,
            early_stopping=True,
            cache_implementation="static"
        )
    return tokenizer.batch_decode(outputs, skip_special_tokens=True)

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Load model and tokenizer
    print(f"Loading model {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, src_lang="en_XX")
    # Load in float16 to save memory and allow larger batch size
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float16).to(device)
    model.eval()

    data = load_data()
    start_idx = get_processed_count()

    # Initial batch size
    batch_size = 8
    
    # We will process one dialogue at a time, but batch the utterances inside it.
    # If a dialogue has many utterances, we chunk them into batch_size
    
    print(f"Starting translation targeting ~7GB VRAM limit...")
    
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f_out:
        for i in tqdm(range(start_idx, len(data)), desc="Translating dialogues"):
            dialogue = data[i]
            utterances = dialogue["utterances"]
            
            # Extract texts
            texts_to_translate = [utt["text"] for utt in utterances]
            translated_texts = []
            
            # Dynamic batching check
            current_vram = get_vram_usage()
            
            # Translate in batches
            for j in range(0, len(texts_to_translate), batch_size):
                batch_texts = texts_to_translate[j:j+batch_size]
                
                # Check VRAM before translation to adjust batch size if needed
                if current_vram < TARGET_VRAM * 0.8:
                    # We have plenty of room, could increase batch size, but for stability we keep it steady
                    # or slowly increase it up to a limit
                    if batch_size < 32:
                        batch_size += 2
                elif current_vram > TARGET_VRAM * 0.95:
                    # Getting close to limit, reduce batch size
                    batch_size = max(2, batch_size - 4)
                    torch.cuda.empty_cache()
                
                try:
                    translations = translate_batch(model, tokenizer, batch_texts, device)
                    translated_texts.extend(translations)
                except torch.cuda.OutOfMemoryError:
                    # If OOM, halve the batch size, clear cache, and try again item by item
                    print(f"\nOOM Error caught! Reducing batch size from {batch_size} to {batch_size // 2}")
                    batch_size = max(1, batch_size // 2)
                    torch.cuda.empty_cache()
                    gc.collect()
                    
                    # Fallback: process 1 by 1
                    for text in batch_texts:
                        translated_texts.extend(translate_batch(model, tokenizer, [text], device))

                current_vram = get_vram_usage()

            # Add translated text back to the object
            for utt, text_vi in zip(utterances, translated_texts):
                utt["text_vi"] = text_vi
            
            # Save the dialogue object as JSONL
            f_out.write(json.dumps(dialogue, ensure_ascii=False) + "\n")
            f_out.flush()
            
            # Periodically clear cache to prevent fragmentation
            if i % 100 == 0:
                torch.cuda.empty_cache()

    print("Translation completed!")

if __name__ == "__main__":
    main()
