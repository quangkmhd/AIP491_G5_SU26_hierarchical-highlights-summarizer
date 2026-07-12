# ViT5 Chunk Summarizer — Fine-tune & Evaluation Report

> **Date**: 2026-07-10
> **Model**: `VietAI/vit5-base-vietnews-summarization` (T5-base, 226M params)
> **Task**: raw 8-utterance block → short Vietnamese summary
> **Goal**: replace the local Gemma GGUF teacher used in `generate_8u_summaries.py` with a fast on-device fine-tuned model

---

## TL;DR

We fine-tuned `VietAI/vit5-base-vietnews-summarization` to summarize
raw 8-utterance blocks in Vietnamese meeting transcripts. The model
was trained on 28,079 (block, summary) pairs from the
Alimeeting4MUG_vi corpus (targets generated previously by Gemma) and
evaluated on the dev split.

| Stage | ROUGE-1 | ROUGE-2 | ROUGE-L | Notes |
|---|---|---|---|---|
| **Val (best ckpt, 200 quick)** | 0.7316 | 0.4967 | **0.5559** | epoch 6, 200-sample quick eval |
| **Val (full 2,807 samples)** | 0.7302 | 0.4957 | 0.5574 | end-of-training full eval |
| **Dev benchmark (6,038 blocks)** | 0.7265 | 0.4854 | 0.5486 | held-out `dev_vi.jsonl` |

The fine-tuned ViT5 closely tracks the Gemma teacher style. Loss
clearly overfits after epoch 6, but R-1 keeps creeping up while
ROUGE-L plateaus — the early-stopping signal (best ROUGE-L = 0.5559
at step 4,740) correctly identified the right stopping point.

---

## Pipeline

```
data/Alimeeting4MUG_vi/train_vi.jsonl
  → for each chunk_summaries entry:
        - resolve raw sentences by [start_id, end_id] in content.sentences
        - format as "speaker: text\n..."  (input)
        - use the existing `summary` field as target
  → 90/10 random split (seed=42)
  → Seq2SeqTrainer (ROUGE-1/2/L, early stop on rougeL)
  → outputs/chunk_summarizer/vit5-chunk-summarizer-v1/  (model + tokenizer)
```

Scripts:
- `src/train/chunk_summarizer/finetune_chunk_summarizer.py` — training
- `src/train/chunk_summarizer/evaluate_chunk_summarizer.py` — benchmark
- `src/train/chunk_summarizer/data_utils.py` — shared data + tokenizer
- `src/train/chunk_summarizer/CLAUDE.md` — stable design decisions

CLI wrappers: `scripts/train_chunk_summarizer.sh`, `scripts/eval_chunk_summarizer.sh`.

---

## Dataset

- **Source**: `data/Alimeeting4MUG_vi/train_vi.jsonl` (295 records)
- **Block extraction**: 1-indexed `content.chunk_summaries[*]` with
  `start_id` / `end_id` ranges
- **Skip stats**: 0 missing sentences, 0 empty summaries, 0 empty
  formatted blocks — every (record, topic, block) triple became a
  training example
- **Examples**: 28,079 (one per chunk_summaries entry)
- **Split**: 25,272 train / 2,807 val (90/10, seed=42)
- **Per-epoch quick eval**: 200-sample random subset of the 2,807
  val (for speed; the full 2,807 is evaluated once at end of training)

### Token-length distribution (raw 8u block, spm)

| Stat | Value |
|---|---|
| Total blocks | 28,079 |
| Mean tokens | 137 |
| Median tokens | 132 |
| P95 tokens | 225 |
| P99 tokens | 296 |
| Max tokens | 2,045 |
| Overflow at 512 cap | 3 / 28,079 (0.01 %) |

→ `max_input_len=512` is plenty; only 3 blocks are truncated from
the right (most-recent context preserved).

### Target summary length

- Mean 175 chars (~50 tokens)
- Max 382 chars
- → `max_target_len=128` is a safe cap

---

## Training configuration

| Hyperparam | Value | Why |
|---|---|---|
| Base model | `VietAI/vit5-base-vietnews-summarization` | 226M, 512 ctx, already summarization-tuned on Vietnamese news |
| Optimizer | AdamW (HF default) | standard |
| Learning rate | **3e-4** | T5-family converges well at higher LR than BART |
| Weight decay | 0.01 | standard |
| Warmup ratio | 0.06 | standard |
| Per-device batch | **2** | constrained by 8 GB GPU; bs=4 OOMed |
| Gradient accumulation | 16 | effective batch = 32 |
| Epochs | 10 | cap; early stopping on ROUGE-L |
| Early stop patience | 5 | tracked by `EarlyStoppingCallback` |
| Precision | fp16 | half memory, sufficient for fine-tuning |
| Scheduler | linear | HF default with warmup |
| Best-model loading | `load_best_model_at_end=True` | on `metric_for_best_model="rougeL"` |
| Save strategy | `epoch`, `save_total_limit=2` | keeps best + latest |
| Generation (in-eval) | `num_beams=4`, `max_new_tokens=128`, `no_repeat_ngram_size=3` | matches vietnews-summarization style |
| Input prefix | `"Tóm tắt: "` | matches the original vietnews-summarization prompt style |

### Two-pass eval strategy

`eval_strategy="epoch"` with `predict_with_generate=True` and the full
2,807-sample val set takes ~47 min per call (beam-4 generation is
slow on 8 GB GPU). At 10 epochs that's 8 hours of just eval.

We instead:
1. Per-epoch eval on a **200-sample random subset** (~4 min) — the
   trainer tracks `rougeL` on this and picks the best checkpoint.
2. End-of-training eval on the **full 2,807-sample val** — this
   becomes the headline metric (`final_val_*`).

---

## Training progression

Per-epoch metrics on the 200-sample quick eval:

| Epoch | Loss  | R-1   | R-2   | R-L   | Note |
|------:|------:|------:|------:|------:|------|
| 1 | 0.9289 | 0.7017 | 0.4487 | 0.5190 | first epoch |
| 2 | 0.8085 | 0.7123 | 0.4660 | 0.5365 | |
| 3 | 0.7755 | 0.7168 | 0.4803 | 0.5418 | loss minimum |
| 4 | 0.7781 | 0.7244 | 0.4860 | 0.5502 | |
| 5 | 0.7935 | 0.7235 | 0.4897 | 0.5451 | |
| **6** | 0.8320 | 0.7316 | 0.4967 | **0.5559** | **best ROUGE-L** ← saved |
| 7 | 0.8977 | 0.7311 | 0.4905 | 0.5500 | overfit begins |
| 8 | 0.9731 | 0.7346 | 0.4995 | 0.5537 | |
| 9 | 1.0966 | 0.7330 | 0.4910 | 0.5467 | |
| 10 | 1.1964 | 0.7352 | 0.4968 | 0.5545 | loss doubled |

Observations:
- **Loss minimum at epoch 3** (0.7755) — after that the model
  starts overfitting (loss climbs steadily to 1.20 by epoch 10).
- **ROUGE-L peaks at epoch 6** (0.5559) — the early-stopping
  signal correctly identified this as the best checkpoint.
- **ROUGE-1 keeps creeping up** through all 10 epochs while
  ROUGE-L plateaus — the model is learning to use surface-level
  words but losing structural alignment. R-2 also peaks around
  epoch 6–8 then dips.

### End-of-training (full val)

After 10 epochs, the best-checkpoint weights are reloaded and the
**full 2,807-sample val set** is evaluated with beam-4 generation:

| Metric | Value |
|---|---|
| `final_val_loss` | 0.8174 |
| `final_val_rouge1` | 0.7302 |
| `final_val_rouge2` | 0.4957 |
| **`final_val_rougeL`** | **0.5574** |
| `final_val_rougeLsum` | 0.5574 |
| `final_val_gen_len` | 66.90 |
| `final_val_runtime` | 3,052 s ≈ 50.9 min |

The full-val ROUGE-L (0.5574) is essentially identical to the
quick-eval signal (0.5559) — the 200-sample subset was enough to
pick the right checkpoint.

---

## Dev benchmark (`dev_vi.jsonl`, 6,038 blocks, 65 records)

Dev benchmark results:

| Metric | Value |
|---|---|
| **Mean ROUGE-1** | 0.7265 |
| **Mean ROUGE-2** | 0.4854 |
| **Mean ROUGE-L** | 0.5486 |
| Median predicted summary tokens | 92 |
| Median input block tokens | 191 |
| Generation config | `num_beams=4, max_new_tokens=128, no_repeat_ngram_size=3, length_penalty=1.0` |

These scores are computed against the single reference summary per
block (Gemma-generated, 1 reference rather than 3 like
`topic_titler/evaluate`).

### Sample predictions (first record, first 3 blocks)

**Block 1** (R-1=0.7438, R-L=0.5785)

> **Input**: `no.0: Đúng vậy. no.0: Tôi nghĩ rằng TikTok có lẽ sẽ rất
> phổ biến, vì hiện nay mọi người đều xem TV, báo chí, tạp chí, ít
> hơn so với trước đây. no.0: Đúng vậy, chúng ta có thể tìm một số
> người nổi tiến...`
>
> **Reference**: *"Các thành viên thảo luận về tiềm năng của TikTok
> trong việc quảng bá sản phẩm dầu gội nhờ lượng người dùng lớn,
> đồng thời đề xuất sử dụng các video để quảng bá."*
>
> **Predicted**: *"Các thành viên thảo luận về tính phổ biến của
> TikTok và đề xuất tìm kiếm người nổi tiếng để quảng bá sản phẩm
> dầu gội, đồng thời nhận định rằng nền tảng này đang có nhiều
> người sử dụng."*

**Block 2** (R-1=0.6154, R-L=0.4615)

> **Input**: discusses Douyin ads, includes some Chinese fragments
> (`抖音的对现在是人最多的`)
>
> **Reference**: *"Các quảng cáo trên Douyin thường là những nội
> dung không được người dùng ưa chuộng nhưng lại có chi phí thấp
> hơn."*
>
> **Predicted**: *"Các thành viên thảo luận về các hình thức quảng
> cáo trên Douyin, nhận định rằng các nền tảng này thường rẻ hơn
> và được người tiêu dùng ưa chuộng."*

The predicted summary gets the gist right (Douyin ads) but **flips
the polarity** — reference says users *don't* like the ads, predicted
says they *do*. The reference is faithful to a sarcastic/literal
reading of the input; the predicted model summarizes the surface
discussion more naively. This is a known weakness of seq2seq
summarizers when input sentiment is implicit.

**Block 3** (R-1=0.8608, R-L=0.6835)

> **Input**: discussion of finding influencers on Douyin to advertise
> products, mentions Bawang brand
>
> **Reference**: *"Cuộc thảo luận xoay quanh việc tìm kiếm người có
> ảnh hưởng lớn trên Douyin để quảng cáo sản phẩm, nhưng một thành
> viên khác đã đề cập đến trường hợp sản phẩm Bawang được Trần
> Chính tài trợ và trở nên nổi tiếng nhanh chóng nhờ ảnh hưởng của
> các ngôi sao lớn."*
>
> **Predicted**: *"Các thành viên thảo luận về việc tìm kiếm những
> người có ảnh hưởng lớn trên Douyin để quảng cáo sản phẩm, đồng
> thời đề cập đến việc sàn sao Bawang của Trần Chính tài trợ đã
> trở nên nổi tiếng ngay lập tức."*

Near-perfect overlap (R-1=0.86). The model correctly identifies all
three key entities: Douyin, Bawang, and the influence-marketing
discussion. Minor paraphrasing: "ngay lập tức" vs. "nhanh chóng",
"sàn sao" vs. "ngôi sao".

---

## Resources

- **Wall-clock training time**: 4.5 hours (00:24 → 04:49 on 2026-07-10)
- **GPU**: 8 GB VRAM (RTX-class), bs=2 grad_accum=16, fp16
- **Disk**: 903 MB for the full `model.safetensors` (model only) —
  ~5.4 GB with the optimizer state in `checkpoint-7900/optimizer.pt`
- **Best checkpoint size**: ~5.4 GB on disk (with optimizer state);
  903 MB for inference-only weights
- **Inference speed**: ~1 sample/s with beam-4 (≈47 min for 2,807
  samples on the same hardware)

---
---

## Comparison with `topic_titler/`

This sub-project mirrors `src/train/topic_titler/`. Key differences:

| | `chunk_summarizer` | `topic_titler` |
|---|---|---|
| Base model | ViT5 (T5-base) | BARTpho (BART) |
| Model size | 226M | 132M |
| Context window | 512 | 1024 |
| Input | raw 8u transcript | concat of N block summaries |
| Output | block summary | topic title |
| Refs per example | 1 (Gemma) | 1 (longest candidate of 3) |
| Best rougeL | 0.5559 (epoch 6) | n/a (in progress) |
| Final rougeL | 0.5574 (full val) | n/a |

Both follow the same data flow:
`jsonl → build examples → HF Dataset → tokenize → 90/10 split → Seq2SeqTrainer → ROUGE-1/2/L → best ckpt`.

---

## Next steps (suggested)

1. **Use the fine-tuned model to re-summarize the corpus** — replace Gemma path with a 100x faster on-device ViT5 call to drop the GGUF dependency and produce summaries offline.

2. **Apply to `chunk_summaries` for the test split** — use the fine-tuned model to backfill the missing test split summaries.

3. **Hyperparam tuning** — investigate performance optimizations:
   - Add label smoothing (0.1)
   - Increase warmup ratio
   - Try a smaller LR (1e-4) to slow overfitting
   - Early stop at epoch 6 (3-epoch patience instead of 5)
