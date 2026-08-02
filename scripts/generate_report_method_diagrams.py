"""Generate the editable SVG foundation for report Figures 1–9."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from html import escape
from pathlib import Path


CANVAS_WIDTH = 1200
TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#6b7280"
BORDER_NAVY = "#1f3a5f"
ARROW_PRIMARY = "#3b6ea8"
PANEL_NEUTRAL = "#f8fafc"
OUTPUT_GREEN = "#2e7d32"


def svg_open(lines: list[str], *, height: int, title: str, subtitle: str) -> None:
    """Start an SVG with the report-wide visual grammar and title band."""
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_WIDTH} {height}" '
        f'width="{CANVAS_WIDTH}" height="{height}">'
    )
    lines.append("<style>")
    lines.append("text { font-family: Arial, Helvetica, sans-serif; }")
    lines.append("</style>")
    lines.append("<defs>")
    lines.append(
        f'<marker id="arrow-primary" markerWidth="10" markerHeight="8" refX="9" '
        f'refY="4" orient="auto"><polygon points="0,0 10,4 0,8" '
        f'fill="{ARROW_PRIMARY}"/></marker>'
    )
    lines.append(
        f'<marker id="arrow-output" markerWidth="10" markerHeight="8" refX="9" '
        f'refY="4" orient="auto"><polygon points="0,0 10,4 0,8" '
        f'fill="{OUTPUT_GREEN}"/></marker>'
    )
    lines.append("</defs>")
    lines.append(f'<rect width="{CANVAS_WIDTH}" height="{height}" fill="#ffffff"/>')
    lines.append(
        f'<text x="60" y="58" font-size="22" font-weight="700" '
        f'fill="{TEXT_PRIMARY}">{escape(title)}</text>'
    )
    lines.append(
        f'<text x="60" y="86" font-size="14" fill="{TEXT_SECONDARY}">{escape(subtitle)}</text>'
    )
    lines.append(
        f'<line x1="60" y1="108" x2="1140" y2="108" stroke="{BORDER_NAVY}" '
        'stroke-width="2"/>'
    )


def svg_close(lines: list[str]) -> None:
    """Finish an SVG document."""
    lines.append("</svg>")


def add_box(
    lines: list[str],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    subtitle: str = "",
    state: str = "process",
    step: int | None = None,
) -> None:
    """Add a numbered process or output card to an SVG scene."""
    is_output = state in {"output", "committed"}
    fill = "#f0fdf4" if is_output else PANEL_NEUTRAL
    stroke = OUTPUT_GREEN if is_output else BORDER_NAVY
    lines.append(
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    )
    text_x = x + 18
    if step is not None:
        lines.append(
            f'<circle cx="{x + 26}" cy="{y + 27}" r="14" fill="{stroke}"/>'
        )
        lines.append(
            f'<text x="{x + 26}" y="{y + 32}" text-anchor="middle" font-size="13" '
            'font-weight="700" fill="#ffffff">'
            f"{step}</text>"
        )
        text_x = x + 50
    lines.append(
        f'<text x="{text_x}" y="{y + 33}" font-size="16" font-weight="700" '
        f'fill="{TEXT_PRIMARY}">'
        f"{escape(title)}</text>"
    )
    if subtitle:
        lines.append(
            f'<text x="{text_x}" y="{y + 57}" font-size="13" fill="{TEXT_SECONDARY}">'
            f"{escape(subtitle)}</text>"
        )


def add_arrow(
    lines: list[str],
    *,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    label: str = "",
    state: str = "flow",
) -> None:
    """Add a labelled connector with a matching primary or output marker."""
    is_output = state in {"output", "committed"}
    stroke = OUTPUT_GREEN if is_output else ARROW_PRIMARY
    marker = "arrow-output" if is_output else "arrow-primary"
    lines.append(
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
        f'stroke-width="2.5" marker-end="url(#{marker})"/>'
    )
    if label:
        label_x = (x1 + x2) // 2
        label_y = (y1 + y2) // 2 - 10
        lines.append(
            f'<text x="{label_x}" y="{label_y}" text-anchor="middle" font-size="12" '
            f'fill="{TEXT_SECONDARY}">{escape(label)}</text>'
        )


def add_rule_pill(
    lines: list[str],
    *,
    x: int,
    y: int,
    width: int,
    label: str,
    state: str = "neutral",
) -> None:
    """Add a compact rule or reproducibility note."""
    is_output = state in {"output", "committed"}
    fill = "#f0fdf4" if is_output else PANEL_NEUTRAL
    stroke = OUTPUT_GREEN if is_output else BORDER_NAVY
    lines.append(
        f'<rect x="{x}" y="{y}" width="{width}" height="30" rx="15" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"/>'
    )
    lines.append(
        f'<text x="{x + width // 2}" y="{y + 20}" text-anchor="middle" font-size="12" '
        f'fill="{TEXT_SECONDARY}">{escape(label)}</text>'
    )


def write_svg(lines: list[str], path: Path) -> Path:
    """Write one complete deterministic SVG document and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _render_foundation(path: Path, *, title: str, subtitle: str) -> Path:
    """Render the shared scene shell that later tasks populate with content."""
    lines: list[str] = []
    svg_open(lines, height=360, title=title, subtitle=subtitle)
    add_box(
        lines,
        x=420,
        y=160,
        width=360,
        height=96,
        title="Method diagram",
        subtitle="Detailed scene follows the shared visual grammar",
    )
    svg_close(lines)
    return write_svg(lines, path)


def figure_01(path: Path) -> Path:
    return _render_foundation(
        path,
        title="SYSTEM OVERVIEW — FIVE-MODULE PIPELINE",
        subtitle="End-to-end processing route",
    )


def figure_02(path: Path) -> Path:
    return _render_foundation(
        path,
        title="MODULE 4 — TOPIC SEGMENTATION",
        subtitle="Topic segmentation module overview",
    )


def figure_03(path: Path) -> Path:
    return _render_foundation(
        path,
        title="MODULE 4 — TOPIC SEGMENTATION",
        subtitle="Multi-scale depth aggregation",
    )


def figure_04(path: Path) -> Path:
    return _render_foundation(
        path,
        title="MODULE 4 — TOPIC SEGMENTATION",
        subtitle="Adaptive candidate selection",
    )


def figure_05(path: Path) -> Path:
    return _render_foundation(
        path,
        title="MODULE 4 — TOPIC SEGMENTATION",
        subtitle="Streaming boundary confirmation",
    )


def figure_06(path: Path) -> Path:
    return _render_foundation(
        path,
        title="MODULE 5 — HIERARCHICAL SUMMARIZATION",
        subtitle="Hierarchical summarization module overview",
    )


def figure_07(path: Path) -> Path:
    return _render_foundation(
        path,
        title="MODULE 5 — HIERARCHICAL SUMMARIZATION",
        subtitle="Utterance chunking",
    )


def figure_08(path: Path) -> Path:
    return _render_foundation(
        path,
        title="MODULE 5 — HIERARCHICAL SUMMARIZATION",
        subtitle="ViT5 chunk summarization",
    )


def figure_09(path: Path) -> Path:
    return _render_foundation(
        path,
        title="MODULE 5 — HIERARCHICAL SUMMARIZATION",
        subtitle="BARTpho topic titling",
    )


FIGURES: tuple[tuple[str, Callable[[Path], Path]], ...] = (
    ("fig01_five_module_pipeline", figure_01),
    ("fig02_topic_segmentation_module", figure_02),
    ("fig03_multiscale_depth_score_detail", figure_03),
    ("fig04_adaptive_threshold_candidates", figure_04),
    ("fig05_streaming_boundary_confirmation", figure_05),
    ("fig06_hierarchical_summarization_module", figure_06),
    ("fig07_utterance_chunking_detail", figure_07),
    ("fig08_chunk_summarization_detail", figure_08),
    ("fig09_topic_titling_detail", figure_09),
)


def generate_all(output_dir: Path) -> list[Path]:
    """Generate the nine report SVGs in their fixed figure order."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return [renderer(output_dir / f"{stem}.svg") for stem, renderer in FIGURES]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("report_compilation/assets"),
        help="Directory for generated SVG files.",
    )
    args = parser.parse_args()
    for path in generate_all(args.output_dir):
        print(path)


if __name__ == "__main__":
    main()
