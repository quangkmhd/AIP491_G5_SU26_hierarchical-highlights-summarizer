# Evaluation Methodology

This document is the authoritative reference for how PluginEval measures plugin and skill quality.
It covers the three evaluation layers, all ten scoring dimensions, the composite formula, badge
thresholds, anti-pattern flags, Elo ranking, and actionable improvement tips.

Related: [Full rubric anchors](references/rubrics.md)

---

## The Three Evaluation Layers

PluginEval stacks three complementary layers. Each layer produces a score between 0.0 and 1.0 for
each applicable dimension, and later layers override or blend with earlier ones according to
per-dimension blend weights.

### Layer 1 — Static Analysis

**Speed:** < 2 seconds. No LLM calls. Deterministic.

The static analyzer (`layers/static.py`) runs six sub-checks directly against the parsed SKILL.md:

| Sub-check | What it measures |
|---|---|
| `frontmatter_quality` | Name presence, description length, trigger-phrase quality |
| `orchestration_wiring` | Output/input documentation, code block count, orchestrator anti-pattern |
| `progressive_disclosure` | Line count vs. sweet-spot (200–600 lines), references/ and assets/ bonuses |
| `structural_completeness` | Heading density, code blocks, examples section, troubleshooting section |
| `token_efficiency` | MUST/NEVER/ALWAYS density, duplicate-line repetition ratio |
| `ecosystem_coherence` | Cross-references to other skills/agents, "related"/"see also" mentions |

These six sub-checks feed directly into six of the ten final dimensions (via `STATIC_TO_DIMENSION`
mapping). The remaining four dimensions — `output_quality`, `scope_calibration`,
`robustness`, and part of `triggering_accuracy` — receive no static contribution and rely
entirely on Layer 2 and/or Layer 3.

**Anti-pattern penalty** is applied multiplicatively to the Layer 1 score:

```
penalty = max(0.5, 1.0 − 0.05 × anti_pattern_count)
```

Each additional detected anti-pattern reduces the score by 5%, flooring at 50%.

### Layer 2 — LLM Judge

**Speed:** 30–90 seconds. One or more LLM calls (Sonnet by default). Non-deterministic.

The `eval-judge` agent reads the SKILL.md and any `references/` files, then scores four
dimensions using anchored rubrics (see [references/rubrics.md](references/rubrics.md)):

1. **Triggering accuracy** — F1 score derived from 10 mental test prompts
2. **Orchestration fitness** — Worker purity assessment (0–1 rubric)
3. **Output quality** — Simulates 3 realistic tasks; assesses instruction quality
4. **Scope calibration** — Judges depth and breadth relative to the skill's category

The judge returns a structured JSON object (no markdown fences) that the eval engine merges
into the composite. When `judges > 1`, scores are averaged and Cohen's kappa is reported as
an inter-judge agreement metric.

### Layer 3 — Monte Carlo Simulation

**Speed:** 5–20 minutes. N=50 simulated Agent SDK invocations (default). Statistical.

Monte Carlo runs `N` real prompts through the skill and records:

- **Activation rate** — Fraction of prompts that triggered the skill
- **Output consistency** — Coefficient of variation (CV) across quality scores
- **Failure rate** — Error/crash fraction with Clopper-Pearson exact CIs
- **Token efficiency** — Median token count, IQR, outlier count

The Layer 3 composite formula:

```
mc_score = 0.40 × activation_rate
         + 0.30 × (1 − min(1.0, CV))
         + 0.20 × (1 − failure_rate)
         + 0.10 × efficiency_norm
```

where `efficiency_norm = max(0, 1 − median_tokens / 8000)`.

---

## Composite Scoring Formula

The final score is a weighted blend across all three layers for each dimension, then summed:

```
composite = Σ(dimension_weight × blended_dimension_score) × 100 × anti_pattern_penalty
```

### Dimension Weights

| Dimension | Weight | Why it matters |
|---|---|---|
| `triggering_accuracy` | 0.25 | A skill that never fires — or fires incorrectly — has no value |
| `orchestration_fitness` | 0.20 | Skills must be pure workers; supervisor logic belongs in agents |
| `output_quality` | 0.15 | Correct, complete output is the primary deliverable |
| `scope_calibration` | 0.12 | Neither a stub nor a bloated monster |
| `progressive_disclosure` | 0.10 | SKILL.md is lean; detail lives in references/ |
| `token_efficiency` | 0.06 | Minimal context waste per invocation |
| `robustness` | 0.05 | Handles edge cases without crashing |
| `structural_completeness` | 0.03 | Correct sections in the right order |
| `code_template_quality` | 0.02 | Working, copy-paste-ready examples |
| `ecosystem_coherence` | 0.02 | Cross-references; no duplication with siblings |

### Layer Blend Weights

Each dimension draws from different layers at different ratios. With all three layers active
(`--depth deep` or `certify`):

| Dimension | Static | Judge | Monte Carlo |
|---|---|---|---|
| `triggering_accuracy` | 0.15 | 0.25 | 0.60 |
| `orchestration_fitness` | 0.10 | 0.70 | 0.20 |
| `output_quality` | 0.00 | 0.40 | 0.60 |
| `scope_calibration` | 0.30 | 0.55 | 0.15 |
| `progressive_disclosure` | 0.80 | 0.20 | 0.00 |
| `token_efficiency` | 0.40 | 0.10 | 0.50 |
| `robustness` | 0.00 | 0.20 | 0.80 |
| `structural_completeness` | 0.90 | 0.10 | 0.00 |
| `code_template_quality` | 0.30 | 0.70 | 0.00 |
| `ecosystem_coherence` | 0.85 | 0.15 | 0.00 |

At `--depth standard` (static + judge only), blends are renormalized to drop the Monte Carlo
column. At `--depth quick` (static only), all weight falls on Layer 1.

### Blended Score Calculation

For a given depth, the blended score for dimension `d` is:

```
blended[d] = Σ( layer_weight[d][layer] × layer_score[d][layer] )
             ─────────────────────────────────────────────────────
             Σ( layer_weight[d][layer] for available layers )
```

This normalization ensures that skipping Monte Carlo at standard depth doesn't artificially
deflate scores.

---

## Interpreting Dimension Scores

Each dimension score is a float in `[0.0, 1.0]`. The CLI converts it to a letter grade:

| Grade | Score range | Meaning |
|---|---|---|
| A | 0.90 – 1.00 | Excellent — no meaningful improvement needed |
| B | 0.80 – 0.89 | Good — minor gaps only |
| C | 0.70 – 0.79 | Adequate — one or two clear improvement areas |
| D | 0.60 – 0.69 | Marginal — needs targeted work |
| F | < 0.60 | Failing — significant remediation required |

When reading a report, focus first on the lowest-graded dimension that has the highest weight.
A D in `triggering_accuracy` (weight 0.25) costs far more than a D in `ecosystem_coherence`
(weight 0.02).

**Confidence intervals** appear in the report when Layer 2 or Layer 3 ran. Narrow CIs (± < 5
points) indicate stable scores. Wide CIs suggest inconsistency — often caused by an ambiguous
description or instructions that work for some prompt styles but not others.

---

## Quality Badges

Badges require both a composite score threshold AND an Elo threshold (when Elo is available).
The `Badge.from_scores()` logic checks composite first, then Elo if provided:

| Badge | Composite | Elo | Meaning |
|---|---|---|---|
| Platinum ★★★★★ | ≥ 90 | ≥ 1600 | Reference quality — suitable for gold corpus |
| Gold ★★★★ | ≥ 80 | ≥ 1500 | Production ready |
| Silver ★★★ | ≥ 70 | ≥ 1400 | Functional, has improvement opportunities |
| Bronze ★★ | ≥ 60 | ≥ 1300 | Minimum viable — not yet recommended for users |
| — | < 60 | any | Does not meet minimum bar |

The Elo threshold is skipped when Elo has not been computed (i.e., at quick or standard depth
without `certify`). A skill can earn a badge on composite score alone in those cases.

---

## Anti-Pattern Flags

The static analyzer detects five anti-patterns. Each carries a severity multiplier that feeds
into the penalty formula.

### OVER_CONSTRAINED

**Trigger:** More than 15 occurrences of MUST, ALWAYS, or NEVER in the SKILL.md.

**Problem:** Overly prescriptive instructions reduce model flexibility, increase token overhead,
and signal that the author is trying to micromanage every output rather than providing
principled guidance.

**Fix:** Audit every MUST/ALWAYS/NEVER. Replace directive language with explanatory framing
where possible. Reserve hard constraints for genuine safety or correctness requirements. Target
fewer than 10 such directives per 100 lines.

### EMPTY_DESCRIPTION

**Trigger:** The frontmatter `description` field is fewer than 20 characters after stripping.

**Problem:** Without a meaningful description, the Claude Code plugin system cannot determine
when to invoke the skill. The skill becomes invisible to autonomous invocation.

**Fix:** Write a description of at least 60–120 characters that includes:
- A "Use this skill when..." or "Use when..." trigger clause
- Two or more concrete contexts separated by commas or "or"

### MISSING_TRIGGER

**Trigger:** The description does not contain "use when", "use this skill when",
"use proactively", or "trigger when" (case-insensitive).

**Problem:** Even a long description is useless for autonomous invocation if it doesn't
include a clear trigger signal. The system's routing model needs an explicit cue.

**Fix:** Prepend "Use this skill when..." to the description, followed by specific scenarios.
Example: "Use this skill when measuring plugin quality, interpreting score reports, or
explaining badge thresholds to a team."

### BLOATED_SKILL

**Trigger:** SKILL.md exceeds 800 lines AND the skill has no `references/` directory.

**Problem:** A monolithic SKILL.md forces the entire document into context on every invocation,
wasting tokens on content only needed in edge cases.

**Fix:** Create a `references/` directory and move supporting material there:
- Detailed rubrics → `references/rubrics.md`
- Extended examples → `references/examples.md`
- Configuration reference → `references/config.md`

The SKILL.md should link to these files with `[text](references/filename.md)` so the model
can fetch them on demand.

### ORPHAN_REFERENCE

**Trigger:** SKILL.md contains a markdown link `[text](references/filename)` where
`filename` does not exist in the `references/` directory.

**Problem:** Dead links waste tokens on context that will never resolve and confuse the model.

**Fix:** Either create the missing reference file or remove the dead link.

### DEAD_CROSS_REF

**Trigger:** SKILL.md references another skill or agent by relative path and that path
cannot be resolved from the skills/ directory.

**Problem:** Broken ecosystem links undermine the plugin's coherence score and may cause
the model to attempt navigation to non-existent files.

**Fix:** Verify the referenced skill exists. Update the path or remove the reference.

---

## Elo Ranking

... [skipped or abbreviated remaining to keep it clean]
