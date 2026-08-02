# Report Figures 1–9 Redesign

## Objective

Replace Figures 1–9 referenced by
`report_compilation/Khoa_luan_Streaming_Meeting_Summary_hoan_chinh.md`
with accurate, publication-oriented technical diagrams. The figures must make
the system and methodology easier to understand without repeating the report's
full prose or introducing facts that are not supported by the report and source
code.

## Deliverables

- Nine editable SVG source files in `report_compilation/assets/`.
- Nine high-resolution PNG exports at the existing Markdown image paths.
- Unchanged figure numbering and Vietnamese captions in the report.
- English-only text inside every diagram.
- Automated SVG validation and a visual review of every PNG.

## Shared Visual Grammar

All nine figures use a single restrained academic style based on Fireworks
Tech Graph Style 1:

- pure white background (`#ffffff`);
- near-black primary text (`#111827`) and gray secondary text (`#6b7280`);
- navy/blue borders and primary-flow arrows;
- green only for final outputs or committed states;
- no gradients, shadows, decorative AI imagery, 3D effects, emojis, or product
  logos;
- Arial/Helvetica-compatible sans-serif typography with at least 12 px text;
- short English labels, preferably no more than three words per primary node;
- numbered stages arranged left to right unless a time sequence requires a
  top-to-bottom or three-frame layout;
- orthogonal connectors attached to node edges, with no edge crossings;
- an arrow legend only when a diagram contains more than one arrow semantic;
- no explanatory paragraph inside a figure when the same explanation belongs
  in the report body.

The title band follows one of these forms:

- Figure 1: `SYSTEM OVERVIEW — FIVE-MODULE PIPELINE`
- Figures 2–5: `MODULE 4 — TOPIC SEGMENTATION`
- Figures 6–9: `MODULE 5 — HIERARCHICAL SUMMARIZATION`

A smaller subtitle identifies the specific operation shown by the figure.
Stage names use sentence case and consistent numbering: `1`, `2`, `3`, and so
on. Inputs appear on the left, outputs on the right, and time moves left to
right.

## Content Selection Rule

Include only information that performs at least one of these roles:

1. identifies an input, transformation, state, or output;
2. explains a relationship that cannot be inferred from proximity alone;
3. records a parameter required to understand or reproduce the illustrated
   method;
4. distinguishes pending data from immutable output.

Exclude decorative examples, redundant prose, repeated formulas, evaluation
metrics unrelated to the illustrated operation, implementation filenames,
training statistics, and parameters that are explained in a later focused
figure.

## Figure Specifications

### Figure 1 — Five-Module System Pipeline

Show `Audio Stream` flowing through five numbered modules:
`Audio Preprocessing`, `Speaker Diarization`, `Automatic Speech Recognition`,
`Topic Segmentation`, and `Hierarchical Summarization`. Name the artifact
between modules only when its form materially changes, ending with
`Hierarchical Meeting Recap` containing topic titles and ordered chunk
summaries. Do not show model settings, evaluation metrics, formulas, or the
internal steps of Modules 4 and 5.

### Figure 2 — Topic Segmentation Module

Show the module-level flow:
`Speaker-labelled Utterances` → `Lexical Cohesion` → `Multi-scale Depth` →
`Adaptive Threshold` → `Merge Short Segments` → `Streaming Confirmation` →
`Committed Topic Segments`. Add one restrained lower lane showing that
overlapping windows advance in time and update pending candidates. Do not
repeat formulas or detailed plots from Figures 3–5.

### Figure 3 — Multi-Scale Depth Aggregation

Show four stages:
`Similarity Profile` → `Depth by Radius` → `Z-score Normalization` →
`Mean Aggregation`. Include the radius set `R = {3, 5, 10, 15, 20}`, one
schematic valley demonstrating `S_i`, `p_L`, and `p_R`, and the two equations
needed to connect per-radius depth to aggregated depth. Do not draw a separate
large chart for every radius or add prose explaining what the equations already
show.

### Figure 4 — Adaptive Candidate Selection

Show `Aggregated Depth`, local `Mean and Standard Deviation`, threshold
`tau = mu + alpha sigma`, and the resulting `Candidate Set`. Use one compact
profile to distinguish accepted peaks above the threshold from rejected points.
Do not show multiple alpha-sensitivity charts because they are analysis rather
than part of the processing path.

### Figure 5 — Streaming Boundary Confirmation

Use three chronological frames: `Window t`, `Window t+1`, and `Window t+2`.
Show a boundary moving through `Candidate`, `Pending`, and `Committed` states as
right context becomes available. Include only the commitment condition
`g <= s_t + W - L` and the invariant `Committed boundaries are immutable`.
Do not reproduce the full segmentation pipeline or include decorative state
descriptions.

### Figure 6 — Hierarchical Summarization Module

Show the module overview:
`Committed Topic Segment` → `Non-overlapping Chunks` → `ViT5 Chunk Summaries`
→ `BARTpho Topic Title` → `Hierarchical Recap`. The output must visibly contain
one topic title above ordered chunk summaries. Do not repeat token limits or
decoding parameters covered by Figures 7–9.

### Figure 7 — Utterance Chunking

Use one concrete segment with 21 chronological utterances and group it into
three blocks of `8`, `8`, and `5`. State the three rules compactly:
`Chronological`, `No overlap`, and `Never cross a topic boundary`. Do not list
full utterance text or render 21 verbose cards.

### Figure 8 — ViT5 Chunk Summarization

Show `Speaker-labelled Utterances` → `Task Formatting` → `Tokenization` →
`Fine-tuned ViT5-base` → `Chunk Summary` → `Store and Emit`. The reproducibility
note may include `max input: 512 tokens`, `beam size: 4`, `no sampling`,
`no-repeat 3-gram`, and `max output: 128 tokens`. Do not add training history,
dataset statistics, or multiple example summaries.

### Figure 9 — BARTpho Topic Titling

Show ordered chunk summaries flowing through `Join with " / "`,
`Keep Last 1,500 Characters`, `Add Task Prefix`, `Tokenization`, and
`Fine-tuned BARTpho-syllable-base` to produce `Topic Title`. Show that the title
is generated only after every chunk summary is available. The reproducibility
note may include `max input: 1,024 tokens`, `beam size: 4`, `no sampling`,
`no-repeat 3-gram`, and `max output: 200 tokens`. Do not show raw utterances,
training metrics, or unrelated model internals.

## File and Integration Strategy

The existing PNG filenames remain unchanged so all Markdown references stay
valid. Each PNG gains an SVG source with the same stem:

- `fig01_five_module_pipeline.{svg,png}`
- `fig02_topic_segmentation_module.{svg,png}`
- `fig03_multiscale_depth_score_detail.{svg,png}`
- `fig04_adaptive_threshold_candidates.{svg,png}`
- `fig05_streaming_boundary_confirmation.{svg,png}`
- `fig06_hierarchical_summarization_module.{svg,png}`
- `fig07_utterance_chunking_detail.{svg,png}`
- `fig08_chunk_summarization_detail.{svg,png}`
- `fig09_topic_titling_detail.{svg,png}`

The report body and captions are not rewritten unless a path correction is
required. Existing unrelated working-tree changes must be preserved.

## Validation and Acceptance Criteria

Each figure is complete only when:

1. XML parsing succeeds;
2. Fireworks SVG syntax, marker, geometry, and composition validation succeeds;
3. PNG export succeeds at publication resolution;
4. every visible diagram label is English;
5. the background is pure white and the palette follows the shared grammar;
6. text does not overflow or collide with connectors;
7. connectors do not cross node interiors or each other;
8. a visual review confirms the diagram remains legible at report width;
9. all nine Markdown image paths resolve to the regenerated PNG files.

## Out of Scope

- Redesigning quantitative charts beginning with Figure 10.
- Rewriting the thesis methodology or changing figure captions.
- Changing runtime behavior, model configuration, or training artifacts.
- Introducing new scientific claims not already supported by the report and
  source code.
