# 🛠 Operations & System Validation

This page documents how to operate, benchmark, evaluate, and troubleshoot the Hierarchical Meeting Recap System.

---

## 🏎 1. Running System Evaluations

To verify model performance and metrics against our target standards:

```bash
# General evaluation command to score topic segmentation against ground-truth indices
uv run python -m src.eval.run_segmentation_eval --corpus meeting_committee --data-root data/eval_vi
```

### Segmentation Quality Metrics
The system measures segmentation accuracy using three core metric calculations:

1.  **$P_k$ (Beeferman et al., 1999)**: Measures slide window disagreement probability. Lower is better. Our target baseline is $P_k \le 30.0$.
2.  **Win-Diff (Pevzner & Hearst, 2002)**: Evaluates segment boundaries by comparing window cuts. Lower is better.
3.  **F1-Score**: Measures overlapping accuracy between generated segments and human ground-truth divisions.

---

## 🐳 2. Dev & Validation Loop Scripts

```bash
# Fast, network-free suite (model doubles)
uv run pytest tests/ -q -m 'not real_model'

# Required CUDA checkpoint smoke test
uv run pytest tests/manual/test_local_recap_models_smoke.py -v -m real_model
```

Multiple specialized evaluation and tuning scripts live under the `/scripts` directory to support developer workflows:

```bash
# 1. Download Model Weights
# Pulls the localized Vietnamese models and places them under standard directories
./scripts/download_models.sh

# 2. Evaluate Coherence Scorer
# Scores transcripts using the fine-tuned FPTAI/vibert-base-cased checkpoint
uv run python scripts/eval_tool15_vibert.py

# 3. Fine-Tune BARTpho
# Performs model tuning iterations on the dialogue dataset and creates training checkpoints
uv run python scripts/finetune_bartpho_custom.py

# 4. Verify Baseline vs Evaluation Harness
# Compares your localized runs directly to the ground-truth targets stored under docs/generated
uv run python scripts/verify_real_vs_eval.py
```

---

## 🩺 3. Developer Diagnostics & Troubleshooting

### Actionable Error Structures
The system uses the `LoggableError` hierarchy to guarantee that server, model, or validator exceptions are accompanied by a human-friendly `fix` suggestion.

If you encounter an exception, look at the error log formatting. Example:
```
[src.service.orchestrator] ERROR: transcript has no utterances
  HINT: The orchestrator requires dialogue records to initialize TextTiling.
  FIX: Provide a TranscriptIngestionRequest with non-empty `utterances` or `flat_texts`!
```

### Common Resolutions

#### 1. Out of Memory (OOM) on CUDA
If both recap checkpoints cannot fit, free GPU memory and retry. The recap
runtime intentionally has no CPU fallback; loader errors include a `fix` hint.

#### 2. Local Tokenizer UNK Errors (The C4 Vocab Mismatch)
During initial setup, the pre-trained checkpoint `cpt_4000.pth` is hardwired to a 38,168-vocab Vietnamese-subset tokenizer. This is different in length from the standard 119,547-vocab multilingual tokenizer.
*   **System Action**: Under the hood, the system uses `_coerce_token_ids` inside `model_loader.py` to clamp out-of-vocabulary indices above 38,168 back to standard `0` (UNK).
*   **Resolution**: If coherence scores are flat-lining, verify that your text segments contain authentic Vietnamese phrasing, rather than corrupted Unicode arrays or pure symbols, as clamping degrades accuracy.
