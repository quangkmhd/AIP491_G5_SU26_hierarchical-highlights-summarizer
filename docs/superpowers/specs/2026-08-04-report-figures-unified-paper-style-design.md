# Unified Paper Style for Remaining Report Figures

## Objective

Redesign the remaining figures in the report figure series so they use the
same publication-oriented visual grammar approved for the revised topic
segmentation overview. The redesign must improve immediate comprehension,
make module hierarchy explicit, and remove decorative or redundant content
without changing the method described by the report.

## Scope

The following seven assets are redesigned:

- `fig01_five_module_pipeline.png`
- `fig02_overall_software_architecture.png`
- `fig06_hierarchical_summarization_module.png`
- `fig07_utterance_chunking_detail.png`
- `fig08_chunk_summarization_detail.png`
- `fig09_topic_titling_detail.png`
- `fig10_event_sequence.png`

The four approved topic-segmentation figures are frozen and must not be
regenerated:

- `fig02_topic_segmentation_module.png`
- `fig03_multiscale_depth_score_detail.png`
- `fig04_adaptive_threshold_candidates.png`
- `fig05_streaming_boundary_confirmation.png`

Dataset distributions, training-history charts, evaluation charts, and other
assets outside the Figure 1--10 method series are out of scope.

## Shared Visual Grammar

All redesigned figures use:

- a pure white background;
- near-black primary text and dark navy outlines and arrows;
- muted gray for secondary or pending information;
- muted green only for final outputs or committed states;
- flat two-dimensional geometry with no gradients, drop shadows, 3D effects,
  decorative icons, logos, or watermarks;
- concise English labels in an Arial/Helvetica-compatible sans-serif face;
- generous whitespace and text sized for legibility at report width;
- a left-to-right reading direction except when a layered architecture or
  chronological sequence communicates the method more accurately;
- input and output endpoints visually distinguished from processing modules;
- numbered module cards when the report defines an explicit module sequence.

Every figure must communicate one primary relationship at a glance. It must
not repeat explanatory paragraphs, evaluation metrics, implementation
filenames, or parameters that belong to another focused figure.

## Figure Designs

### Figure 1: Five-Module System Pipeline

Show `Audio Stream` as an input endpoint, followed by one framed group titled
`FIVE PROCESSING MODULES`. Inside the group, show five numbered modules:
`1 Audio Preprocessing`, `2 Speaker Diarization`, `3 Automatic Speech
Recognition`, `4 Topic Segmentation`, and `5 Hierarchical Summarization`.
End with a separate green output endpoint, `Hierarchical Meeting Recap`.
Artifact labels may appear beneath arrows only where the representation changes
materially. Do not show model names, metrics, or internal substeps.

### Figure 2: Overall Software Architecture

Use four horizontal layers: `Client`, `Application Runtime`, `AI Services`, and
`Local Model Runtime`. The client communicates with the FastAPI runtime; the
runtime communicates with the streaming orchestrator; the orchestrator calls
the five numbered AI modules; model-backed services connect downward to their
local runtimes. Emphasize one primary streaming data path. Avoid product-style
icons, infrastructure decoration, and crossed connectors.

### Figure 6: Hierarchical Summarization Module

Use one framed group titled `HIERARCHICAL SUMMARIZATION` containing three
numbered internal stages: `1 Non-overlapping Chunks`, `2 ViT5 Chunk Summaries`,
and `3 BARTpho Topic Title`. Keep `Committed Topic Segment` and `Hierarchical
Recap` outside the group as input and output. The output visibly places one
topic title above ordered chunk summaries. Do not include decoding parameters.

### Figure 7: Utterance Chunking

Show one committed topic segment as a chronological strip of 21 compact
utterance cells. Group the cells into three adjacent blocks labelled
`Chunk 1 — 8 utterances`, `Chunk 2 — 8 utterances`, and
`Chunk 3 — 5 utterances`. Add only three compact rules: `Chronological`,
`No overlap`, and `Never cross a topic boundary`. Do not render full utterance
text.

### Figure 8: ViT5 Chunk Summarization

Show a numbered processing flow from `Speaker-labelled Utterances` through
`Task Formatting`, `Tokenization`, `Fine-tuned ViT5-base`, and `Store and Emit`
to the green `Chunk Summary` output. Place reproducibility settings in one
small secondary note: `512-token input`, `beam size 4`, `no sampling`,
`no-repeat 3-gram`, and `128-token output`. Do not include training history or
dataset statistics.

### Figure 9: BARTpho Topic Titling

Show ordered chunk summaries flowing through `Join with " / "`,
`Keep Last 1,500 Characters`, `Add Task Prefix`, `Tokenization`, and
`Fine-tuned BARTpho-syllable-base` to a green `Topic Title` output. Make the
precondition `All chunk summaries available` visually explicit. Place the
reproducibility settings in one small secondary note: `1,024-token input`,
`beam size 4`, `no sampling`, `no-repeat 3-gram`, and `200-token output`.

### Figure 10: Streaming Event Sequence

Use a compact left-to-right sequence/swimlane diagram with six participants:
`Transcript`, `Orchestrator`, `Segmenter`, `ViT5`, `BARTpho`, and `Output`.
Show only the events required to understand incremental operation:
`utterance-accepted`, boundary commitment, repeated chunk summarization,
`chunk-closed`, `segment-closed`, `title-emitted`, and
`meeting-completed`. Use solid arrows for processing calls, dashed arrows for
returns, and green only for emitted final or committed events. Include a small
two-item arrow legend. Do not reproduce payload schemas or implementation
method names.

## Output and Integration

Each result is a high-resolution landscape PNG saved over its existing target
filename because the user explicitly requested replacement. Existing SVG and
PDF sources are not treated as the generated-image deliverable and must not be
silently presented as matching editable sources after the PNG redesign. Report
Markdown paths and Vietnamese captions remain unchanged.

## Validation

Each asset is accepted only when:

1. the PNG exists and is at least 1,700 pixels wide and 800 pixels high;
2. every required label is correctly spelled and no extra AI-generated text is
   visible;
3. the number and hierarchy of modules match the report;
4. input, transformations, and output can be identified immediately;
5. arrows have a consistent direction and do not cross text or node interiors;
6. the figure remains readable in a contact sheet at approximate report scale;
7. its report reference resolves to the regenerated file where applicable;
8. the four approved topic-segmentation figures remain byte-for-byte unchanged
   during this phase.

## Non-Goals

- Rewriting report prose, captions, formulas, or scientific claims.
- Changing runtime code or model configuration.
- Redesigning experimental charts outside the Figure 1--10 method series.
- Adding decorative imagery merely to make figures more colorful.
