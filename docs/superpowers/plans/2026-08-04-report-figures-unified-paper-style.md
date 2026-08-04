# Unified Paper Style for Remaining Report Figures Implementation Plan

> **Status (2026-08-04): Complete.** Seven target PNGs were regenerated and visually reviewed; all meet the minimum dimensions, all six report references resolve, Figure 10 remains an auxiliary unreferenced asset, and the four protected topic-segmentation PNGs retain their recorded checksums.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the seven remaining Figure 1--10 method assets with accurate, high-resolution academic diagrams that match the approved topic-segmentation visual grammar.

**Architecture:** Each figure is generated independently with the built-in image generation workflow from a content-locked prompt derived from the approved design. Generated candidates are staged outside the target path, inspected individually and in a report-scale contact sheet, then copied over the existing PNG only after passing semantic and visual checks. A checksum guard protects the four approved topic-segmentation figures throughout execution.

**Tech Stack:** Built-in image generation, PNG, ImageMagick `identify` and `montage`, shell validation, Markdown report references.

## Global Constraints

- Follow `docs/superpowers/specs/2026-08-04-report-figures-unified-paper-style-design.md` exactly.
- Use pure white backgrounds, near-black text, navy outlines/arrows, gray secondary information, and muted green only for final or committed states.
- Use concise English text inside figures and retain existing Vietnamese report captions.
- Do not change `fig02_topic_segmentation_module.png`, `fig03_multiscale_depth_score_detail.png`, `fig04_adaptive_threshold_candidates.png`, or `fig05_streaming_boundary_confirmation.png`.
- Do not redesign dataset, training-history, or evaluation charts.
- Preserve unrelated working-tree changes.
- Use one built-in image-generation call per distinct figure; do not use CLI fallback.

---

### Task 1: Establish Content and Integrity Baselines

**Files:**
- Read: `report_compilation/Khoa_luan_Streaming_Meeting_Summary_hoan_chinh.md`
- Read: `docs/superpowers/specs/2026-08-04-report-figures-unified-paper-style-design.md`
- Create: `tmp/imagegen/report-figures-2026-08-04/protected.sha256`

**Interfaces:**
- Consumes: approved figure design and report captions.
- Produces: immutable checksums for the four completed figures and a staging directory for generated candidates.

- [x] **Step 1: Create a staging directory**

Run:

```bash
mkdir -p tmp/imagegen/report-figures-2026-08-04
```

Expected: the directory exists and no report asset is modified.

- [x] **Step 2: Record protected-figure checksums**

Run:

```bash
sha256sum \
  report_compilation/assets/fig02_topic_segmentation_module.png \
  report_compilation/assets/fig03_multiscale_depth_score_detail.png \
  report_compilation/assets/fig04_adaptive_threshold_candidates.png \
  report_compilation/assets/fig05_streaming_boundary_confirmation.png \
  > tmp/imagegen/report-figures-2026-08-04/protected.sha256
```

Expected: four checksum lines are written.

- [x] **Step 3: Confirm the target files and report references**

Run:

```bash
for file in \
  fig01_five_module_pipeline.png \
  fig02_overall_software_architecture.png \
  fig06_hierarchical_summarization_module.png \
  fig07_utterance_chunking_detail.png \
  fig08_chunk_summarization_detail.png \
  fig09_topic_titling_detail.png \
  fig10_event_sequence.png; do
  test -s "report_compilation/assets/$file"
done
```

Expected: exit code 0.

### Task 2: Generate the System-Level Figures

**Files:**
- Modify: `report_compilation/assets/fig01_five_module_pipeline.png`
- Modify: `report_compilation/assets/fig02_overall_software_architecture.png`

**Interfaces:**
- Consumes: Figure 1 and Figure 2 content specifications.
- Produces: the five-module overview and layered runtime architecture diagrams.

- [x] **Step 1: Generate Figure 1 into staging**

Use the built-in image-generation tool with the exact module sequence from the design. Require a separate input endpoint, a framed group containing exactly five numbered module cards, and a separate green output endpoint. Save the candidate as `tmp/imagegen/report-figures-2026-08-04/fig01_five_module_pipeline.png`.

- [x] **Step 2: Validate Figure 1 visually**

Confirm all labels are spelled correctly, numbers 1--5 occur once, input/output are outside the module frame, arrows flow left-to-right, and no unrequested labels are present. Regenerate once with a targeted correction if any check fails.

- [x] **Step 3: Generate Figure 2 into staging**

Use the built-in image-generation tool with four horizontal layers: Client, Application Runtime, AI Services, and Local Model Runtime. Require exactly five numbered AI modules, one primary streaming path, orthogonal connectors, and no product icons. Save the candidate as `tmp/imagegen/report-figures-2026-08-04/fig02_overall_software_architecture.png`.

- [x] **Step 4: Validate Figure 2 visually**

Confirm every component belongs to the correct layer, the five-module ordering matches the report, connectors do not cross text, and decorative infrastructure is absent. Regenerate once with a targeted correction if any check fails.

- [x] **Step 5: Install the accepted system figures**

Copy the two accepted candidates to their existing `report_compilation/assets/` paths. Overwriting is authorized by the user's redesign request.

### Task 3: Generate the Hierarchical Summarization Overview and Chunking Figure

**Files:**
- Modify: `report_compilation/assets/fig06_hierarchical_summarization_module.png`
- Modify: `report_compilation/assets/fig07_utterance_chunking_detail.png`

**Interfaces:**
- Consumes: report Sections 3.6 and 3.6.1.
- Produces: one three-stage summarization overview and one exact 21-utterance chunking diagram.

- [x] **Step 1: Generate Figure 6 into staging**

Require one external committed-topic input, one framed group containing exactly three numbered stages, and one external hierarchical-recap output with a title above ordered summaries. Save as `tmp/imagegen/report-figures-2026-08-04/fig06_hierarchical_summarization_module.png`.

- [x] **Step 2: Validate Figure 6 visually**

Confirm the stage order is chunking, ViT5 summaries, BARTpho title; input/output are outside the group; and no inference parameters appear.

- [x] **Step 3: Generate Figure 7 into staging**

Require exactly 21 compact utterance cells grouped 8, 8, and 5, plus the rules Chronological, No overlap, and Never cross a topic boundary. Save as `tmp/imagegen/report-figures-2026-08-04/fig07_utterance_chunking_detail.png`.

- [x] **Step 4: Validate Figure 7 visually**

Count all cells and verify the group sizes are exactly 8, 8, and 5. Reject any candidate with full utterance prose, crossed boundaries, or extra rules.

- [x] **Step 5: Install the accepted overview and chunking figures**

Copy the two accepted candidates to their existing report asset paths.

### Task 4: Generate the ViT5 and BARTpho Detail Figures

**Files:**
- Modify: `report_compilation/assets/fig08_chunk_summarization_detail.png`
- Modify: `report_compilation/assets/fig09_topic_titling_detail.png`

**Interfaces:**
- Consumes: report Sections 3.6.2 and 3.6.3.
- Produces: content-locked model inference diagrams with compact reproducibility notes.

- [x] **Step 1: Generate Figure 8 into staging**

Require the ordered flow Speaker-labelled Utterances, Task Formatting, Tokenization, Fine-tuned ViT5-base, Store and Emit, and Chunk Summary. Include one secondary settings note containing 512-token input, beam size 4, no sampling, no-repeat 3-gram, and 128-token output. Save as `tmp/imagegen/report-figures-2026-08-04/fig08_chunk_summarization_detail.png`.

- [x] **Step 2: Validate Figure 8 visually**

Confirm model name, settings, and stage order exactly match the report; ensure the green output is the only emphasized state.

- [x] **Step 3: Generate Figure 9 into staging**

Require ordered chunk summaries, the explicit all-summaries-available precondition, join separator, 1,500-character tail, task prefix, tokenization, fine-tuned BARTpho-syllable-base, and Topic Title. Include the specified 1,024-token/beam/no-sampling/no-repeat/200-token settings note. Save as `tmp/imagegen/report-figures-2026-08-04/fig09_topic_titling_detail.png`.

- [x] **Step 4: Validate Figure 9 visually**

Confirm exact punctuation in `" / "`, model name, limits, chronological order, and the precondition before title generation.

- [x] **Step 5: Install the accepted model figures**

Copy the two accepted candidates to their existing report asset paths.

### Task 5: Generate the Streaming Event Sequence

**Files:**
- Modify: `report_compilation/assets/fig10_event_sequence.png`

**Interfaces:**
- Consumes: the approved Figure 10 event list and runtime participants.
- Produces: a compact swimlane diagram distinguishing calls, returns, and emitted events.

- [x] **Step 1: Generate Figure 10 into staging**

Require six participants and only the approved event vocabulary. Use solid arrows for processing calls, dashed arrows for returns, green emitted/committed events, and a two-item legend. Save as `tmp/imagegen/report-figures-2026-08-04/fig10_event_sequence.png`.

- [x] **Step 2: Validate Figure 10 visually**

Confirm participant order, chronological top-to-bottom event order, consistent arrow semantics, exact event spelling, and absence of payload schemas or method names.

- [x] **Step 3: Install the accepted event-sequence figure**

Copy the accepted candidate to `report_compilation/assets/fig10_event_sequence.png`.

### Task 6: Publication-Scale Verification and Handoff

**Files:**
- Verify: all seven redesigned PNGs
- Verify: four protected topic-segmentation PNGs
- Create: `tmp/imagegen/report-figures-2026-08-04/contact-sheet.png`
- Modify: `docs/exec-plans/completed/report-figures-1-9-redesign.md` only if evidence logging is required by the active report-figure plan

**Interfaces:**
- Consumes: all accepted image candidates.
- Produces: fresh dimension, reference, checksum, and visual-review evidence.

- [x] **Step 1: Validate minimum dimensions**

Run `identify` for all seven target images and fail if any width is below 1,700 pixels or height below 800 pixels.

- [x] **Step 2: Verify report references**

For every redesigned asset referenced in the report, use `rg` to confirm its existing Markdown path resolves. Record that `fig10_event_sequence.png` is an auxiliary asset if it remains unreferenced.

- [x] **Step 3: Verify protected checksums**

Run:

```bash
sha256sum --check tmp/imagegen/report-figures-2026-08-04/protected.sha256
```

Expected: all four protected figures report `OK`.

- [x] **Step 4: Create and inspect a contact sheet**

Use ImageMagick `montage` to arrange the seven redesigned figures at report-like thumbnail scale. Inspect the result for small text, inconsistent stroke weight, unintended color, clipping, and cross-figure style drift.

- [x] **Step 5: Inspect the final diff**

Run:

```bash
git status --short
git diff --stat -- report_compilation/assets
```

Expected: the seven intended PNGs are modified; unrelated changes are preserved and unmodified by this work.

- [x] **Step 6: Report deliverables**

Provide clickable paths to all seven PNGs, identify the built-in image generation mode, state the verification results, and note that existing SVG/PDF files were not regenerated and therefore are not matching editable sources for the new raster artwork.
