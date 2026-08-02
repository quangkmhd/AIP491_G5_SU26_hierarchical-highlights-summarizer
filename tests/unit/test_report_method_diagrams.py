"""Contract tests for the report-method SVG generator."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
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


def _visible_text(path: Path) -> str:
    """Return rendered SVG text with XML entities decoded."""
    root = ET.fromstring(path.read_text())
    return "\n".join(
        "".join(element.itertext())
        for element in root.iter("{http://www.w3.org/2000/svg}text")
    )


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


def test_figure_01_shows_the_five_module_pipeline_without_internal_metrics(
    tmp_path: Path,
) -> None:
    """Catch a missing system stage or leakage of lower-level evaluation detail."""
    figure = _visible_text(generate_all(tmp_path)[0])

    assert all(
        label in figure
        for label in (
            "Audio Stream",
            "Audio Preprocessing",
            "Speaker Diarization",
            "Automatic Speech Recognition",
            "Topic Segmentation",
            "Hierarchical Summarization",
            "cleaned speech",
            "speaker-labelled audio",
            "speaker-labelled utterances",
            "committed topics",
            "Hierarchical Meeting Recap",
            "hierarchical recap",
        )
    )
    assert "WER" not in figure


def test_figure_02_shows_the_module_flow_and_streaming_windows_without_formulas(
    tmp_path: Path,
) -> None:
    """Catch omitted segmentation stages, window progression, or duplicated formulas."""
    figure = _visible_text(generate_all(tmp_path)[1])

    assert all(
        label in figure
        for label in (
            "Speaker-labelled Utterances",
            "Lexical Cohesion",
            "Multi-scale Depth",
            "Adaptive Threshold",
            "Merge Short Segments",
            "Streaming Confirmation",
            "Committed Topic Segments",
            "Window t",
            "Window t+1",
            "Window t+2",
            "Pending candidates",
        )
    )
    assert "tau =" not in figure
    assert "p_L" not in figure


def test_figure_03_connects_multiscale_depth_to_mean_aggregation(
    tmp_path: Path,
) -> None:
    """Catch a missing radius, valley landmark, normalization, or aggregation equation."""
    figure = _visible_text(generate_all(tmp_path)[2])

    assert all(
        label in figure
        for label in (
            "Similarity Profile",
            "Depth by Radius",
            "Z-score Normalization",
            "Mean Aggregation",
            "R = {3, 5, 10, 15, 20}",
            "S_i",
            "p_L",
            "p_R",
            "d_i^(r) = max(0, p_L - S_i) + max(0, p_R - S_i)",
            "D_i = (1 / |R|) sum z_i^(r)",
        )
    )
    assert figure.count("Similarity Profile") == 1


def test_figure_04_distinguishes_accepted_and_rejected_candidates(
    tmp_path: Path,
) -> None:
    """Catch a missing threshold decision or irrelevant sensitivity analysis."""
    figure = _visible_text(generate_all(tmp_path)[3])

    assert all(
        label in figure
        for label in (
            "Aggregated Depth",
            "Mean and Standard Deviation",
            "tau = mu + alpha sigma",
            "Candidate Set",
            "Accepted",
            "Rejected",
        )
    )
    assert "alpha sensitivity" not in figure.lower()


def test_figure_05_commits_a_fixed_global_candidate_after_lookahead(
    tmp_path: Path,
) -> None:
    """Catch moving candidate positions, missing state progression, or a missing invariant."""
    path = generate_all(tmp_path)[4]
    figure = _visible_text(path)

    assert all(
        label in figure
        for label in (
            "Window t",
            "Window t+1",
            "Window t+2",
            "Global position g",
            "Candidate",
            "Pending",
            "Committed",
            "g <= s_t + W - L",
            "Committed boundaries are immutable",
        )
    )
    assert "Lexical Cohesion" not in figure
    root = ET.fromstring(path.read_text())
    chronological_arrows = [
        element
        for element in root.iter("{http://www.w3.org/2000/svg}line")
        if element.get("marker-end")
    ]
    assert {arrow.get("stroke") for arrow in chronological_arrows} == {"#3b6ea8"}
