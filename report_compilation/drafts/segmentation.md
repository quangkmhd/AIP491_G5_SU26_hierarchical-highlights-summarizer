# Dialogue Topic Segmentation (DTS)

Topic Segmentation divides text streams (such as spoken dialogues or call transcripts) into discrete thematic units. Unlike structured documents, meeting recordings lack bullet points, structural chapters, or formal paragraph boundaries. This module provides a collection of algorithms to extract these boundaries.

---

## 📊 Overview of Available Segmenters

We support five segmenters spanning unsupervised NLP heuristics and supervised Transformer architectures.

```
                  ┌─ Unsupervised ──► NltkTextTiling, CustomTextTiling, SlidingTextTiling
                  │
[ DTS Segmenters ]┼─ Supervised ────► ViBertTextTiling (Embedding similarities)
                  │
                  └─ Supervised ────► BamiBert1DOD (1D Object Detection classification)
```

---

## 🔍 Unsupervised & Heuristic Segmenters

Heuristic segmenters use lexical cohesion properties to identify topic shifts, running efficiently on CPU without requiring GPU environments.

### 1. `nltk_texttiling` (`src/segmenters/nltk_texttiling.py`)
*   **Concept**: A thin wrapper wrapping the classic NLTK `TextTiling` boundary model.
*   **How it works**: Groups text sequences into lexical pseudo-sentences, measures block cosine similarities, computes depth scores, and sets flags on similarity valleys.
*   **Properties**:
    *   Fast execution.
    *   Relies primarily on default NLTK tokenization rules which may not align perfectly with Vietnamese multi-character syllable spacing.

### 2. `sliding_texttiling` (`src/segmenters/sliding_texttiling.py`)
*   **Concept**: Multi-scale Sliding TextTiling combining standard TextTiling with Multi-Scale Depth Validation, inspired by Section 3.2.2 of Asthana et al. (2025)'s *LLM-powered Meeting Recap System*. Xem tài liệu chi tiết: [sliding_texttiling.md](sliding_texttiling.md).
*   **How it works**:
    *   Instead of measuring depths at a single hardcoded window, it performs **multi-scale depth analysis** simultaneously over a collection of radii (defaults: `[3, 5, 10, 15, 20]`). Xem tài liệu chi tiết: [sliding_texttiling.md](sliding_texttiling.md).
    *   Each radius corresponds to searching for boundaries at different resolutions (smaller radii identify quick shifts; wider radii locate larger phase shifts).
    *   Depth outcomes are normalized (using zscore) and combined:
        $$\text{depth\_profile} = \frac{1}{|R|} \sum_{r \in R} \text{zscore}(\text{depth}_r)$$
    *   Boundaries are flagged if $\text{depth\_profile} \ge \alpha$ and a minimum spacing limit (`min_segment_ratio`) is enforced to prevent over-segmentation.
*   **Performance**: Excellent overall unsupervised baseline; filters noise and avoids over-partitioning.

---

## 🤖 Supervised & Deep Learning Segmenters

Supervised segmenters leverage deep transformer models fine-tuned to recognize dialogue boundaries.

### 1. `vibert_texttiling` (`src/segmenters/vibert_texttiling.py`)
*   **Concept**: Replaces static Bag-of-Words similarities in TextTiling with dense sentence embeddings yielded by a Vietnamese Bert fine-tuned by us.
*   **Huấn luyện & Nền tảng**: Được tinh chỉnh (fine-tune) trên chính 6 bộ dữ liệu tiếng Việt thực nghiệm dựa trên phương pháp tính điểm liên kết cặp câu của Xing và Carenini (2021) [@Xing2021].
*   **Details**:
    *   Loads local weights (e.g., `models/vibert/cpt_3818.pth`).
    *   Feeds sentence structures to map semantic embeddings, calculating cosine distances between embeddings to evaluate topic shifts.
    *   Inherits similarity alignment features from TextTiling.

### 2. `bamibert_1dod` (`src/segmenters/bamibert_1dod.py`)
*   **Concept**: Re-envisions dialogue segmenting as a **1D Object Detection task (1DOD)**, inspired by the paper *One-Dimensional Object Detection for Streaming Text Segmentation of Meeting Dialogue* [@He2024].
*   **Huấn luyện & Nền tảng**: Được tinh chỉnh (fine-tune) trên chính 6 bộ dữ liệu tiếng Việt thực nghiệm dựa trên phương pháp phát hiện biên của He và cộng sự (2024).
*   **How it works**:
    *   Utilizes a local fine-tuned model (`models/bamibert-1dod-vi-v1`).
    *   Encodes speaker turns and textual context within a sliding multi-sentence window.
    *   The model directly classifies whether each utterance boundary has a high likelihood of being a topic shift.
*   **Performance**: High accuracy; leverages contextual understanding of spoken cues (e.g., transitions, introductions) rather than relying solely on lexical repetition.

---

## 📈 Evaluation Metrics Summary

Evaluations are computed in `src/evaluate/metrics.py` to assess segment boundary matches.

*   **Pk Score (WindowDiff Variation)**:
    Checks if sliding windows covering $k$ utterance steps contain matching numbers of boundaries in prediction vs. ground truth. Highly penalized by missed segments. **Lower is better (0.0 to 1.0)**.
*   **Wd (WindowDiff)**:
    A stricter metric that accounts for exact boundary counts within each sliding window. **Lower is better**.
*   **F1-Score**:
    Computes precision & recall of boundary positions within a tolerance window (precision vs. recall of topic boundaries). **Higher is better**.
