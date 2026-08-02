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


def add_text(
    lines: list[str],
    *,
    x: int,
    y: int,
    text: str,
    size: int = 13,
    fill: str = TEXT_PRIMARY,
    weight: int = 400,
    anchor: str = "start",
) -> None:
    """Add one escaped SVG text label."""
    lines.append(
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{escape(text)}</text>'
    )


def add_multiline_text(
    lines: list[str],
    *,
    x: int,
    y: int,
    text: str,
    size: int = 13,
    fill: str = TEXT_PRIMARY,
    weight: int = 400,
    anchor: str = "middle",
    line_height: int = 17,
) -> None:
    """Add compact multiline text while preserving its readable phrase."""
    parts = text.split("\n")
    spans = []
    for index, part in enumerate(parts):
        separator = " " if index < len(parts) - 1 else ""
        offset = 0 if index == 0 else line_height
        spans.append(
            f'<tspan x="{x}" dy="{offset}">{escape(part + separator)}</tspan>'
        )
    lines.append(
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{"".join(spans)}</text>'
    )


def add_panel(
    lines: list[str],
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    state: str = "process",
) -> None:
    """Add a restrained semantic frame with a compact header."""
    is_output = state in {"output", "committed"}
    fill = "#f0fdf4" if is_output else PANEL_NEUTRAL
    stroke = OUTPUT_GREEN if is_output else BORDER_NAVY
    lines.append(
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    )
    add_text(
        lines,
        x=x + 18,
        y=y + 30,
        text=title,
        size=18,
        fill=stroke,
        weight=700,
    )
    lines.append(
        f'<line x1="{x + 18}" y1="{y + 44}" x2="{x + width - 18}" '
        f'y2="{y + 44}" stroke="{stroke}" stroke-width="1" opacity="0.35"/>'
    )


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
        f'<text x="60" y="58" font-size="28" font-weight="700" '
        f'fill="{TEXT_PRIMARY}">{escape(title)}</text>'
    )
    lines.append(
        f'<text x="60" y="88" font-size="17" fill="{TEXT_SECONDARY}">{escape(subtitle)}</text>'
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
    if step is not None:
        lines.append(
            f'<circle cx="{x + 22}" cy="{y + 22}" r="13" fill="{stroke}" '
            f'data-step="{step}"/>'
        )
        lines.append(
            f'<text x="{x + 22}" y="{y + 27}" text-anchor="middle" font-size="14" '
            'font-weight="700" fill="#ffffff">'
            f"{step}</text>"
        )
        text_x = x + width // 2
        title_y = y + 55
        title_size = 14
        title_anchor = "middle"
    else:
        text_x = x + 18
        title_y = y + 31
        title_size = 16
        title_anchor = "start"
    title_lines = title.split("\n")
    add_multiline_text(
        lines,
        x=text_x,
        y=title_y,
        text=title,
        size=title_size,
        fill=TEXT_PRIMARY,
        weight=700,
        anchor=title_anchor,
        line_height=18,
    )
    if subtitle:
        add_text(
            lines,
            x=text_x,
            y=title_y + 26 + (len(title_lines) - 1) * 18,
            text=subtitle,
            size=13,
            fill=TEXT_SECONDARY,
            anchor=title_anchor,
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
            f'<text x="{label_x}" y="{label_y}" text-anchor="middle" font-size="13" '
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
        f'<rect x="{x}" y="{y}" width="{width}" height="34" rx="17" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"/>'
    )
    lines.append(
        f'<text x="{x + width // 2}" y="{y + 23}" text-anchor="middle" font-size="14" '
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
    lines: list[str] = []
    svg_open(
        lines,
        height=560,
        title="SYSTEM OVERVIEW — FIVE-MODULE PIPELINE",
        subtitle="End-to-end processing route",
    )
    nodes = (
        (35, 115, "Audio\nStream", "", "process", None),
        (180, 130, "Audio\nPreprocessing", "", "process", 1),
        (340, 130, "Speaker\nDiarization", "", "process", 2),
        (500, 130, "Automatic Speech\nRecognition", "", "process", 3),
        (660, 130, "Topic\nSegmentation", "", "process", 4),
        (820, 130, "Hierarchical\nSummarization", "", "process", 5),
        (
            990,
            175,
            "Hierarchical\nMeeting Recap",
            "title + ordered summaries",
            "output",
            None,
        ),
    )
    centers = []
    for x, width, title, subtitle, state, step in nodes:
        centers.append((x, width))
        add_box(
            lines,
            x=x,
            y=185,
            width=width,
            height=112,
            title=title,
            subtitle=subtitle,
            state=state,
            step=step,
        )
    for index, ((x, width), (next_x, _)) in enumerate(
        zip(centers[:-1], centers[1:], strict=True)
    ):
        add_arrow(
            lines,
            x1=x + width,
            y1=241,
            x2=next_x,
            y2=241,
            state="output" if index == len(centers) - 2 else "flow",
        )
    artifacts = (
        (325, "cleaned\nspeech"),
        (485, "speaker-labelled\naudio"),
        (645, "speaker-labelled\nutterances"),
        (805, "committed\ntopics"),
        (970, "hierarchical\nrecap"),
    )
    add_text(
        lines,
        x=60,
        y=375,
        text="Representation changes",
        size=12,
        fill=TEXT_SECONDARY,
        weight=700,
    )
    for x, label in artifacts:
        lines.append(
            f'<line x1="{x}" y1="320" x2="{x}" y2="342" stroke="{BORDER_NAVY}" '
            'stroke-width="1"/>'
        )
        lines.append(f'<circle cx="{x}" cy="320" r="3" fill="{BORDER_NAVY}"/>')
        add_multiline_text(
            lines,
            x=x,
            y=363,
            text=label,
            size=12,
            fill=TEXT_SECONDARY,
            weight=600,
        )
    svg_close(lines)
    return write_svg(lines, path)


def figure_02(path: Path) -> Path:
    lines: list[str] = []
    svg_open(
        lines,
        height=650,
        title="MODULE 4 — TOPIC SEGMENTATION",
        subtitle="Topic segmentation module overview",
    )
    stages = (
        (30, 120, "Speaker\ntagged\nUtterances", "process", None),
        (175, 150, "Lexical\nCohesion", "process", 1),
        (350, 150, "Multi-scale\nDepth", "process", 2),
        (525, 150, "Adaptive\nThreshold", "process", 3),
        (700, 150, "Merge Short\nSegments", "process", 4),
        (875, 150, "Streaming\nConfirmation", "process", 5),
        (1050, 120, "Committed\nTopic\nSegments", "output", None),
    )
    for x, width, title, state, step in stages:
        add_box(
            lines,
            x=x,
            y=160,
            width=width,
            height=112,
            title=title,
            state=state,
            step=step,
        )
    for index in range(len(stages) - 1):
        add_arrow(
            lines,
            x1=stages[index][0] + stages[index][1],
            y1=216,
            x2=stages[index + 1][0],
            y2=216,
            state="output" if index == len(stages) - 2 else "flow",
        )
    add_panel(
        lines,
        x=95,
        y=335,
        width=1010,
        height=245,
        title="Streaming windows",
    )
    add_text(
        lines,
        x=1080,
        y=365,
        text="same ID + fill = repeated context",
        size=12,
        fill=TEXT_SECONDARY,
        anchor="end",
    )
    lines.append(
        f'<line x1="190" y1="485" x2="1010" y2="485" stroke="{ARROW_PRIMARY}" '
        'stroke-width="2"/>'
    )
    lines.append(
        f'<polygon points="1010,485 998,479 998,491" fill="{ARROW_PRIMARY}"/>'
    )
    add_text(
        lines,
        x=600,
        y=478,
        text="time",
        size=12,
        fill=TEXT_SECONDARY,
        anchor="middle",
    )
    windows = (
        (175, "t", range(1, 9), "u5-u8 repeated"),
        (470, "t+1", range(5, 13), "u5-u8 | u9-u12"),
        (765, "t+2", range(9, 17), "u9-u12 repeated"),
    )
    for x, window_name, utterance_ids, context_label in windows:
        lines.append(
            f'<rect x="{x}" y="395" width="260" height="70" rx="8" '
            f'fill="#ffffff" stroke="{BORDER_NAVY}" stroke-width="1.5"/>'
        )
        add_text(
            lines,
            x=x + 14,
            y=418,
            text=f"Window {window_name}",
            size=13,
            weight=700,
        )
        for cell, utterance_id in enumerate(utterance_ids):
            if 5 <= utterance_id <= 8:
                fill = "#dbeafe"
            elif 9 <= utterance_id <= 12:
                fill = "#bfdbfe"
            else:
                fill = "#e5e7eb"
            cell_x = x + 14 + cell * 29
            lines.append(
                f'<rect x="{cell_x}" y="432" width="24" height="18" rx="3" '
                f'fill="{fill}" stroke="#94a3b8" stroke-width="1" '
                f'data-window="{window_name}" data-utterance="u{utterance_id}"/>'
            )
            add_text(
                lines,
                x=cell_x + 12,
                y=446,
                text=f"u{utterance_id}",
                size=12,
                fill=TEXT_PRIMARY,
                anchor="middle",
            )
        add_text(
            lines,
            x=x + 130,
            y=462,
            text=context_label,
            size=12,
            fill=TEXT_SECONDARY,
            anchor="middle",
        )
    add_rule_pill(
        lines,
        x=500,
        y=535,
        width=200,
        label="Pending candidates",
    )
    svg_close(lines)
    return write_svg(lines, path)


def figure_03(path: Path) -> Path:
    lines: list[str] = []
    svg_open(
        lines,
        height=720,
        title="MODULE 4 — TOPIC SEGMENTATION",
        subtitle="Multi-scale depth aggregation",
    )
    panels = (
        (50, "Input — Similarity Profile"),
        (330, "1  Depth by Radius"),
        (610, "2  Z-score Normalization"),
        (890, "3  Mean Aggregation"),
    )
    for x, title in panels:
        add_panel(lines, x=x, y=145, width=240, height=385, title=title)
    for x in (290, 570, 850):
        add_arrow(lines, x1=x, y1=340, x2=x + 40, y2=340)

    lines.append(
        f'<path d="M 78 270 C 105 245, 125 255, 143 280 S 165 382, 185 393 '
        f'S 220 278, 260 265" fill="none" stroke="{ARROW_PRIMARY}" '
        'stroke-width="3"/>'
    )
    lines.append(f'<circle cx="185" cy="393" r="5" fill="{BORDER_NAVY}"/>')
    add_text(lines, x=104, y=246, text="p_L", size=12, weight=700)
    add_text(lines, x=232, y=255, text="p_R", size=12, weight=700)
    add_text(lines, x=193, y=416, text="S_i", size=12, weight=700)
    add_text(
        lines,
        x=170,
        y=468,
        text="one cohesion valley",
        size=12,
        fill=TEXT_SECONDARY,
        anchor="middle",
    )

    add_rule_pill(
        lines,
        x=350,
        y=210,
        width=200,
        label="R = {3, 5, 10, 15, 20}",
    )
    for row, radius in enumerate((3, 5, 10, 15, 20)):
        y = 270 + row * 43
        add_text(lines, x=354, y=y + 15, text=f"r = {radius}", size=12, weight=700)
        lines.append(
            f'<path d="M 405 {y + 12} L 438 {y + 8} L 466 {y + 24} '
            f'L 493 {y + 9} L 535 {y + 15}" fill="none" stroke="{ARROW_PRIMARY}" '
            'stroke-width="2"/>'
        )

    add_text(
        lines,
        x=730,
        y=260,
        text="center",
        size=13,
        weight=700,
        anchor="middle",
    )
    add_text(
        lines,
        x=730,
        y=315,
        text="then scale",
        size=13,
        weight=700,
        anchor="middle",
    )
    lines.append(
        f'<line x1="660" y1="350" x2="800" y2="350" stroke="{BORDER_NAVY}" '
        'stroke-width="1.5" stroke-dasharray="5,4"/>'
    )
    add_text(
        lines,
        x=730,
        y=385,
        text="per radius",
        size=12,
        fill=TEXT_SECONDARY,
        anchor="middle",
    )

    for row in range(5):
        y = 235 + row * 45
        lines.append(
            f'<line x1="930" y1="{y}" x2="1090" y2="{y}" stroke="#cbd5e1" '
            'stroke-width="1"/>'
        )
        lines.append(
            f'<circle cx="{966 + row * 22}" cy="{y}" r="5" fill="{ARROW_PRIMARY}"/>'
        )
    lines.append(
        f'<line x1="1010" y1="445" x2="1010" y2="490" '
        f'stroke="{ARROW_PRIMARY}" stroke-width="2"/>'
    )
    lines.append(
        f'<polygon points="1010,490 1004,478 1016,478" fill="{ARROW_PRIMARY}"/>'
    )
    add_text(
        lines,
        x=1010,
        y=510,
        text="one aggregate profile",
        size=12,
        fill=TEXT_SECONDARY,
        anchor="middle",
    )

    add_rule_pill(
        lines,
        x=100,
        y=560,
        width=1000,
        label="D_r(i) = (p_L(i,r) + p_R(i,r) - 2S_i) / 2",
    )
    add_rule_pill(
        lines,
        x=100,
        y=610,
        width=1000,
        label="D_hat_r(i) = (D_r(i) - mu_r) / (sigma_r + epsilon)",
    )
    add_rule_pill(
        lines,
        x=100,
        y=660,
        width=1000,
        label="D_bar(i) = (1 / |R|) sum_{r in R} D_hat_r(i)",
    )
    svg_close(lines)
    return write_svg(lines, path)


def figure_04(path: Path) -> Path:
    lines: list[str] = []
    svg_open(
        lines,
        height=620,
        title="MODULE 4 — TOPIC SEGMENTATION",
        subtitle="Adaptive candidate selection",
    )
    add_panel(
        lines,
        x=55,
        y=150,
        width=520,
        height=370,
        title="Input — Aggregated Depth",
    )
    add_box(
        lines,
        x=625,
        y=175,
        width=230,
        height=105,
        title="Mean and Standard\nDeviation",
        subtitle="local statistics",
        step=1,
    )
    add_box(
        lines,
        x=625,
        y=335,
        width=230,
        height=95,
        title="tau = mu + alpha sigma",
        subtitle="local threshold",
        step=2,
    )
    add_box(
        lines,
        x=930,
        y=175,
        width=220,
        height=115,
        title="Candidate\nSelection",
        subtitle="depth > threshold",
        step=3,
    )
    add_box(
        lines,
        x=930,
        y=395,
        width=220,
        height=100,
        title="Candidate Set",
        subtitle="accepted boundary indices",
        state="output",
    )
    add_arrow(lines, x1=575, y1=228, x2=625, y2=228)
    add_arrow(lines, x1=740, y1=280, x2=740, y2=335)
    add_arrow(lines, x1=855, y1=382, x2=900, y2=382)
    lines.append(
        f'<path d="M 900 382 L 900 232 L 930 232" fill="none" '
        f'stroke="{ARROW_PRIMARY}" stroke-width="2.5" '
        'marker-end="url(#arrow-primary)"/>'
    )
    add_arrow(lines, x1=1040, y1=290, x2=1040, y2=395, state="output")

    lines.append(
        f'<line x1="92" y1="430" x2="540" y2="430" stroke="{BORDER_NAVY}" '
        'stroke-width="1.5"/>'
    )
    lines.append(
        f'<line x1="92" y1="325" x2="540" y2="325" stroke="{BORDER_NAVY}" '
        'stroke-width="1.5" stroke-dasharray="7,5"/>'
    )
    add_text(lines, x=98, y=313, text="threshold", size=12, fill=TEXT_SECONDARY)
    lines.append(
        f'<path d="M 92 405 L 135 390 L 175 360 L 220 250 L 265 374 L 310 342 '
        f'L 355 285 L 400 365 L 445 345 L 490 352 L 540 395" fill="none" '
        f'stroke="{ARROW_PRIMARY}" stroke-width="3"/>'
    )
    lines.append(
        f'<circle cx="220" cy="250" r="7" fill="{BORDER_NAVY}" '
        'data-profile-state="accepted" data-index="4"/>'
    )
    lines.append(
        f'<circle cx="355" cy="285" r="7" fill="{BORDER_NAVY}" '
        'data-profile-state="accepted" data-index="7"/>'
    )
    lines.append(
        '<circle cx="310" cy="342" r="7" fill="#ffffff" stroke="#6b7280" '
        'stroke-width="2" data-profile-state="rejected" data-index="6"/>'
    )
    add_text(lines, x=220, y=232, text="Accepted", size=12, weight=700, anchor="middle")
    add_text(
        lines,
        x=310,
        y=368,
        text="Rejected",
        size=12,
        fill=TEXT_SECONDARY,
        anchor="middle",
    )
    for index, cx in zip((4, 7), (1010, 1070), strict=True):
        lines.append(
            f'<circle cx="{cx}" cy="468" r="15" fill="#f0fdf4" '
            f'stroke="{OUTPUT_GREEN}" stroke-width="1.5" '
            f'data-candidate-index="{index}"/>'
        )
        add_text(
            lines,
            x=cx,
            y=473,
            text=str(index),
            size=12,
            weight=700,
            anchor="middle",
        )
    svg_close(lines)
    return write_svg(lines, path)


def figure_05(path: Path) -> Path:
    lines: list[str] = []
    svg_open(
        lines,
        height=670,
        title="MODULE 4 — TOPIC SEGMENTATION",
        subtitle="Streaming boundary confirmation",
    )
    frames = (
        (55, "Window t", "Candidate", 190, 105, "process"),
        (410, "Window t+1", "Pending", 155, 62, "process"),
        (765, "Window t+2", "Committed", 120, 24, "committed"),
    )
    add_arrow(lines, x1=355, y1=330, x2=410, y2=330)
    add_arrow(lines, x1=710, y1=330, x2=765, y2=330)
    for frame_x, title, state_label, local_g, remaining, state in frames:
        add_panel(
            lines,
            x=frame_x,
            y=155,
            width=300,
            height=360,
            title=title,
            state=state,
        )
        stroke = OUTPUT_GREEN if state == "committed" else BORDER_NAVY
        fill = "#f0fdf4" if state == "committed" else "#ffffff"
        add_rule_pill(
            lines,
            x=frame_x + 75,
            y=220,
            width=150,
            label=state_label,
            state=state,
        )
        axis_y = 350
        lines.append(
            f'<line x1="{frame_x + 30}" y1="{axis_y}" x2="{frame_x + 270}" '
            f'y2="{axis_y}" stroke="{stroke}" stroke-width="2"/>'
        )
        marker_x = frame_x + local_g
        lines.append(
            f'<line x1="{marker_x}" y1="305" x2="{marker_x}" y2="382" '
            f'stroke="{stroke}" stroke-width="3" data-global-position="g" '
            f'data-frame-x="{frame_x}"/>'
        )
        lines.append(
            f'<circle cx="{marker_x}" cy="{axis_y}" r="7" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="3"/>'
        )
        add_text(
            lines,
            x=marker_x,
            y=402,
            text="Global position g",
            size=12,
            fill=stroke,
            weight=700,
            anchor="middle",
        )
        add_text(
            lines,
            x=frame_x + 30,
            y=334,
            text="window start",
            size=12,
            fill=TEXT_SECONDARY,
        )
        bar_x = frame_x + 145
        lines.append(
            f'<rect x="{bar_x}" y="445" width="{remaining}" height="16" rx="8" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5" '
            'data-lookahead="remaining"/>'
        )
        add_text(
            lines,
            x=frame_x + 150,
            y=486,
            text="remaining lookahead",
            size=12,
            fill=TEXT_SECONDARY if state != "committed" else OUTPUT_GREEN,
            anchor="middle",
        )
    add_rule_pill(
        lines,
        x=305,
        y=560,
        width=270,
        label="g <= s_t + W - L",
    )
    add_rule_pill(
        lines,
        x=605,
        y=560,
        width=330,
        label="Committed boundaries are immutable",
        state="committed",
    )
    svg_close(lines)
    return write_svg(lines, path)


def figure_06(path: Path) -> Path:
    lines: list[str] = []
    svg_open(
        lines,
        height=560,
        title="MODULE 5 — HIERARCHICAL SUMMARIZATION",
        subtitle="Hierarchical summarization module overview",
    )
    stages = (
        (45, "Committed Topic\nSegment", None),
        (240, "Non-overlapping\nChunks", 1),
        (435, "ViT5 Chunk\nSummaries", 2),
        (630, "BARTpho Topic\nTitle", 3),
    )
    for x, title, step in stages:
        add_box(
            lines,
            x=x,
            y=235,
            width=155,
            height=112,
            title=title,
            step=step,
        )
    for index in range(len(stages) - 1):
        add_arrow(
            lines,
            x1=stages[index][0] + 155,
            y1=291,
            x2=stages[index + 1][0],
            y2=291,
        )

    add_arrow(lines, x1=785, y1=291, x2=825, y2=291, state="output")
    add_panel(
        lines,
        x=825,
        y=155,
        width=330,
        height=315,
        title="Hierarchical Recap",
        state="output",
    )
    lines.append(
        '<rect x="855" y="225" width="270" height="50" rx="8" '
        f'fill="#ffffff" stroke="{OUTPUT_GREEN}" stroke-width="1.5"/>'
    )
    add_text(
        lines,
        x=990,
        y=255,
        text="Topic Title",
        size=14,
        fill=OUTPUT_GREEN,
        weight=700,
        anchor="middle",
    )
    for index, y in enumerate((300, 345, 390), start=1):
        lines.append(
            f'<rect x="855" y="{y}" width="270" height="34" rx="6" '
            f'fill="#ffffff" stroke="{OUTPUT_GREEN}" stroke-width="1.25"/>'
        )
        add_text(
            lines,
            x=875,
            y=y + 22,
            text=f"{index}  Chunk summary",
            size=12,
            fill=TEXT_PRIMARY,
            weight=600,
        )
    svg_close(lines)
    return write_svg(lines, path)


def figure_07(path: Path) -> Path:
    lines: list[str] = []
    svg_open(
        lines,
        height=590,
        title="MODULE 5 — HIERARCHICAL SUMMARIZATION",
        subtitle="Utterance chunking",
    )
    add_panel(
        lines,
        x=50,
        y=145,
        width=1100,
        height=285,
        title="Committed Topic Segment — 21 utterances",
    )
    chunks = (
        (120, 330, 1, range(1, 9), "8 utterances"),
        (450, 330, 2, range(9, 17), "8 utterances"),
        (800, 280, 3, range(17, 22), "5 utterances"),
    )
    fills = ("#eff6ff", "#e8f1fb", "#f1f5f9")
    for (x, width, chunk, utterances, count_label), fill in zip(
        chunks, fills, strict=True
    ):
        lines.append(
            f'<rect x="{x}" y="220" width="{width}" height="125" rx="8" '
            f'fill="#ffffff" stroke="{BORDER_NAVY}" stroke-width="1.5"/>'
        )
        add_text(
            lines,
            x=x + width // 2,
            y=247,
            text=f"Chunk {chunk} — {count_label}",
            size=13,
            weight=700,
            anchor="middle",
        )
        utterance_ids = list(utterances)
        cell_width = 32
        gap = 5
        strip_width = len(utterance_ids) * cell_width + (len(utterance_ids) - 1) * gap
        cell_x = x + (width - strip_width) // 2
        for offset, utterance_id in enumerate(utterance_ids):
            current_x = cell_x + offset * (cell_width + gap)
            lines.append(
                f'<rect x="{current_x}" y="275" width="{cell_width}" height="36" '
                f'rx="4" fill="{fill}" stroke="#94a3b8" stroke-width="1" '
                f'data-chunk="{chunk}" data-utterance="u{utterance_id}"/>'
            )
            add_text(
                lines,
                x=current_x + cell_width // 2,
                y=298,
                text=f"u{utterance_id}",
                size=12,
                anchor="middle",
            )
    lines.append(
        f'<line x1="120" y1="380" x2="1080" y2="380" stroke="{ARROW_PRIMARY}" '
        'stroke-width="2"/>'
    )
    lines.append(
        f'<polygon points="1080,380 1068,374 1068,386" fill="{ARROW_PRIMARY}"/>'
    )
    add_text(
        lines,
        x=600,
        y=405,
        text="chronological order",
        size=12,
        fill=TEXT_SECONDARY,
        anchor="middle",
    )
    add_rule_pill(lines, x=170, y=485, width=230, label="Chronological")
    add_rule_pill(lines, x=485, y=485, width=230, label="No overlap")
    add_rule_pill(
        lines,
        x=800,
        y=485,
        width=230,
        label="Never cross a topic boundary",
    )
    svg_close(lines)
    return write_svg(lines, path)


def figure_08(path: Path) -> Path:
    lines: list[str] = []
    svg_open(
        lines,
        height=590,
        title="MODULE 5 — HIERARCHICAL SUMMARIZATION",
        subtitle="ViT5 chunk summarization",
    )
    stages = (
        (30, 145, "Speaker-labelled\nUtterances", "process", None),
        (205, 165, "Task\nFormatting", "process", 1),
        (400, 165, "Tokenization", "process", 2),
        (595, 165, "Fine-tuned\nViT5-base", "process", 3),
        (790, 165, "Store and\nEmit", "process", 4),
        (985, 185, "Emitted Chunk\nSummary", "output", None),
    )
    for x, width, title, state, step in stages:
        add_box(
            lines,
            x=x,
            y=175,
            width=width,
            height=120,
            title=title,
            state=state,
            step=step,
        )
    for index in range(len(stages) - 1):
        add_arrow(
            lines,
            x1=stages[index][0] + stages[index][1],
            y1=235,
            x2=stages[index + 1][0],
            y2=235,
            state="output" if index == len(stages) - 2 else "flow",
        )

    add_panel(lines, x=50, y=390, width=1100, height=130, title="Decoding constraints")
    lines.append('<g data-constraint-footer="vit5">')
    constraints = (
        (105, 190, "max input: 512 tokens"),
        (305, 150, "beam size: 4"),
        (465, 150, "no sampling"),
        (625, 190, "no-repeat 3-gram"),
        (825, 230, "max output: 128 tokens"),
    )
    for x, width, label in constraints:
        add_rule_pill(lines, x=x, y=460, width=width, label=label)
    lines.append("</g>")
    svg_close(lines)
    return write_svg(lines, path)


def figure_09(path: Path) -> Path:
    lines: list[str] = []
    svg_open(
        lines,
        height=620,
        title="MODULE 5 — HIERARCHICAL SUMMARIZATION",
        subtitle="BARTpho topic titling",
    )
    stages = (
        (20, 130, "ordered-summaries", "Ordered Chunk\nSummaries", "process", None, 0),
        (165, 135, "all-summaries-ready", "All summaries\nready", "process", None, 0),
        (315, 110, "join", 'Join with\n" / "', "process", 1, 1),
        (440, 150, "truncate", "Keep Last 1,500\nCharacters", "process", 2, 2),
        (605, 110, "prefix", "Add Task\nPrefix", "process", 3, 3),
        (730, 115, "tokenization", "Tokenization", "process", 4, 4),
        (
            860,
            190,
            "bartpho-inference",
            "Fine-tuned\nBARTpho-syllable-base",
            "process",
            5,
            5,
        ),
        (1065, 115, "topic-title", "Topic\nTitle", "output", None, 6),
    )
    for x, width, stage, title, state, step, order in stages:
        lines.append(f'<g data-stage="{stage}" data-order="{order}">')
        add_box(
            lines,
            x=x,
            y=180,
            width=width,
            height=125,
            title=title,
            state=state,
            step=step,
        )
        if stage == "all-summaries-ready":
            lines.append(
                f'<rect x="{x + 6}" y="186" width="{width - 12}" height="113" '
                f'rx="7" fill="none" stroke="{BORDER_NAVY}" stroke-width="1"/>'
            )
        lines.append("</g>")
    for index in range(len(stages) - 1):
        x, width, _, _, _, _, _ = stages[index]
        next_x = stages[index + 1][0]
        add_arrow(
            lines,
            x1=x + width,
            y1=242,
            x2=next_x,
            y2=242,
            state="output" if index == len(stages) - 2 else "flow",
        )

    add_panel(lines, x=50, y=405, width=1100, height=130, title="Decoding constraints")
    lines.append('<g data-constraint-footer="bartpho">')
    constraints = (
        (95, 210, "max input: 1,024 tokens"),
        (315, 150, "beam size: 4"),
        (475, 150, "no sampling"),
        (635, 190, "no-repeat 3-gram"),
        (835, 240, "max output: 200 tokens"),
    )
    for x, width, label in constraints:
        add_rule_pill(lines, x=x, y=475, width=width, label=label)
    lines.append("</g>")
    svg_close(lines)
    return write_svg(lines, path)


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
