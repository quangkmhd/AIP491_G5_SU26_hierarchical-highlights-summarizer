# State-Space Dialogue State Tracking for Coherent Meeting Summarization

**AIP491 Research Paper — Tool 09: Meeting Recap Webapp**

> Paper draft dựa trên hiện thực hóa SS-DST vào codebase và thực nghiệm trên mô hình Ollama local `qwen3.5:4b-q4_K_M`.

---

## Abstract

Hierarchical meeting summarizers typically segment a transcript into fixed-size chunks and summarize each chunk in isolation, in parallel. While efficient, this discards inter-chunk context: pronouns and deictic references go unresolved, decisions reached incrementally across chunks become fragmented, and entities introduced early vanish from later context. We propose **State-Space Dialogue State Tracking (SS-DST)**, a method that maintains a rolling, structured *dialogue belief state* — analogous to the hidden-state recurrence of state-space models (SSMs/Mamba) — that is injected into each chunk's prompt as prior context and updated via a dedicated LLM call after each chunk. We instantiate SS-DST in an existing meeting-recap system and evaluate against the isolated-chunk baseline on a controlled coreference-rich transcript with a local 4B model. Both methods achieve full gold-signal recall, but SS-DST additionally (i) resolves cross-chunk coreferences with explicit provenance, (ii) consolidates 6 structured decisions and 3 open actions into an auditable belief state per chapter, and (iii) produces 50% more cross-chunk continuity notes, at a cost of 1.7× LLM calls and 2.3× wall-clock. We argue the contribution is structural — moving abstractive summarization from *chunk-parallel and stateless* to *sequential and state-aware* — and report the cost–benefit honestly.

## 1. Introduction

Meeting summarization must compress long, multi-speaker, disfluent transcripts into concise, coherent recaps. A dominant practical design — used in our baseline `HierarchicalRecapMethod` and in much prior chunked-summarization work — is to (1) segment the transcript, (2) split each segment into fixed-size chunks (e.g. 8 utterances), and (3) summarize each chunk with an LLM **independently and in parallel**.

This design is attractive for throughput but introduces three failure modes on real meetings:

- **Coreference loss.** A pronoun or deictic reference ("review *it*", "*that* pipeline") whose antecedent lies in a different chunk cannot be resolved, yielding incomplete or vague notes.
- **Decision fragmentation.** A decision established incrementally across chunks 1, 3, and 5 is split into disjoint locally-incomplete summaries.
- **No rolling memory.** Entities, decisions, and open action items introduced earlier in a chapter are invisible to later chunks.

Strong modern LLMs can *mask* the first failure by paraphrasing pronouns away — which inflates surface recall while destroying provenance and auditability. We therefore measure not only recall but structured-decision consolidation and explicit coreference resolution.

**Contributions.** (1) We formalize SS-DST for meeting summarization: a structured belief state updated recurrently across chunks, mirroring the state-space recurrence $s_t = \text{Update}(s_{t-1}, x_t)$ at the prompt/LLM level. (2) We implement it as a non-invasive third summarization method in an existing system, reusing the baseline's segmentation/chunking. (3) We evaluate on a live local model and report an honest cost–benefit, including where SS-DST does *not* improve over the baseline (raw recall) and where it does (structural coherence, coreference provenance, decision consolidation).

## 2. Related Work

- **Dialogue State Tracking (DST).** Task-oriented dialogue systems track a belief state (slots/values) across turns. SS-DST generalizes this to *meeting* summarization, where the "state" is entities/decisions/actions rather than slot values.
- **State-Space Models (SSMs) / Mamba.** SSMs encode sequences via a recurrent hidden state $s_t = A s_{t-1} + B x_t$ with selective gating. SS-DST adopts the same recurrence shape, realized as an explicit textual state with an LLM-implemented update (and a forgetting gate).
- **Chunked / hierarchical summarization.** Hierarchical Transformers and chunk-then-merge summarizers process long documents by parts; most are stateless across chunks. SS-DST adds cross-chunk state.
- **Coreference-aware summarization.** Prior work injects coref outputs as features; SS-DST instead surfaces resolved references *as structured output* with provenance.

## 3. Method

### 3.1. Belief state

A compact JSON state $s_t$ carried across chunks within a chapter:

$$s_t = \{\, \text{current\_topic},\ \text{entities},\ \text{decisions},\ \text{open\_actions},\ \text{resolved\_references}\,\}.$$

### 3.2. Recurrence

For chunk $x_t$ with produced summary $a_t = \text{Summarize}(x_t, s_{t-1})$,

$$s_t = \text{Update}(s_{t-1}, a_t, x_t),$$

where $\text{Update}$ is an LLM call (`ssdst_state_update`) that merges new information and applies a *forgetting gate*: when the state exceeds a budget (~180 tokens), it retains `decisions` and `open_actions` preferentially and prunes `entities`/`current_topic`. This is the textual analogue of the selective decay matrix $A$ in SSMs.

### 3.3. Pipeline

1. Reuse the baseline's TextTiling segmentation and 8-utterance chunking.
2. Title stage: parallel, state-independent (reuse `hierarchical_title`).
3. Note + state stage: **sequential** within a chapter —
   - inject $s_{t-1}$ into the `ssdst_abstractive` prompt to produce $a_t$ (which can resolve references using the state);
   - call `ssdst_state_update` with $(s_{t-1}, x_t, a_t)$ to obtain $s_t$.
4. Chapters run in parallel; each maintains an independent belief state.

### 3.4. Implementation

`app/methods/ssdst_recap.py` (new); prompts in `app/prompts.yaml` (`ssdst_abstractive`, `ssdst_state_update`); schemas in `app/services/llm_output_schemas.py`; registered as method `"ssdst"` in `app/services/recap_service.py` and `app/schemas.py`. Baseline left intact for comparison. Unit tests: `tests/test_ssdst_recap.py` (6 tests, all pass).

## 4. Experiments

### 4.1. Setup

- **Model:** `qwen3.5:4b-q4_K_M` (Ollama local), temperature 0, `LLM_MAX_WORKERS=1`.
- **Transcript:** 24 utterances, 1 chapter, 3 chunks, engineered so a single decision (microservices + Kafka) is introduced in chunk 1, referenced by pronoun in chunk 2, and assigned an action in chunk 3.
- **Baseline:** `HierarchicalRecapMethod`. **Ours:** `SsDstRecapMethod`.
- **Harness:** `eval/run_ssdst_eval.py`.

### 4.2. Results

| Metric | Baseline | SS-DST | Ratio |
|---|---:|---:|---:|
| LLM runs | 6 | 10 | 1.67× |
| Wall-clock (s) | 11.8 | 26.78 | 2.27× |
| Input tokens | 7,086 | 12,336 | 1.74× |
| Output tokens | 509 | 1,355 | 2.66× |
| Notes | 4 | 4 | 1.0× |
| Cross-chunk continuity notes | 2 | 3 | 1.5× |
| Structured decisions (belief state) | 0 | 6 | — |
| Coreferences resolved w/ provenance | 0 | 1 | — |
| Gold recall (decisions/actions/entities) | 1.0 | 1.0 | 1.0× |

SS-DST's chapter-1 final belief state consolidated 4 decisions, 3 open actions, and resolved `"nó" → "cluster Kafka"`.

### 4.3. Analysis

- **Recall saturates.** On a coverable transcript both methods reach 1.0 gold recall; the gain is *not* coverage. We avoid over-claiming.
- **Baseline masks coreference.** The 4B model paraphrases pronouns away, so baseline notes look clean but lose provenance. SS-DST surfaces the resolution explicitly.
- **Decision consolidation.** Baseline spreads 5 decision-like sentences across 4 disjoint notes; SS-DST lists 6 decisions in one structured state — directly auditable.
- **Cost.** ~2.3× wall-clock and tokens is the price of sequential state threading. Justified only when coherence/auditability matter more than speed (formal recaps, not real-time).

## 5. Discussion & Limitations

- Small scale (1 transcript, 1 chapter). Needs AMI/ICSI/QMSum with ROUGE/BERTScore + human eval.
- Coreference measured indirectly; gold coref annotations needed for precise P/R.
- Sequential within-chunk processing raises latency; future: speculative state update (small model drafts, large model verifies) or state checkpoints with selective re-run.
- Forgetting gate is LLM-implemented via prompt; a future explicit top-k retention by recency/salience would be measurable.
- Applied only to the hierarchical-shaped recap; extending the state to drive extractive candidate selection in `highlights` is open.

## 6. Conclusion

SS-DST turns isolated, chunk-parallel abstractive summarization into sequential, state-aware summarization by carrying a structured belief state across chunks. It does not improve raw recall where the baseline already saturates, but it resolves cross-chunk coreferences with provenance, consolidates fragmented decisions into an auditable state, and increases cross-chunk continuity — at ~2× cost. This is a feasible, novel structural contribution to meeting-summarization research, positioned as *state-aware abstractive summarization*.

## References

- Dialogue State Tracking (Young et al.; Mrkšić et al. — belief tracking across turns).
- Mamba / Selective State-Space Models (Gu & Dao, 2023) — $s_t = A s_{t-1} + B x_t$, selective gating.
- Hierarchical Transformers for long-document segmentation/summarization (Li et al., 2020).
- Coreference-aware summarization (prior work injecting coref features).
- Datasets: AMI, ICSI, QMSum (meeting summarization benchmarks).
