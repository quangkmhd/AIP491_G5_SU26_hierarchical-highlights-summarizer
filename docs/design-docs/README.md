# Design Documents

This directory holds **core architecture decisions, research hypotheses, and design beliefs** for the dialogue topic segmentation + meeting recap system.

## What goes here

- Architecture decision records (ADR format)
- Research hypotheses being tested
- Core algorithm designs (coherence scoring, segmentation, summarization)
- Data flow diagrams and pipeline architecture
- Integration design between coherence scoring and meeting recap

## What does NOT go here

- Execution plans (→ `docs/exec-plans/`)
- Auto-generated output (→ `docs/generated/`)
- External library docs (→ `docs/references/`)

## Rule

When making a structural decision that future agents need to understand, write it here. A decision not documented = a decision that doesn't exist for the next agent session.