# Ollama & Python RAM Optimization Guide for QMSum Evaluation

## Root Causes of RAM Spikes (92-93%)

### 1. Ollama `llama-server --no-mmap`
- Ollama server was launched with `--no-mmap`, which loads the ENTIRE model file into RAM
  (not memory-mapped from disk). A 3GB model can expand to 5-7GB in VRAM/RAM.
- **Fix**: Set `OLLAMA_FLASH_ATTENTION=1` and let ollama use mmap by default.
  If you can restart ollama serve, remove `--no-mmap` from its launch arguments.

### 2. Multiple Parallel Slots
- By default Ollama allocates KV cache for multiple parallel requests.
  Each 4096 context slot with a 4B model can consume 1-2GB extra RAM.
- **Fix**: `export OLLAMA_NUM_PARALLEL=1` (only 1 slot, minimal KV cache)

### 3. Model Staying Loaded (`keep_alive`)
- `OLLAMA_KEEP_ALIVE=10m` keeps the model + KV cache resident for 10 minutes after EACH request.
  During eval, this means the model NEVER unloads, RAM grows with fragmented KV caches.
- **Fix**: `export OLLAMA_KEEP_ALIVE=0s` — unload immediately after request completes.

### 4. Python Accumulating Results in Memory
- The eval script stores ALL results in `agg_results` list, keeping all generated text
  in Python memory. For 27 samples with long transcripts, this can grow to hundreds of MB.
- **Fix**: Write each sample result to disk (`per_sample/*.json`) immediately,
  do NOT accumulate in a Python list. Aggregate from disk at the very end.

### 5. Large Context Window
- Default `num_ctx=4096` creates large KV cache. The meeting transcripts can be very long,
  but for title/abstractive chunk prompts we only need ~2000-3000 context.
- **Fix**: Set `num_ctx=2048` in Ollama Modelfile or pass as parameter to reduce KV cache by half.

## Applied Fixes in `run_official_qmsum_full_eval_safe.py`

```python
os.environ["OLLAMA_NUM_PARALLEL"] = "1"
os.environ["OLLAMA_MAX_LOADED_MODELS"] = "1"
os.environ["OLLAMA_KEEP_ALIVE"] = "0s"
```

- Each sample is written to `per_sample/{name}.json` IMMEDIATELY after processing
- No in-memory accumulation of generated text
- Final aggregation reads from disk
- GC called after each sample

## How to Run (Low-RAM Mode)

```bash
# Stop existing ollama and restart WITHOUT --no-mmap if possible
ollama stop qwen3.5:4b-q4_K_M
# Or restart the whole service

# Run with low-RAM settings
OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_KEEP_ALIVE=0s \
  python3 eval/run_official_qmsum_full_eval_safe.py --memory-mode safe

# Monitor RAM in another terminal
watch -n 5 'free -m && ollama ps'
```

## Expected RAM Usage

| Component | Before | After (Optimized) |
|-----------|--------|-------------------|
| Ollama model loaded | 5-7GB (no-mmap) | 2-3GB (mmap) |
| KV cache (per slot) | 1-2GB × N slots | 0.5-1GB × 1 slot |
| Python objects | 500MB+ (accumulated) | <100MB (disk-only) |
| **Total** | **9-14GB (92%)** | **3-5GB (25-31%)** |