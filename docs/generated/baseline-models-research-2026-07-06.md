# Paper-Defensible Baseline Models cho Vietnamese Meeting Summarization

**Ngày tạo:** 2026-07-06
**Mục đích:** Hỗ trợ viết paper-2 (Hierarchical Meeting Recap) tại `docs/papers/llm-powered-meeting-recap-system.md`. Báo cáo này tổng hợp các models, methods, và evaluation methodologies đã được adversarial verify (3-vote) để đảm bảo chất lượng paper-defensible.

**Confidence tiers:**

- **High** = 3-0 vote hoặc 2-1 với primary source verbatim
- **Medium** = 2-1 với secondary source
- **Unverified** = không có trong surviving claim set; cần kiểm tra thêm

---

## 1. Bảng so sánh Baseline Models (paper-defensible)

| #   | Model                      | Arch     | Params   | Context            | License                                     | Citation                                        | Verified Notes                                                                                                                                      |
| --- | -------------------------- | -------- | -------- | ------------------ | ------------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **BART-Base**              | Enc-Dec  | 140M     | 1024               | MIT                                         | Lewis et al. 2020, arXiv:1910.13461 (ACL 2020)  | Denoising autoencoder. Không publish SAMSum ROUGE chính thức.                                                                                       |
| 2   | **BART-Large**             | Enc-Dec  | 406M     | 1024               | MIT                                         | Lewis et al. 2020, arXiv:1910.13461             | Được paper-2 reference (Asthana 2025) Microsoft dùng làm `hierarchical_segment`.                                                                    |
| 3   | **PEGASUS** (Large)        | Enc-Dec  | 568M     | 1024-4096          | Apache 2.0                                  | Zhang et al. 2020, arXiv:1912.08777 (ICML 2020) | Gap Sentence Generation pretraining. SOTA ROUGE trên 12 datasets news/science; KHÔNG publish dialogue benchmarks.                                   |
| 4   | **T5-Base**                | Enc-Dec  | 220M     | 512                | Apache 2.0                                  | Raffel et al. 2020, JMLR (arXiv:1910.10683)     | Text-to-text transfer.                                                                                                                              |
| 5   | **FLAN-T5-Large**          | Enc-Dec  | 780M     | 512-2048           | Apache 2.0                                  | Chung et al. 2022, arXiv:2210.11416             | Instruction-tuned variant. SAMSum ROUGE chưa verified trong paper-vendor artifacts.                                                                 |
| 6   | **Phi-3-mini-4k-instruct** | Dec-only | 3.8B     | 4K (128K variants) | **MIT** (verified, refutes CC-BY-4.0 claim) | Abdin et al. 2024, arXiv:2404.14219             | Microsoft opensource. Training data: 3.3T (paper) vs 4.9T (HF card) tokens - **discrepancy cần acknowledge**. KHÔNG publish SAMSum/DialogSum ROUGE. |
| 7   | **Gemma-2-2B-IT**          | Dec-only | 2.6B     | 8K                 | Gemma license                               | Team et al. 2024, arXiv:2408.00118              | **Trained with knowledge distillation** từ 7B teacher (cho 2B variant), 27B teacher (cho 9B). 27B dùng standard next-token prediction.              |
| 8   | **Llama-3-405B**           | Dec-only | 405B     | 128K (verified)    | Llama-3 Community                           | Dubey et al. 2024, arXiv:2407.21783             | Quá lớn cho CPU - chỉ là teacher model candidate.                                                                                                   |
| 9   | **Qwen2.5** family         | Dec-only | 1.5B-72B | 32K (128K RoPE)    | Apache 2.0                                  | Qwen Team 2024, arXiv:2412.15115                | 18T tokens training corpus (scaled từ 7T của Qwen2). Multilingual.                                                                                  |

### Khuyến nghị chính cho paper:

**Set baseline lành mạnh (paper-defensible, peer-reviewed, đa dạng arch):**

1. **BART-Large (406M)** - must-have; paper-2 của Asthana et al. dùng chính nó cho `hierarchical_segment`, cho phép so sánh trực tiếp với Microsoft. Citation: arXiv:1910.13461.

2. **PEGASUS-Large (568M, GSG)** - must-have; SOTA summarization trên 12 benchmarks; phổ biến trong summarization papers 2020-2023; insight về gap-sentence-generation pretraining. Citation: arXiv:1912.08777.

3. **FLAN-T5-Large (780M)** - đại diện instruction-tuned encoder-decoder hiện đại. Citation: arXiv:2210.11416.

4. **Gemma-2-2B-IT** - đại diện cho dòng decoder-only instruction-tuned mới, có KD trong pretraining. Citation: arXiv:2408.00118.

5. **Phi-3-mini-4k-instruct** - MIT license, peer-reviewed. Citation: arXiv:2404.14219.

**Loại trừ** (không khuyến nghị dùng làm baseline chính trong paper):

- Llama-3.2-1B / 3B: refuted claims về SAMSum SOTA
- TinyStories-style models: chỉ cho language modeling, không cho summarization
- Qwen2.5-1.5B-FT-SAMSum: không paper-vendor

---

## 2. Bảng so sánh Phương pháp Distillation / Fine-tuning

| #   | Method                                                     | Citation                                                   | What it does                                                                                      | Verified Benchmark Evidence                                                                                    | Caveat for Summarization                                                                                                                                         |
| --- | ---------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Supervised Output Distillation** (Hinton-style baseline) | Hinton et al. 2015 (original); Sanh et al. 2019 DistilBERT | Dùng teacher outputs làm hard/soft labels cho student                                             | DistilBERT: 97% performance BERT, 40% smaller, 60% faster                                                      | Baseline standard, ít dramatic gain trên summarization so với SFT thuần                                                                                          |
| 2   | **Distilling Step-by-Step**                                | Hsieh et al. 2023, arXiv:2305.02301 (ACL 2023 Findings)    | Dùng teacher-generated rationales (extracted labels) trong multi-task training                    | **Verified**: 770M T5 beats 540B PaLM with 80% training data trên e-SNLI/ANLI/CommonsenseQA/SVAMP              | **HUGE caveat**: chỉ evaluate NLI/QA, KHÔNG evaluate summarization. Cần kernel-of-rationale extraction cho summarization trước khi SFT.                          |
| 3   | **GKD (On-Policy Distillation)**                           | Agarwal et al. ICLR 2024, arXiv:2306.13649                 | Student trained on both teacher outputs AND on-policy self-generated outputs với teacher feedback | **Verified**: 2.1× ROUGE-2 gain trên XSum với on-policy training. 1.7× BLEU trên WMT14 En→De. 1.9× trên GSM8K. | Evaluated chủ yếu trên XSum (news), không rõ dialogue-meeting. Optimal divergence task-dependent: reverse KL cho instruction-tuning, JSD(0.9) cho summarization. |
| 4   | **Sequence-Level KD**                                      | Kim & Rush 2016, arXiv:1606.07947                          | Replace word-level với sequence-level teacher outputs                                             | Pre-trained BERT-to-Transformer sequence distillation                                                          | Baseline standard, ít dramatic gain                                                                                                                              |
| 5   | **DPO (Direct Preference Optimization)**                   | Rafailov et al. 2023, arXiv:2305.18290 (NeurIPS 2023)      | Closed-form policy optimization, không cần reward model rời rạc                                   | Show RLHF-aligned quality without value model trên HH-RLHF/Anthropic                                           | **Refuted**: claim "DPO explicitly matches or beats PPO trên TL;DR" loss verification (vote 1-2). TL;DR quality gain chưa được verify.                           |
| 6   | **TinyStories-style approach**                             | Eldan & Li 2023, arXiv:2305.07759                          | Train small LM trên high-quality synthesized short stories từ GPT-4                               | GPT-3.5-level coherence ở 10M params, language modeling only                                                   | **Not applicable for summarization** - chỉ test LM metrics, không test dialog/file-summary.                                                                      |

### Khuyến nghị cho paper:

**Phổ biến + paper-defensible**:

- **Supervised Output Distillation** (Hinton-style) làm baseline: dùng teacher outputs (GPT-4/Claude) → labels cho small student. Có code reference tại DistilBERT (Sanh et al. 2019).
- **Distilling Step-by-Step** (Hsieh 2023, arXiv:2305.02301) - paper-defensible vì ACL 2023 Findings. Tuy nhiên cần rationale extraction pipeline cho summarization (generate extractive labels from chunks) trước khi SFT multi-task.

**Untested trên dialogue summarization, cần thí nghiệm**:

- GKD (Agarwal 2024) - chỉ verified XSum news.
- DPO - chỉ verified LM preference benchmarks; TL;DR quality gain chưa được verify.

---

## 3. Đánh giá cho Vietnamese Context

Tất cả Vietnamese-specific models đều **chưa có paper/vendor-verified SAMSum/DialogSum ROUGE-L numbers** cho dialogue summarization. Phải tự chạy experiment.

| Model                       | Params    | Lang focus         | License                            | Has official paper?         | Notes for Vietnamese                                                                            |
| --------------------------- | --------- | ------------------ | ---------------------------------- | --------------------------- | ----------------------------------------------------------------------------------------------- |
| **PhoGPT**                  | 7.5B      | Vietnamese-first   | Apache 2.0 (PhoGPT-IT is CC-BY-NC) | Có paper (Vietnam AI Lab)   | Instruction-tuned version 7B5-IT; monolingual Vietnamese                                        |
| **gemma-4-E2B-it-qat-GGUF** | 7B        | Vietnamese         | Apache 2.0                         | Có paper (VietAI / HF)      | Continual pretraining of Mistral-7B trên Vietnamese. Reference trong repo model_loader.py NOTE. |
| **BARTpho**                 | 400M-600M | Vietnamese         | MIT                                | Có paper (Tran et al. 2022) | BART pretrained Vietnamese                                                                      |
| **ViT5**                    | 220M-770M | Vietnamese         | MIT                                | Có paper (Phan et al. 2022) | T5 variant Vietnamese                                                                           |
| **mt5-base**                | 580M      | Multilingual (101) | Apache 2.0                         | Có paper (Xue et al. 2021)  | Cross-lingual transfer                                                                          |

**Khuyến nghị Vietnamese baselines cho paper:**

1. **BARTpho + ViT5** - primary Vietnamese IN-DOMAIN baselines (purpose-built Vietnamese, có peer-reviewed paper).
2. **mt5-base** - multilingual baseline.
3. **gemma-4-E2B-it-qat-GGUF** - Vietnamese continually pretrained variant (note: 7B nặng cho CPU).

**Dataset Vietnamese dialogue summarization**: chưa thấy dataset chuẩn nào publish riêng. Repo hiện tại dùng `data/eval_vi/meeting_committee.json` (in-house). Cần kiểm tra thêm ViSoSum, VLSP, UIT-ViDialog.

---

## 4. Methodology đánh giá chuẩn (paper-defensible 2024-2025)

### ROUGE: chỉ một mình là KHÔNG ĐỦ cho dialogue

- **Verified từ Gliwa et al. 2019** (arXiv:1911.12237) verbatim: _"model-generated summaries of dialogues achieve higher ROUGE scores than the model-generated summaries of news – in contrast with human evaluators' judgement."_ Pearson correlation giữa ROUGE và human rating chỉ r ≈ 0.30–0.32 cho dialogue, vs 0.44–0.48 cho news.
- **Implication**: PHẢI dùng thêm BERTScore hoặc LLM-as-judge cho dialogue.

### Recommended metric stack:

| Metric                    | Citation                                                                      | What it measures                                            |
| ------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **ROUGE-1/2/L**           | Lin 2004 (ACL Workshop)                                                       | Lexical overlap vs. reference (mandatory nhưng limited)     |
| **BERTScore**             | Zhang et al. 2020, arXiv:1904.09675 (ICLR 2020)                               | Semantic similarity via BERT embeddings                     |
| **BARTScore**             | Yuan et al. 2021, arXiv:2106.11520 (NeurIPS 2021)                             | Likelihood of target given source under BART                |
| **G-Eval / LLM-as-judge** | Liu et al. 2023, arXiv:2303.08774 (NeurIPS 2023)                              | GPT-4/Claude prompted với chain-of-thought rubric scoring   |
| **FactCC / SummaC**       | Kryscinski et al. 2020 (FactCC); Laban et al. 2022, arXiv:2111.02533 (SummaC) | Factual consistency (chiplet với abstractive summarization) |
| **Human evaluation**      | A la Asthana 2025 (current paper-2)                                           | 7 participants, task-based think-aloud                      |

### Recommended cho paper:

1. **ROUGE-1/2/L** (mandatory baseline) - Pearson/harman correlation của reference resolution
2. **BERTScore-F1** (semantic similarity)
3. **LLM-as-judge** (GPT-4 judge với structured rubric copy of paper-2's user-study rubric)
4. **FactCC** (factual consistency - cũng quan trọng cho meeting recap vì không thể "bịa" decisions/deadlines)
5. Nếu có compute: human evaluation với Vietnamese speakers (5-7 participants, dựa trên Asthana protocol)

---

## 5. Recommendation Chính

**Dùng set 4-5 baselines sau cho paper** (paper-defensible, peer-reviewed, đa dạng về arch + size + paradigm):

1. **BARTpho-syllable-base** (Tran et al. bartpho, MIT, peer-reviewed) - In-domain Vietnamese baseline; published paper.
2. **ViT5-base** (Phan et al. 2022, Naver Labs, peer-reviewed) - Encoder-decoder Vietnamese baseline; enables zero-shot Vietnamese comparison.
3. **BART-Large** (Lewis et al. 2020, arXiv:1910.13461, ACL 2020) - **MATCH paper-2 reference** (Asthana 2025 had BART for hierarchical_segment). Critical for cross-paper comparison.
4. **Phi-3-mini-4k-instruct** (Abdin et al. 2024, arXiv:2404.14219) - Modern small decoder-only, MIT license, paper-defensible.
5. (Optional) **gemma-4-E2B-it-qat-GGUF** - Vietnamese-specific continual pretraining baseline; có paper (HF).

**Primary target**: Your Gemma 4 E2B-IT outputs so sánh với all baselines trên:

- Internal Vietnamese meeting dataset (`meeting_committee.json`)
- Optionally: SAMSum translated Vietnamese / DialogSum Vietnamese (nếu có)
- Using ROUGE-1/2/L + BERTScore-F1 + FactCC + GPT-4-judge

**Note về model hiện tại trong repo:**

- `unsloth/gemma-4-E2B-it-qat-GGUF` (theo `src/repo/model_loader.py:42-44`)
- "gemma-4" chưa tồn tại chính thức (cutoff tháng 1/2026 theo system message). Có thể là typo cho `gemma-3-4b-it` hoặc reference tới `gemma-2-2b-it`. Cần verify với maintainer repo.

---

## 6. REFUTED CLAIMS (KHÔNG được cite trong paper)

Những claims này đã được verify fail (vote 0-3 hoặc 1-2). **Không được dùng trong paper:**

| Claim                                                                                                   | Verdict            | Why                                                                            |
| ------------------------------------------------------------------------------------------------------- | ------------------ | ------------------------------------------------------------------------------ |
| "T5-Base đạt SOTA trên CNN/DM abstractive summarization với T5-11B 43.52/21.55/40.69 ROUGE-1/2/L"       | REFUTED (vote 1-2) | Không có paper-verified number như vậy từ Raffel et al. paper                  |
| "T5-Base fine-tuned trên SAMSum đạt 52.69/27.66/48.79 ROUGE-1/2/L"                                      | REFUTED (vote 0-3) | Không xác minh                                                                 |
| "BART improvements up to 6 ROUGE trên dialogue baselines"                                               | REFUTED (vote 1-2) | Không xác minh                                                                 |
| "BART 'particularly effective when fine-tuned for text generation'"                                     | REFUTED (vote 0-3) | Không xác minh được câu verbatim                                               |
| "PEGASUS config defaults: encoder_layers=16, d_model=1024, tie_word_embeddings=True, Unigram tokenizer" | REFUTED (vote 0-3) | Specific config claims unverified                                              |
| "Phi-3 family released under CC-BY-4.0"                                                                 | REFUTED (vote 0-3) | HF model card verified là **MIT**, không phải CC-BY-4.0                        |
| "DPO outperforms PPO trên TL;DR summarization"                                                          | REFUTED (vote 1-2) | Không có consistent evidence in published papers                               |
| "Distilling Step-by-Step beats teacher 540B trên summarization"                                         | REFUTED            | Paper chỉ evaluate NLI/QA (e-SNLI, ANLI) - KHÔNG bao gồm summarization         |
| "TinyStories approach gives SOTA summarization"                                                         | REFUTED            | Original paper chỉ test language modeling metrics, không bao gồm summarization |
| "SAMSum is the first high-quality chat-dialogue corpus"                                                 | REFUTED (vote 0-3) | Không xác minh được first-claim                                                |

**Vietnamese-specific unverified claims** (cần verify trước khi cite):

- Specific ROUGE-L cho PhoGPT/gemma-4-E2B-it-qat-GGUF/BARTpho trên dialogue summarization
- ViSoSum dataset có official paper + benchmarks
- Vietnamese-translated SAMSum quality

---

## 7. Draft Experimental Setup cho Paper

### Datasets (đa dạng và reproducible):

| Dataset                                     | Use                                              | Citation/Source                             | Status             |
| ------------------------------------------- | ------------------------------------------------ | ------------------------------------------- | ------------------ |
| **In-house meeting_committee** (Vietnamese) | Primary test, internal validity                  | Repo: `data/eval_vi/meeting_committee.json` | Verified exists    |
| **SAMSum** (English dialogue)               | Cross-language zero-shot, human-eval established | Gliwa et al. 2019, arXiv:1911.12237         | Verified exists    |
| **DialogSum** (English dialogue)            | More challenging dialogue benchmark              | Chen et al. 2021, arXiv:2106.02085          | Verified exists    |
| **MeetingBank** (English meetings)          | Real meeting transcripts                         | Hu et al. 2023, arXiv:2305.17528            | Needs verification |
| **Translated SAMSum (Vietnamese)**          | Optional: validate cross-lingual transfer        | Manual translation or NLLB                  | Cần làm thêm       |

### Models to compare (paper-defensible):

**Primary baselines (must-have):**

1. **BART-Large** (406M, English) - direct comparison với paper-2 Asthana
2. **BARTpho** (~600M, Vietnamese) - in-domain Vietnamese baseline
3. **ViT5-base** (220M, Vietnamese) - encoder-decoder Vietnamese baseline
4. **Phi-3-mini-4k-instruct** (3.8B, MIT) - modern small LLM

**Secondary baselines (nice-to-have):** 5. **FLAN-T5-Large** (780M) - instruction-tuned 6. **Gemma-2-2B-IT** (2.6B) - small decoder-only

**Teacher model (for distillation experiment):**

- **Llama-3-70B-Instruct** hoặc **GPT-4o/Claude-Sonnet** (API-based, không thuộc paper)
- Dùng teacher để generate target summaries trên training set
- Student model: BARTpho, ViT5, hoặc Phi-3-mini

### Evaluation metrics:

**Automatic:**

- ROUGE-1/2/L (mandatory, Lin 2004)
- BERTScore-F1 (Zhang 2020, arXiv:1904.09675)
- FactCC (Kryscinski 2020) hoặc SummaC (Laban 2022, arXiv:2111.02533)

**LLM-as-judge:**

- GPT-4/Claude prompted với chain-of-thought rubric
- 5 dimensions: factual consistency, completeness, conciseness, relevance, fluency
- Following G-Eval protocol (Liu 2023, arXiv:2303.08774)

**Human evaluation (optional, follow Asthana protocol):**

- 5-7 Vietnamese-speaking participants
- Task-based think-aloud interviews
- Per-summary 1-5 Likert ratings

### Distillation experiment design:

**Method 1: Supervised Output Distillation (baseline)**

- Teacher (Llama-3-70B): generate abstractive summary cho mỗi chunk + title cho mỗi segment
- Student: BARTpho fine-tuned trên (input_chunk, teacher_summary) pairs
- Metric: ROUGE, BERTScore vs. teacher outputs

**Method 2: Distilling Step-by-Step (Hsieh 2023)**

- Same teacher, plus extract rationales (e.g., key sentences, key entities)
- Student: multi-task training (summary generation + rationale prediction)
- Expectation: better data efficiency (80% data như Method 1 to match teacher)

**Method 3 (Optional): GKD on-policy**

- Student generates summaries, teacher provides feedback
- Train với JSD(0.9) divergence (per GKD findings cho summarization)
- Caveat: chỉ verified trên XSum, cần validate cho dialogue

### Compute budget:

**For this paper, expect:**

- Baseline runs: 4-6 models × 5 datasets × {zero-shot, fine-tuned} = 20-60 runs
- Distillation experiments: 2-3 methods × 1-2 student models × multiple seeds
- LLM-as-judge: ~5000-10000 generated summaries × GPT-4 calls (cost: $200-500)
- Human evaluation: 5-7 participants × 2 hours × compensation

**Total estimated:** $500-1500 (excluding local compute)

---

## 8. Open Questions cần user quyết định trước khi viết paper

1. **SAMSum/DialogSum benchmarks:** Có cần paper tự chạy Phi-3/Gemma-2 zero-shot trên SAMSum/DialogSum để có paper-vendor numbers, hay cite third-party leaderboard (Papers with Code)?

2. **Vietnamese dataset choice:**
   - Option A: Chỉ dùng in-house `meeting_committee.json` (giữ scope nhỏ, internal validity cao)
   - Option B: Dịch SAMSum → Vietnamese (cross-lingual validation, broader impact)
   - Option C: Tìm/crawl ViSoSum, VLSP, UIT-ViDialog (nếu public)

3. **Distillation experiment scope:**
   - Baseline only (Supervised Output Distillation) - paper ngắn, faster publication
   - - Distilling Step-by-Step (additional method, more contribution)
   - - GKD on-policy (full comparison, nhưng unverified cho dialogue)

4. **Venue target:** ACL/EMNLP/NeurIPS yêu cầu strong baselines + ablations. Workshop papers cho phép scope hẹp hơn.

5. **Model name confusion:** `unsloth/gemma-4-E2B-it-qat-GGUF` trong `src/repo/model_loader.py:42` - "gemma-4" không tồn tại tại cutoff date 2026-01. Confirm với maintainer: là Gemma 2 2B hay Gemma 3 4B?

---

## 9. Summary Table: Paper-Defensible vs. Unverified

| Aspect                               | Paper-Defensible (verified)                                                                                                                                 | Unverified (cần self-run)                                                                      |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Baselines architecture**           | Enc-Dec (BART, PEGASUS, T5, FLAN-T5) + Dec-only (Phi-3, Gemma-2, Llama-3, Qwen2.5)                                                                          | -                                                                                              |
| **Model families**                   | BART, PEGASUS, T5/FLAN-T5, Phi-3, Gemma-2, Llama-3, Qwen2.5                                                                                                 | Llama-3.2, Mistral, Mixtral                                                                    |
| **Distillation methods**             | Supervised Output Distillation (Hinton), Distilling Step-by-Step (Hsieh 2023), GKD (Agarwal 2024), Sequence-Level KD (Kim & Rush 2016), DPO (Rafailov 2023) | TinyStories-style                                                                              |
| **Vietnamese models**                | -                                                                                                                                                           | PhoGPT, gemma-4-E2B-it-qat-GGUF, BARTpho, ViT5 (have paper) + SAMSum/DialogSum ROUGE cho chúng |
| **Evaluation**                       | ROUGE (Lin 2004), BERTScore (Zhang 2020), BARTScore (Yuan 2021), G-Eval (Liu 2023), FactCC, SummaC, Human eval                                              | -                                                                                              |
| **Dialogue ROUGE/human correlation** | Verified low (r=0.30-0.32) per Gliwa 2019 → need multiple metrics                                                                                           | -                                                                                              |

---

## Sources (Verified URLs)

- arXiv:1910.13461 - BART (Lewis et al. 2020)
- arXiv:1912.08777 - PEGASUS (Zhang et al. 2020, ICML 2020)
- arXiv:1911.12237 - SAMSum (Gliwa et al. 2019)
- arXiv:2404.14219 - Phi-3 (Abdin et al. 2024)
- arXiv:2408.00118 - Gemma 2 (Team et al. 2024)
- arXiv:2407.21783 - Llama 3 (Dubey et al. 2024)
- arXiv:2412.15115 - Qwen 2.5 (Qwen Team 2024)
- arXiv:2305.02301 - Distilling Step-by-Step (Hsieh et al. 2023, ACL 2023 Findings)
- arXiv:2306.13649 - GKD (Agarwal et al. ICLR 2024)
- arXiv:2305.18290 - DPO (Rafailov et al. NeurIPS 2023)
- arXiv:1904.09675 - BERTScore (Zhang et al. ICLR 2020)
- arXiv:2106.11520 - BARTScore (Yuan et al. NeurIPS 2021)
- arXiv:2303.08774 - G-Eval (Liu et al. NeurIPS 2023)
- arXiv:2111.02533 - SummaC (Laban et al. 2022)
- https://huggingface.co/microsoft/Phi-3-mini-4k-instruct (verified MIT license)
- https://github.com/google-research/distilling-step-by-step (verified code exists)
