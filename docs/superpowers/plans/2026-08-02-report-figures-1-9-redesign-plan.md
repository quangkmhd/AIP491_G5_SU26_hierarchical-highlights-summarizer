# Report Figures 1–9 Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace report Figures 1–9 with accurate, restrained, English-language technical diagrams in editable SVG and publication-resolution PNG formats.

**Architecture:** A dedicated Python generator owns the shared academic visual grammar and nine figure-specific scene functions. It writes deterministic SVG using the Fireworks-required Python list method; the Fireworks validators then check XML, markers, geometry, and composition before PNG export and visual inspection.

**Tech Stack:** Python 3 standard library, SVG, Fireworks Tech Graph validation scripts, CairoSVG, ImageMagick contact sheets, Markdown.

## Global Constraints

- Follow `docs/superpowers/specs/2026-08-02-report-figures-1-9-redesign.md` exactly.
- Use a pure white background and a restrained navy/gray palette; green is reserved for outputs or committed states.
- All visible text inside Figures 1–9 must be English.
- Preserve the nine existing PNG paths and add an SVG with the same stem.
- Preserve unrelated working-tree changes.
- Do not redesign Figures 10 onward or rewrite the Vietnamese figure captions.
- Every SVG must pass Fireworks syntax, marker, geometry, and composition validation and receive a visual PNG review.

---

### Task 1: Establish the Baseline and Active Execution Record

**Files:**
- Create: `docs/exec-plans/active/report-figures-1-9-redesign.md`
- Modify: `docs/exec-plans/active/index.md`

**Interfaces:**
- Consumes: repository startup workflow in `AGENTS.md` and the approved design spec.
- Produces: a dated progress log and reproducible verification commands for this figure-only change.

- [ ] **Step 1: Confirm repository and tool availability**

Run:

```bash
pwd
python3 --version
python3 -c "import cairosvg; print(cairosvg.__version__)"
command -v montage
```

Expected: the repository root is the meeting-summary project, Python and CairoSVG are available, and `montage` resolves to an executable.

- [ ] **Step 2: Run the standard baseline verification**

Run:

```bash
uv sync
uv run pytest tests/ -q
```

Expected: dependency sync succeeds and the existing suite completes without failures. If the baseline fails, record the exact pre-existing failure before modifying diagram assets.

- [ ] **Step 3: Create the active execution plan**

Create `docs/exec-plans/active/report-figures-1-9-redesign.md` with these concrete sections: objective; Figures 1–9 in scope; Figures 10+ and report prose out of scope; the validation commands from Task 5; risks covering small report-scale text and accidental overwrite of unrelated changes; a progress log beginning on `2026-08-02`; and no open content decisions because the design spec is approved.

- [ ] **Step 4: Route the active plan from the index**

Replace the sentence saying no plan is active with a link to `report-figures-1-9-redesign.md` and identify Task 2 as the current step.

- [ ] **Step 5: Verify the documentation diff**

Run:

```bash
git diff --check -- docs/exec-plans/active/index.md docs/exec-plans/active/report-figures-1-9-redesign.md
```

Expected: exit code 0 and no whitespace errors.

### Task 2: Build the Deterministic Diagram Generator

**Files:**
- Create: `scripts/generate_report_method_diagrams.py`
- Create: `tests/unit/test_report_method_diagrams.py`

**Interfaces:**
- Consumes: figure specifications from the approved design spec.
- Produces: `generate_all(output_dir: Path) -> list[Path]`, returning the nine generated SVG paths in figure order.

- [ ] **Step 1: Write failing generator contract tests**

Add tests that import `generate_all`, generate into `tmp_path`, and assert:

```python
assert [path.suffix for path in outputs] == [".svg"] * 9
assert len(outputs) == 9
assert all(path.exists() for path in outputs)
assert all('<rect width="1200" height="' in path.read_text() for path in outputs)
assert all('fill="#ffffff"' in path.read_text() for path in outputs)
```

Also assert the exact English title family for Figure 1, Figures 2–5, and Figures 6–9, plus the absence of Vietnamese characters in SVG `<text>` elements.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
uv run pytest tests/unit/test_report_method_diagrams.py -q
```

Expected: collection or import failure because the generator does not yet exist.

- [ ] **Step 3: Implement shared SVG primitives**

Implement a dependency-free generator using `lines: list[str]` and `lines.append(...)` for every SVG. Define these exact helpers:

```python
def svg_open(lines: list[str], *, height: int, title: str, subtitle: str) -> None: ...
def svg_close(lines: list[str]) -> None: ...
def add_box(lines: list[str], *, x: int, y: int, width: int, height: int,
            title: str, subtitle: str = "", state: str = "process",
            step: int | None = None) -> None: ...
def add_arrow(lines: list[str], *, x1: int, y1: int, x2: int, y2: int,
              label: str = "", state: str = "flow") -> None: ...
def add_rule_pill(lines: list[str], *, x: int, y: int, width: int,
                  label: str, state: str = "neutral") -> None: ...
def write_svg(lines: list[str], path: Path) -> Path: ...
```

Use a 1200 px-wide viewBox, embedded Arial/Helvetica font stack, white canvas,
`#111827` text, `#1f3a5f` navy borders, `#3b6ea8` primary arrows,
`#6b7280` secondary text, `#f8fafc` neutral panels, and `#2e7d32` only for
outputs/committed states. Define matching arrow markers in `<defs>`.

- [ ] **Step 4: Implement the public generation contract**

Define nine figure functions named `figure_01` through `figure_09`, a fixed
`FIGURES` tuple mapping names to functions, and:

```python
def generate_all(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return [renderer(output_dir / f"{stem}.svg") for stem, renderer in FIGURES]
```

The CLI must default to `report_compilation/assets` and accept an optional
`--output-dir` path.

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/unit/test_report_method_diagrams.py -q
```

Expected: all generator contract tests pass.

### Task 3: Implement Figures 1–5

**Files:**
- Modify: `scripts/generate_report_method_diagrams.py`
- Modify: `tests/unit/test_report_method_diagrams.py`

**Interfaces:**
- Consumes: shared primitives from Task 2.
- Produces: semantic SVG scenes for the five-module overview and Module 4.

- [ ] **Step 1: Add semantic-content tests for Figures 1–5**

Assert that each SVG contains its required labels and excludes its prohibited
detail. Examples:

```python
assert "Audio Preprocessing" in fig1 and "WER" not in fig1
assert "Streaming Confirmation" in fig2 and "tau =" not in fig2
assert "R = {3, 5, 10, 15, 20}" in fig3
assert "Candidate Set" in fig4 and "alpha sensitivity" not in fig4.lower()
assert "Committed boundaries are immutable" in fig5
```

- [ ] **Step 2: Run tests and confirm the new assertions fail**

Run:

```bash
uv run pytest tests/unit/test_report_method_diagrams.py -q
```

Expected: failures identify the figure scenes that still lack their required content.

- [ ] **Step 3: Draw Figure 1**

Create a left-to-right architecture diagram with input, five numbered modules,
and final recap output. Use artifact labels only where the representation
changes: cleaned speech, speaker-labelled audio, speaker-labelled utterances,
committed topics, and hierarchical recap.

- [ ] **Step 4: Draw Figure 2**

Create the seven-stage topic-segmentation flow and a lower streaming lane with
three overlapping window cards. Keep formulas and detailed curves out of this
overview.

- [ ] **Step 5: Draw Figures 3 and 4**

Create Figure 3 with one similarity valley, a compact five-row radius stack,
normalization, and mean aggregation. Create Figure 4 with one depth profile,
the local-statistics card, threshold line, and accepted/rejected candidate
markers.

- [ ] **Step 6: Draw Figure 5**

Create three chronological window frames with the candidate position fixed in
global time and the lookahead region shrinking until the commitment condition
is met. Use green only in the committed frame and invariant callout.

- [ ] **Step 7: Run focused tests**

Run:

```bash
uv run pytest tests/unit/test_report_method_diagrams.py -q
```

Expected: all Figures 1–5 content tests pass.

### Task 4: Implement Figures 6–9

**Files:**
- Modify: `scripts/generate_report_method_diagrams.py`
- Modify: `tests/unit/test_report_method_diagrams.py`

**Interfaces:**
- Consumes: shared primitives from Task 2.
- Produces: semantic SVG scenes for Module 5 and its three focused operations.

- [ ] **Step 1: Add semantic-content tests for Figures 6–9**

Assert required labels and exclusions, including:

```python
assert "Hierarchical Recap" in fig6 and "512 tokens" not in fig6
assert all(label in fig7 for label in ("8 utterances", "5 utterances", "No overlap"))
assert all(label in fig8 for label in ("512 tokens", "ViT5-base", "128 tokens"))
assert all(label in fig9 for label in ("1,500 characters", "1,024 tokens", "BARTpho-syllable-base"))
```

- [ ] **Step 2: Run tests and confirm the new assertions fail**

Run:

```bash
uv run pytest tests/unit/test_report_method_diagrams.py -q
```

Expected: failures identify Figures 6–9 that still lack their required content.

- [ ] **Step 3: Draw Figures 6 and 7**

Create Figure 6 as a concise module overview ending in a nested title-over-
summaries output. Create Figure 7 as a single 21-utterance strip grouped into
three visibly separate blocks of 8, 8, and 5 with three compact rule pills.

- [ ] **Step 4: Draw Figure 8**

Create the six-stage ViT5 inference path. Put the five decoding constraints in
a single footer row so the main flow remains readable.

- [ ] **Step 5: Draw Figure 9**

Create the ordered-summary titling path and a synchronization gate labelled
`All summaries ready` before BARTpho inference. Put decoding constraints in a
single footer row.

- [ ] **Step 6: Run focused tests**

Run:

```bash
uv run pytest tests/unit/test_report_method_diagrams.py -q
```

Expected: all figure-content tests pass.

### Task 5: Generate, Validate, Export, and Review All Artifacts

**Files:**
- Create: `report_compilation/assets/fig01_five_module_pipeline.svg`
- Create: `report_compilation/assets/fig02_topic_segmentation_module.svg`
- Create: `report_compilation/assets/fig03_multiscale_depth_score_detail.svg`
- Create: `report_compilation/assets/fig04_adaptive_threshold_candidates.svg`
- Create: `report_compilation/assets/fig05_streaming_boundary_confirmation.svg`
- Create: `report_compilation/assets/fig06_hierarchical_summarization_module.svg`
- Create: `report_compilation/assets/fig07_utterance_chunking_detail.svg`
- Create: `report_compilation/assets/fig08_chunk_summarization_detail.svg`
- Create: `report_compilation/assets/fig09_topic_titling_detail.svg`
- Replace: the nine same-stem PNG files in `report_compilation/assets/`

**Interfaces:**
- Consumes: deterministic generator output.
- Produces: validated editable sources and report-ready raster assets.

- [ ] **Step 1: Generate all SVG files**

Run:

```bash
uv run python scripts/generate_report_method_diagrams.py --output-dir report_compilation/assets
```

Expected: nine SVG paths are printed in figure order.

- [ ] **Step 2: Validate all SVG files with Fireworks**

Run:

```bash
for svg in report_compilation/assets/fig0{1,2,3,4,5,6,7,8,9}_*.svg; do
  /home/quangnhvn34/.agents/skills/fireworks-tech-graph/scripts/validate-svg.sh "$svg"
done
```

Expected: all nine files pass XML, marker, geometry, and composition checks.

- [ ] **Step 3: Export publication-resolution PNG files**

Run:

```bash
for svg in report_compilation/assets/fig0{1,2,3,4,5,6,7,8,9}_*.svg; do
  png="${svg%.svg}.png"
  uv run python -c "import cairosvg; cairosvg.svg2png(url='$svg', write_to='$png', output_width=2400)"
done
```

Expected: nine 2400 px-wide PNG files replace the current AI-generated assets.

- [ ] **Step 4: Create and inspect a contact sheet**

Run:

```bash
montage report_compilation/assets/fig0{1,2,3,4,5,6,7,8,9}_*.png \
  -thumbnail 600x400 -tile 3x3 -geometry +16+16 -background white \
  /tmp/report-figures-1-9-contact-sheet.png
```

Open the contact sheet with the available image reader and inspect title
consistency, text size, overflow, connector routing, arrow-label placement,
color restraint, and English-only copy. Apply at most two focused correction
passes, regenerating and revalidating after each pass.

- [ ] **Step 5: Inspect each dense figure individually**

Visually inspect Figures 2, 3, 5, 8, and 9 at original detail because their
window lanes, formulas, or parameter notes may be too small to judge on the
contact sheet.

### Task 6: Verify Integration and Close the Plan

**Files:**
- Modify: `docs/exec-plans/active/report-figures-1-9-redesign.md`
- Modify: `docs/exec-plans/active/index.md`
- Move when complete: `docs/exec-plans/active/report-figures-1-9-redesign.md` to `docs/exec-plans/completed/report-figures-1-9-redesign.md`
- Modify only if materially warranted: `docs/QUALITY_SCORE.md`

**Interfaces:**
- Consumes: final SVG/PNG artifacts and verification evidence.
- Produces: a restartable repository with recorded evidence and no active plan for completed work.

- [ ] **Step 1: Verify Markdown paths and artifact completeness**

Run:

```bash
uv run python - <<'PY'
from pathlib import Path
import re

report = Path("report_compilation/Khoa_luan_Streaming_Meeting_Summary_hoan_chinh.md")
text = report.read_text(encoding="utf-8")
paths = re.findall(r"!\[[^]]*\]\((assets/fig0[1-9]_[^)]+\.png)\)", text)
assert len(paths) == 9, paths
for relative in paths:
    png = report.parent / relative
    svg = png.with_suffix(".svg")
    assert png.is_file(), png
    assert svg.is_file(), svg
print("verified 9 PNG and 9 SVG report assets")
PY
```

Expected: `verified 9 PNG and 9 SVG report assets`.

- [ ] **Step 2: Run focused and full verification**

Run:

```bash
uv run pytest tests/unit/test_report_method_diagrams.py -q
uv run pytest tests/ -q
git diff --check
```

Expected: focused tests and full suite pass, and no whitespace errors are introduced.

- [ ] **Step 3: Record evidence and archive the active plan**

Append the exact test counts, validation results, PNG dimensions, and
`visual_review: passed` to the progress log. Add a `Verification at archive
time` section, move the plan to `docs/exec-plans/completed/`, and reset
`docs/exec-plans/active/index.md` to state that no execution plan is active.

- [ ] **Step 4: Review the final scoped diff**

Run:

```bash
git status --short
git diff --stat -- scripts/generate_report_method_diagrams.py tests/unit/test_report_method_diagrams.py report_compilation/assets docs/exec-plans docs/QUALITY_SCORE.md
```

Expected: only the generator, its tests, Figure 1–9 assets, and lifecycle docs
from this plan appear in the scoped change; unrelated pre-existing changes
remain untouched.
