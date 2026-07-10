# 🤖 Models, Prompts, & Data Validation

The capabilities of the Meeting Recap System rely on a combination of machine learning models, structured prompting schemas, and validation parameters.

---

## 🔬 1. The Machine Learning Models

### Sliding TextTiling (Topic Segmentation)
Topic segmentation now uses a purely **lexical Sliding TextTiling** approach — no neural scoring model required.

*   **Bag-of-Words**: Each utterance is tokenised by lowercasing, stripping punctuation, and filtering against Vietnamese stop words (`stopwordsiso`).
*   **Cosine Similarity**: Cosine similarity is computed at every consecutive utterance gap, with each side pooled into a `block_size` window (default: 3).
*   **Multi-Scale Depth Scores**: Depth scores are computed at multiple peak-search radii (default `[3, 5, 10, 15, 20]`) using the classic TextTiling formula:
    $$dp_i = \frac{hl(i) + hr(i) - 2 \cdot s_i}{2}$$
    where $s_i$ is the similarity at gap $i$, and $hl$/$hr$ are the nearest peaks on each side.
*   **Normalisation & Aggregation**: Each radius's depth profile is independently z-score normalised, then aggregated via mean/max/sum into a single multi-scale depth profile.
*   **Thresholding**: Boundaries are placed at gaps where $dp_i > \tau$, with $\tau = \mu + \alpha \cdot \sigma$ (default $\alpha = 0.9$).
*   **Small-Segment Merge**: Segments smaller than `min_segment_ratio * n_utterances` are greedily merged into the shallower-depth neighbour.

### Summarization Backbone
The system features dual summarization models (for chunk summaries and chapter titles):
*   **Default Execution**: Runs in an offline, network-free mode using the `MockLLMBackbone` class to provide static, deterministic Vietnamese responses.
*   **Production Backbone**: Can be activated via environment variables (`MODEL_LOAD_LLM=1`) to load `Viet-Mistral/gemma-4-E2B-it-qat-GGUF` at runtime.

---

## 📐 2. The Mathematics of Sliding TextTiling

For a dialogue of $N$ utterances, we compute $N-1$ cosine similarity scores $s_i$ between adjacent utterance windows (each window pools `block_size` utterances). The algorithm then computes local "depth scores" measuring how deep each valley is relative to nearby peaks:

$$dp_i = \frac{hl(i) + hr(i) - 2 \cdot s_i}{2}$$

Where:
*   $s_i$ is the cosine similarity between the BoW vectors at gap $i$.
*   $hl(i)$ is the highest similarity peak value reached to the left of gap $i$ within a given search radius.
*   $hr(i)$ is the highest similarity peak value reached to the right of gap $i$.

This depth computation is repeated at **multiple radii** (default `[3, 5, 10, 15, 20]`). Each radius produces one depth profile which is z-score normalised. The normalised profiles are then aggregated (mean/max/sum) into a single multi-scale depth profile.

### Boundary Cutting Threshold ($\tau$)
A segment boundary is triggered between utterance $i$ and $i+1$ when:

$$dp_i > \tau$$

$$\tau = \mu + \alpha \cdot \sigma$$

Where:
*   $\mu$ is the mean of the aggregated multi-scale depth scores.
*   $\sigma$ is the standard deviation of the depth scores.
*   $\alpha$ is the tuning hyperparameter (default `0.9`, configurable in `SlidingTextTilingConfig`).
*   After thresholding, segments smaller than `min_segment_ratio * N` are greedily merged into the shallower-depth neighbour.

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
