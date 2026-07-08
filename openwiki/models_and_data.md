# 🤖 Models, Prompts, & Data Validation

The capabilities of the Meeting Recap System rely on a combination of machine learning models, structured prompting schemas, and validation parameters.

---

## 🔬 1. The Machine Learning Models

### CoherenceNet (NSP-BERT Scorer)
We adopt the best-performing unsupervised topic segmentation model configuration described in **Paper 1 (_Ours (full)_)**:

*   **Pre-trained Base**: `bert-base-multilingual-cased` (tailored to resolve multilingual syntax structures like Vietnamese).
*   **Architecture**: 12 Transformer layers, 12 attention heads, hidden state size of 768.
*   **Coherence MLP Decoder Deck**: Consists of `Linear(768, 768) -> ReLU() -> Dropout(0.1) -> Linear(768, 2)`.
*   **Loss Criterion**: Optimized via a custom Marginal Ranking Loss function:
    $$L = \frac{1}{N} \sum \max(0, \eta + c^- - c^+)$$
    with a margin threshold of $\eta = 1$. It leverages both dialog flow and open-topic dialog negatives.
*   **Local Checkpoint**: We load from the local, pre-trained checkpoint: `vibert_checkpoints_vi/cpt_4000.pth`.

### Summarization Backbone
The system features dual summarization models (for chunk summaries and chapter titles):
*   **Default Execution**: Runs in an offline, network-free mode using the `MockLLMBackbone` class to provide static, deterministic Vietnamese responses.
*   **Production Backbone**: Can be activated via environment variables (`MODEL_LOAD_LLM=1`) to load `Viet-Mistral/gemma-4-E2B-it-qat-GGUF` at runtime.

---

## 📐 2. The Mathematics of Neural TextTiling

Consecutive utterances are scored in pairs. If a dialogue contains $N$ utterances, the pipeline computes $N-1$ scoring tuples. The transition algorithm computes local "depth scores" measuring semantic valleys:

$$dp_i = \frac{hl(i) + hr(i) - 2c_i}{2}$$

Where:
*   $c_i$ is the coherence score between utterance $i$ and $i+1$.
*   $hl(i)$ is the highest coherence peak value reached to the left of index $i$.
*   $hr(i)$ is the highest coherence peak value reached to the right of index $i$.

### Boundary Cutting Threshold ($\tau$)
A segment boundary is triggered between utterance $i$ and $i+1$ when:

$$dp_i > \tau$$

$$\tau = \mu + \alpha \cdot \sigma$$

Where:
*   $\mu$ is the mean of all computed depth scores across the dialogue.
*   $\sigma$ is the standard deviation of depth scores.
*   $\alpha$ is our tuning hyperparameter. For our Vietnamese dataset, **$\alpha$ is set to 1.0** (or customized in `TextTilingConfig`).

---

## 📝 3. Structured Prompt Guidelines

All task configurations directed to the LLM are standardized into JSON schemas inside `src/repo/prompts_vi.py`.

*   **SYSTEM_PROMPT_VI**: Enforces Vietnamese-only responses, zero markdown fences, no conversational preambles, and 3rd-person professional narrative structure.
*   **HIERARCHIC_ABSTRACTIVE_PROMPT_VI**: Generates factual 1-3 sentence rolling notes per 8-utterance chunk. Configures the boolean attributes:
    *   `contains_key_point`: Set to `true` if a critical decision, architectural change, or blocker is highlighted.
    *   `contains_action_item`: Set to `true` if explicit follow-up commitments, action items, or deadlines are tracked.
*   **HIERARCHIC_TITLE_PROMPT_VI**: Generates a Vietnamese chapter title constrained to 4-10 words.

---

## 🧱 4. Pydantic Invariant Safeguards

To block invalid data or execution-bypassing payloads, strict constraints are enforced by Pydantic validators:

*   `Utterance`: Attributes `speaker` and `text` are strictly marked `min_length=1` and set as `frozen=True` to block inline manipulation.
*   `DialogueTranscript`: Forces utterance sequence ordering. Indices must form an absolute contiguous sequence from $0 \dots N-1$.
*   `MAX_UTTERANCES`: Transcripts are cap-checked at **5,000 utterances** to prevent GPU model timeout/OOM.
*   `MAX_CHUNK_SIZE`: Chunks are strictly limited to **8 utterances** to preserve the 512-token context constraints of abstractive summarizers.
