# Report Figures 1–9 Redesign Execution Plan

## Objective

Replace report Figures 1–9 with accurate, publication-oriented technical diagrams in editable SVG and report-ready PNG formats. The work follows the approved design specification at [`../../superpowers/specs/2026-08-02-report-figures-1-9-redesign.md`](../../superpowers/specs/2026-08-02-report-figures-1-9-redesign.md).

## Scope

In scope:

- Figures 1–9 and their same-stem SVG and PNG assets in `report_compilation/assets/`.
- The deterministic diagram generator, its tests, artifact validation, and visual review required to produce those assets.
- Preservation of the existing Markdown image paths and Vietnamese captions.

Out of scope:

- Figures 10 and later.
- Report prose, methodology, captions, runtime behavior, model configuration, and training artifacts.

## Current Step

Task 2 — Build the Deterministic Diagram Generator.

## Verification Path

Generate all SVG files:

```bash
uv run python scripts/generate_report_method_diagrams.py --output-dir report_compilation/assets
```

Validate all SVG files with Fireworks:

```bash
for svg in report_compilation/assets/fig0{1,2,3,4,5,6,7,8,9}_*.svg; do
  /home/quangnhvn34/.agents/skills/fireworks-tech-graph/scripts/validate-svg.sh "$svg"
done
```

Export publication-resolution PNG files:

```bash
for svg in report_compilation/assets/fig0{1,2,3,4,5,6,7,8,9}_*.svg; do
  png="${svg%.svg}.png"
  uv run python -c "import cairosvg; cairosvg.svg2png(url='$svg', write_to='$png', output_width=2400)"
done
```

Create the contact sheet for visual review:

```bash
montage report_compilation/assets/fig0{1,2,3,4,5,6,7,8,9}_*.png \
  -thumbnail 600x400 -tile 3x3 -geometry +16+16 -background white \
  /tmp/report-figures-1-9-contact-sheet.png
```

Inspect the contact sheet for title consistency, report-scale text size, overflow, connector routing, arrow-label placement, restrained colors, and English-only copy. Inspect Figures 2, 3, 5, 8, and 9 individually at original detail.

## Risks and Blockers

- Small labels, equations, window lanes, and parameter notes can become illegible at report scale; every dense figure requires individual visual inspection in addition to contact-sheet review.
- This checkout has unrelated staged and unstaged changes. Figure work must not overwrite, restore, stage, or otherwise alter changes outside this plan.
- Baseline tool checks on 2026-08-02 found that neither system `python3` nor `uv run python` can import CairoSVG: `ModuleNotFoundError: No module named 'cairosvg'`. This blocks the Task 5 PNG export until the project dependency environment is repaired.

## Open Decisions

None. The design specification is approved; no content decisions remain open.

## Progress Log

### 2026-08-02

- Confirmed repository root: `/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary`.
- Confirmed `python3 --version` reports `Python 3.12.3` and `montage` resolves to `/usr/bin/montage`.
- Recorded the pre-existing system-Python CairoSVG availability failure: `ModuleNotFoundError: No module named 'cairosvg'`.
- Ran `uv sync` successfully. It resolved 117 packages and removed `hf-transfer==0.1.9`; it also reported that the active `VIRTUAL_ENV` does not match the project `.venv` path.
- Ran `uv run pytest tests/ -q` successfully with no test failures. Pytest emitted the pre-existing `pytest-asyncio` deprecation warning about `asyncio_default_fixture_loop_scope`.
- Confirmed the Task 5 export interpreter has the same pre-existing CairoSVG failure: `uv run python -c "import cairosvg; print(cairosvg.__version__)"` raises `ModuleNotFoundError: No module named 'cairosvg'`.
- Created this active execution record and routed the active-plan index. Next action: Task 2.
