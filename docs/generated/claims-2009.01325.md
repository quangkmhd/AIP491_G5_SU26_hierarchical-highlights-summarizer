# Source Claim Extraction — arXiv 2009.01325

**URL:** https://arxiv.org/abs/2009.01325
**Title:** Learning to Summarize with Human Feedback
**Authors:** Nisan Stiennon, Long Ouyang, Jeff Wu, Daniel M. Ziegler, Ryan Lowe, Chelsea Voss, Alec Radford, Dario Amodei, Paul Christiano
**Affiliation:** OpenAI
**Publication venue:** NeurIPS 2020 (Human-in-the-Loop Workshop / main track; arXiv v1 Sept 2020, v3 Feb 2022)
**Type:** Primary research paper (preprint on arXiv, published at NeurIPS 2020)
**Retrieved:** 2026-07-07

## Source Quality Assessment

**Quality:** primary

The paper is the authors' own canonical venue for their research, hosted on arXiv (the institutional preprint server). It is the definitive source for the OpenAI RLHF summarization work that the broader literature cites. A direct binary fetch of the PDF returned only figure captions (the paper is two-column, and WebFetch extracted figure metadata only), so quantitative numbers beyond the abstract are not in this record; the arXiv abstract itself is the most authoritative text that could be programmatically retrieved here, and is universally treated as authoritative in secondary citations (OpenAI blog, NeurIPS proceedings, follow-up papers).

## Falsifiable Claims

### Claim 1 — RL-finetuned model beats both human reference and larger supervised baselines

* **Claim:** The policy fine-tuned with PPO using the learned reward on TL;DR data outperforms both the held-out human reference summaries and substantially larger supervised-only baselines, when judged by human annotators.
* **Quote:** "Our models also significantly outperform both human reference summaries and much larger models fine-tuned with supervised learning alone."
* **Importance:** central — directly establishes the headline methodological premise (RLHF beats SFT for summarization) that the research question wants to extend into meetings.
* **Falsifiability:** Asserts a concrete ranking outcome (PPO-RLHF > human reference > larger SFT) under human preference judgments; can be tested by replicating the evaluation protocol.

### Claim 2 — Reward-model optimization correlates better with human preference than ROUGE optimization

* **Claim:** Training the policy to maximize the reward model's predicted preference yields higher human-rated quality than training it to maximize ROUGE (the standard summarization metric).
* **Quote:** "We show that optimizing our reward model results in better summaries than optimizing ROUGE according to humans."
* **Importance:** central — provides the justification for using a learned reward surrogate instead of ROUGE, which is foundational if the research question wants to extend this to meeting summarization.
* **Falsifiability:** Assertes a measurable relationship between optimization target and human preference ranking; can be checked with an A/B preference study.

### Claim 3 — RLHF transfers zero-shot to a different domain (CNN/DM news)

* **Claim:** The model trained on Reddit TL;DR via RLHF transfers with no news-specific fine-tuning to CNN/DM news summarization and produces summaries nearly matching human references.
* **Quote:** "We also summarize CNN/DM news articles, achieving transfer without any news-specific fine-tuning, with summaries nearly as good as the human reference."
* **Importance:** supporting — relevant to whether a single RLHF-trained model can serve multi-domain summarization (e.g., meetings + emails) in a production system.
* **Falsifiability:** Predicts a specific cross-domain transfer quality outcome that can be re-measured.

### Claim 4 — Human preference data collection is the central training signal

* **Claim:** The methodology rests on collecting a large dataset of human pairwise comparisons between summaries and training a reward model to predict the preferred one.
* **Quote:** "We collect a large, high-quality dataset of human comparisons between summaries, train a reward model to predict the human-preferred summary, and fine-tune a summarization policy using reinforcement learning."
* **Importance:** central — identifies the human-comparison annotation pipeline that any extension to meetings would replicate or replace.
* **Falsifiability:** Describes a concrete, documentable dataset construction and training pipeline that can be inspected and audited.

### Claim 5 — The reward model is the optimization target, not a reference scorer

* **Claim:** The reward model — not the human annotators directly — is what the policy optimizes against in RL fine-tuning.
* **Quote:** "[We] use [the reward model] as a reward function to fine-tune a summarization policy using reinforcement learning."
* **Importance:** supporting — establishes the surrogate-reward architecture that the research question's RLHF-for-meetings suggestion would inherit.
* **Falsifiability:** Assertes a specific, code-verifiable pipeline: rewards are predicted by the RM, not provided per-step by humans, during PPO updates.

## Notes on Completeness

The arXiv abstract fetch returned the full abstract verbatim; the follow-up PDF fetch returned a binary save but only figure-label text was readable (PDF stream parsing limitation of WebFetch), so per-table numerical win-rates, the 1.3B/6B base-model size, KL penalty coefficient, RM validation accuracy, and exact human-comparison counts were not programmatically extracted in this session. The five claims above are all anchored in text that **was** retrieved (the abstract) and are stable across the literature.
