#!/usr/bin/env python3
import os
import sys
import json
import yaml
import re
import argparse
import logging
import signal
from pathlib import Path
from tqdm import tqdm
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/generate_finetune_data.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs dir exists
os.makedirs("logs", exist_ok=True)

def parse_args():
    parser = argparse.ArgumentParser(description="Generate Title & Summaries for train_vi.json using Gemma-4 E4B GGUF")
    parser.add_argument(
        "--input_path",
        type=str,
        default="data/train/train_vi.json",
        help="Path to input train_vi.json"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="data/train/train_vi_processed.jsonl",
        help="Path to output processed jsonl"
    )
    parser.add_argument(
        "--prompts_yaml",
        type=str,
        default="prompt_fintune.yaml",
        help="Path to prompt_fintune.yaml"
    )
    parser.add_argument(
        "--model_path",
        type=str,
        default=None,
        help="Path to local GGUF model file (if specified, skips HF hub download)"
    )
    parser.add_argument(
        "--repo_id",
        type=str,
        default="unsloth/gemma-4-E4B-it-GGUF",
        help="HuggingFace GGUF Repo ID"
    )
    parser.add_argument(
        "--filename",
        type=str,
        default="gemma-4-E4B-it-Q4_K_M.gguf",
        help="GGUF Filename to download"
    )
    parser.add_argument(
        "--max_samples",
        type=int,
        default=None,
        help="Max samples to process (for testing)"
    )
    parser.add_argument(
        "--n_batch",
        type=int,
        default=1024,
        help="Batch size for prompt processing (GPU VRAM). Default 1024 for RTX 4060 8GB."
    )
    parser.add_argument(
        "--n_parallel",
        type=int,
        default=1,
        help="Number of parallel sequences. Default 1 (sequential)."
    )
    return parser.parse_args()

def clean_and_parse_json(text):
    """Robustly parse JSON from the LLM output."""
    cleaned = text.strip()
    
    # Remove markdown code block fences if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Regex to find JSON object structure
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        json_str = match.group(0)
        # Attempt to clean trailing commas
        json_str = re.sub(r',\s*\}', '}', json_str)
        json_str = re.sub(r',\s*\]', ']', json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.debug(f"Regex match parsing failed: {e}. String was: {json_str}")
            
    raise ValueError(f"Failed to parse JSON from text: {text}")

def load_prompts(prompts_yaml_path):
    """Load and clean prompt templates from the YAML file."""
    if not os.path.exists(prompts_yaml_path):
        logger.error(f"Prompts YAML file not found: {prompts_yaml_path}")
        sys.exit(1)
        
    with open(prompts_yaml_path, "r", encoding="utf-8") as f:
        prompts = yaml.safe_load(f)
        
    title_template = prompts.get("hierarchical_title", "")
    abstractive_template = prompts.get("hierarchical_abstractive", "")
    
    # Clean trailing commas in JSON schemas to prevent generation issues
    title_template = re.sub(r',\s*\}', '}', title_template)
    abstractive_template = re.sub(r',\s*\}', '}', abstractive_template)
    abstractive_template = re.sub(r',\s*\]', ']', abstractive_template)
    
    return title_template, abstractive_template

def format_utterances(dialogue_list):
    """Format dialogue utterances — chỉ lấy text_vi, không kèm nhãn speaker."""
    formatted = []
    for idx, turn in enumerate(dialogue_list):
        text = turn.get("text_vi", "").strip()
        formatted.append(text)
    return "\n".join(formatted)

def main():
    args = parse_args()
    
    # Determine the model path
    if args.model_path:
        gguf_path = args.model_path
        logger.info(f"Using local model path: {gguf_path}")
    else:
        logger.info(f"Downloading/loading GGUF model: {args.repo_id}/{args.filename}")
        logger.info("Checking/downloading model GGUF file from Hugging Face...")
        gguf_path = hf_hub_download(
            repo_id=args.repo_id,
            filename=args.filename
        )
    
    logger.info(f"Model file verified at: {gguf_path}")
    if not os.path.exists(gguf_path):
        logger.error(f"Model file does not exist at {gguf_path}")
        sys.exit(1)
        
    logger.info(f"Input path: {args.input_path}")
    logger.info(f"Output path: {args.output_path}")
    
    # Load prompts
    title_template, abstractive_template = load_prompts(args.prompts_yaml)
    
    # ── Initialize Llama model ────────────────────────────────────
    logger.info(
        f"Initializing Llama model with GPU acceleration: "
        f"n_gpu_layers=-1, n_batch={args.n_batch}, n_parallel={args.n_parallel}"
    )
    llm = Llama(
        model_path=gguf_path,
        n_gpu_layers=-1,        # Offload tất cả layers lên GPU
        n_ctx=4096,              # Context length đủ cho 8 utterances hoặc title toàn bộ
        n_batch=args.n_batch,    # Batch size cho prompt processing (tăng để dùng hết VRAM)
        n_ubatch=args.n_batch,   # Batch size cho evaluation (match n_batch)
        n_parallel=args.n_parallel,
        offload_kqv=True,        # Offload KQV cache lên GPU
        verbose=False,
        flash_attn=True          # Flash attention để giảm memory
    )
    logger.info("Llama model initialized successfully.")
    
    # ── Resume logic ──────────────────────────────────────────────
    processed_count = 0
    progress_file = args.output_path + ".progress"

    # Read progress file
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r") as pf:
                val = pf.read().strip()
                if val:
                    processed_count = int(val)
        except Exception as e:
            logger.warning(f"Cannot read progress file, starting from scratch: {e}")
            processed_count = 0

    # Sanity check: verify output file has exactly processed_count valid JSON lines
    if processed_count > 0 and os.path.exists(args.output_path):
        valid_lines = 0
        corrupt = False
        with open(args.output_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                    valid_lines += 1
                except json.JSONDecodeError:
                    corrupt = True
                    break  # stop at first corrupt line
        if corrupt or valid_lines < processed_count:
            logger.warning(f"Output file has {valid_lines} valid lines but progress says {processed_count}. "
                           f"Truncating progress to {valid_lines}.")
            processed_count = valid_lines
            # Rewrite progress file with corrected count
            with open(progress_file, "w") as pf:
                pf.write(str(processed_count))

    if processed_count > 0:
        logger.info(f"Resuming from sample {processed_count} (skipping already processed).")
            
    # Read input file
    if not os.path.exists(args.input_path):
        logger.error(f"Input file not found: {args.input_path}")
        sys.exit(1)
        
    with open(args.input_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        
    total_lines = len(lines)
    logger.info(f"Total dialogues in dataset: {total_lines}")
    
    # Apply max_samples limit if specified
    if args.max_samples is not None:
        total_lines = min(total_lines, args.max_samples)
        lines = lines[:total_lines]
        logger.info(f"Limiting execution to {total_lines} samples.")
        
    # ── Setup ──────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    
    system_prompt = (
        "Bạn là engine tạo meeting recap chuyên nghiệp. "
        "Luôn trả lời bằng tiếng Việt. Chỉ trả về JSON hợp lệ, không thêm giải thích."
    )

    # Biến global để signal handler access
    interrupted = False

    def signal_handler(signum, frame):
        nonlocal interrupted
        if not interrupted:
            logger.warning(f"Received signal {signum}, finishing current sample then exiting...")
            interrupted = True
        else:
            logger.warning("Double interrupt, force exiting...")
            sys.exit(1)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # ── Main processing loop ───────────────────────────────────────
    mode = "a" if processed_count > 0 else "w"
    with open(args.output_path, mode, encoding="utf-8") as out_f:
        for idx in tqdm(range(processed_count, total_lines), desc="Processing dialogues"):
            if interrupted:
                logger.info(f"Interrupted at sample {idx}. Progress saved.")
                break
            line = lines[idx]
            dialogue_obj = json.loads(line)
            dialogue_list = dialogue_obj.get("dialogue", [])
            
            if not dialogue_list:
                logger.warning(f"Empty dialogue at line {idx}, skipping.")
                dialogue_obj["title"] = "none"
                dialogue_obj["summary"] = []
                out_f.write(json.dumps(dialogue_obj, ensure_ascii=False) + "\n")
                out_f.flush()
                # Ghi progress cho empty dialogue để tránh lạc hậu
                _tmp = progress_file + ".tmp"
                with open(_tmp, "w") as pf:
                    pf.write(str(idx + 1))
                os.replace(_tmp, progress_file)
                continue
                
            # 1. Generate Title using entire dialogue
            segment_utts_str = format_utterances(dialogue_list)
            title_prompt = title_template.format(
                input_name=f"dialogue_{idx}",
                chapter_number=1,
                segment_utterances=segment_utts_str
            )
            
            try:
                response = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": title_prompt}
                    ],
                    max_tokens=256,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                generated_title_text = response["choices"][0]["message"]["content"].strip()
                title_data = clean_and_parse_json(generated_title_text)
                title = title_data.get("title", "none").strip()
            except Exception as e:
                logger.warning(f"Error generating title for line {idx}: {e}")
                title = "none"
                
            # 2. Generate Summary for each 8-utterance chunk
            chunk_summaries = []
            chunk_size = 8
            num_chunks = (len(dialogue_list) + chunk_size - 1) // chunk_size
            
            for chunk_idx in range(num_chunks):
                chunk_utts = dialogue_list[chunk_idx * chunk_size : (chunk_idx + 1) * chunk_size]
                chunk_id = f"chunk_{chunk_idx}"
                
                # Format chunk — chỉ lấy text_vi, không kèm nhãn speaker
                chunk_utts_str = []
                for turn_idx, turn in enumerate(chunk_utts):
                    text = turn.get("text_vi", "").strip()
                    chunk_utts_str.append(text)
                
                prompt_chunks_str = f"--- chunk_id: {chunk_id} ---\n" + "\n".join(chunk_utts_str)
                
                abs_prompt = abstractive_template.format(
                    input_name=f"dialogue_{idx}",
                    chapter_number=1,
                    example_chunk_id=chunk_id,
                    prompt_chunks=prompt_chunks_str
                )
                
                try:
                    response = llm.create_chat_completion(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": abs_prompt}
                        ],
                        max_tokens=256,
                        temperature=0.1,
                        response_format={"type": "json_object"}
                    )
                    generated_abs_text = response["choices"][0]["message"]["content"].strip()
                    abs_data = clean_and_parse_json(generated_abs_text)
                    notes = abs_data.get("notes", [])
                    if notes and isinstance(notes, list):
                        chunk_summary = notes[0].get("summary", "none").strip()
                    else:
                        chunk_summary = "none"
                except Exception as e:
                    logger.warning(f"Error generating summary for line {idx} chunk {chunk_idx}: {e}")
                    chunk_summary = "none"
                    
                chunk_summaries.append(chunk_summary)
                
            # Update the dialogue object with new fields
            dialogue_obj["title"] = title
            dialogue_obj["summary"] = chunk_summaries
            
            # Write output + update progress file atomically
            out_f.write(json.dumps(dialogue_obj, ensure_ascii=False) + "\n")
            out_f.flush()

            # Ghi progress file atomically (write to temp, rename)
            # để nếu bị kill giữa chừng, progress file luôn chỉ chứa index đã hoàn thành
            _tmp = progress_file + ".tmp"
            with open(_tmp, "w") as pf:
                pf.write(str(idx + 1))
            os.replace(_tmp, progress_file)

    logger.info("Preprocessing data generation completed.")

if __name__ == "__main__":
    main()
