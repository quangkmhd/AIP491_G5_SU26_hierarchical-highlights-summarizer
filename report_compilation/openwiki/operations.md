# 🛠 Operations & System Validation

This page documents the evaluation metrics and methods used to score the Hierarchical Meeting Recap System.

---

## 📊 Segmentation Quality Metrics

The system measures segmentation accuracy using three core metric calculations:

1.  **$P_k$ (Beeferman et al., 1999)**: Measures slide window disagreement probability. Lower is better. Our target baseline is $P_k \le 30.0$.
2.  **Win-Diff (Pevzner & Hearst, 2002)**: Evaluates segment boundaries by comparing window cuts. Lower is better.
3.  **F1-Score**: Measures overlapping accuracy between generated segments and human ground-truth divisions.

