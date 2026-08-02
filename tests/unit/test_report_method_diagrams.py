"""Contract tests for the report-method SVG generator."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.generate_report_method_diagrams import generate_all


EXPECTED_STEMS = [
    "fig01_five_module_pipeline",
    "fig02_topic_segmentation_module",
    "fig03_multiscale_depth_score_detail",
    "fig04_adaptive_threshold_candidates",
    "fig05_streaming_boundary_confirmation",
    "fig06_hierarchical_summarization_module",
    "fig07_utterance_chunking_detail",
    "fig08_chunk_summarization_detail",
    "fig09_topic_titling_detail",
]


def test_generate_all_writes_nine_white_svg_figures_in_order(tmp_path: Path) -> None:
    """Catch missing, reordered, or non-publication-canvas figure output."""
    outputs = generate_all(tmp_path)

    assert [path.stem for path in outputs] == EXPECTED_STEMS
    assert [path.suffix for path in outputs] == [".svg"] * 9
    assert len(outputs) == 9
    assert all(path.exists() for path in outputs)
    assert all('<rect width="1200" height="' in path.read_text() for path in outputs)
    assert all('fill="#ffffff"' in path.read_text() for path in outputs)


def test_generate_all_uses_the_required_english_title_families(tmp_path: Path) -> None:
    """Catch figures that lose their report-level module context."""
    outputs = generate_all(tmp_path)
    documents = [path.read_text() for path in outputs]

    assert "SYSTEM OVERVIEW — FIVE-MODULE PIPELINE" in documents[0]
    assert all("MODULE 4 — TOPIC SEGMENTATION" in document for document in documents[1:5])
    assert all(
        "MODULE 5 — HIERARCHICAL SUMMARIZATION" in document
        for document in documents[5:]
    )


def test_generate_all_keeps_visible_svg_text_english_only(tmp_path: Path) -> None:
    """Catch Vietnamese characters accidentally introduced into diagram labels."""
    visible_text = "\n".join(
        text
        for path in generate_all(tmp_path)
        for text in re.findall(r"<text\b[^>]*>(.*?)</text>", path.read_text())
    )

    assert not re.search(r"[À-ỹĐđ]", visible_text)
