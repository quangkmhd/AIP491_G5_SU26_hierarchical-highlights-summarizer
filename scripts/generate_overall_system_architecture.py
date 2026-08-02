#!/usr/bin/env python3
"""Generate the publication-ready overall software architecture diagram."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "report_compilation" / "assets" / "fig02_overall_software_architecture.svg"


def add_text(lines: list[str], x: int, y: int, text: str, *, size: int = 16,
             weight: int = 400, anchor: str = "middle", color: str = "#111827") -> None:
    lines.append(
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}">{text}</text>'
    )


def add_card(lines: list[str], node_id: str, x: int, y: int, width: int, height: int,
             eyebrow: str, title: str, details: list[str]) -> None:
    lines.append(f'<g id="{node_id}" data-graph-role="node">')
    lines.append(
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" '
        'fill="#ffffff" stroke="#9ca3af" stroke-width="1.6"/>'
    )
    add_text(lines, x + 18, y + 25, eyebrow.upper(), size=11, weight=600,
             anchor="start", color="#6b7280")
    add_text(lines, x + width // 2, y + 58, title, size=17, weight=600)
    for index, detail in enumerate(details):
        add_text(lines, x + width // 2, y + 87 + index * 22, detail,
                 size=13, color="#4b5563")
    lines.append('</g>')


def add_edge(lines: list[str], edge_id: str, path: str, label_x: int, label_y: int,
             label: str, *, dashed: bool = False) -> None:
    dash = ' stroke-dasharray="7,5"' if dashed else ''
    color = "#6b7280" if dashed else "#2563eb"
    marker = "arrow-gray" if dashed else "arrow-blue"
    lines.append(
        f'<path id="{edge_id}" data-graph-role="edge" d="{path}" fill="none" '
        f'stroke="{color}" stroke-width="2"{dash} marker-end="url(#{marker})"/>'
    )
    add_text(lines, label_x, label_y, label, size=12, weight=600, color=color)


def main() -> None:
    lines: list[str] = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 900" width="1500" height="900">')
    lines.append('<style>text { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }</style>')
    lines.append('<defs>')
    lines.append('<marker id="arrow-blue" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#2563eb"/></marker>')
    lines.append('<marker id="arrow-gray" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#6b7280"/></marker>')
    lines.append('</defs>')
    lines.append('<rect width="1500" height="900" fill="#ffffff"/>')

    add_text(lines, 750, 48, "Overall Software Architecture", size=27, weight=600)
    add_text(lines, 750, 76, "Streaming meeting recap with local AI inference", size=14, color="#6b7280")

    # Layer containers are placed before edges and nodes.
    lines.append('<g data-graph-role="container">')
    lines.append('<rect x="45" y="105" width="1410" height="205" rx="12" fill="#f9fafb" stroke="#d1d5db" stroke-width="1.2" stroke-dasharray="7,5"/>')
    add_text(lines, 65, 130, "INTERACTION AND API LAYER", size=11, weight=600, anchor="start", color="#6b7280")
    lines.append('<rect x="45" y="335" width="1410" height="310" rx="12" fill="#f9fafb" stroke="#d1d5db" stroke-width="1.2" stroke-dasharray="7,5"/>')
    add_text(lines, 65, 360, "APPLICATION AND AI SERVICE LAYER", size=11, weight=600, anchor="start", color="#6b7280")
    lines.append('<rect x="45" y="680" width="1410" height="145" rx="12" fill="#f9fafb" stroke="#d1d5db" stroke-width="1.2" stroke-dasharray="7,5"/>')
    add_text(lines, 65, 705, "LOCAL MODEL RUNTIME", size=11, weight=600, anchor="start", color="#6b7280")
    lines.append('</g>')

    # Primary flow is routed before cards so card fills protect their labels.
    add_edge(lines, "client-api", "M 335 210 H 480", 408, 197, "PCM audio")
    add_edge(lines, "api-orchestrator", "M 610 270 V 320 H 550 V 410 H 590", 610, 312, "WebSocket / REST")
    add_edge(lines, "orchestrator-preprocessing", "M 750 455 V 480 H 190 V 500", 470, 470, "stream control")
    add_edge(lines, "preprocessing-diarization", "M 305 560 H 340", 323, 547, "audio")
    add_edge(lines, "diarization-asr", "M 575 560 H 610", 593, 547, "IDs")
    add_edge(lines, "asr-topic", "M 845 560 H 880", 863, 547, "text")
    add_edge(lines, "topic-summary", "M 1115 560 H 1150", 1133, 547, "topics")
    add_edge(lines, "summary-output", "M 1265 500 V 325 H 1255 V 270", 1310, 326, "JSON events")

    # Runtime/model dependencies use a separate dashed semantic.
    add_edge(lines, "onnx-audio", "M 365 715 V 660 H 728 V 620", 530, 673, "local inference", dashed=True)
    add_edge(lines, "lexical-topic", "M 805 715 V 660 H 998 V 620", 900, 673, "lexical scores", dashed=True)
    add_edge(lines, "seq2seq-summary", "M 1190 715 V 660 H 1268 V 620", 1230, 673, "local inference", dashed=True)

    add_card(lines, "web-client", 75, 155, 260, 115, "Client", "Web Client", ["Microphone and meeting controls"])
    add_card(lines, "fastapi-runtime", 480, 145, 260, 125, "API", "FastAPI Runtime", ["/ws · REST · SSE", "Session and request handling"])
    add_card(lines, "live-output", 1125, 145, 260, 125, "Output", "Live Recap UI", ["Partial transcripts and recap events", "Structured hierarchical report"])

    add_card(lines, "streaming-orchestrator", 600, 365, 300, 90, "Application control", "Streaming Orchestrator", ["Session state and event lifecycle"])
    add_card(lines, "audio-preprocessing", 70, 500, 235, 120, "Module 1", "Audio Preprocessing", ["Silero VAD · PCM buffering"])
    add_card(lines, "speaker-diarization", 340, 500, 235, 120, "Module 2", "Speaker Diarization", ["WeSpeaker embeddings"])
    add_card(lines, "asr", 610, 500, 235, 120, "Module 3", "Speech Recognition", ["Streaming Zipformer ASR"])
    add_card(lines, "topic-segmentation", 880, 500, 235, 120, "Module 4", "Topic Segmentation", ["Multi-Scale Sliding TextTiling"])
    add_card(lines, "hierarchical-summary", 1150, 500, 235, 120, "Module 5", "Hierarchical Summarization", ["ViT5 summaries · BARTpho titles"])

    add_card(lines, "onnx-runtime", 150, 715, 430, 95, "Inference", "ONNX / sherpa-onnx", ["VAD · speaker · ASR checkpoints"])
    add_card(lines, "lexical-runtime", 650, 715, 310, 95, "Algorithm", "Lexical Processing", ["BoW · cosine · multi-scale depth"])
    add_card(lines, "seq2seq-runtime", 1030, 715, 320, 95, "Inference", "PyTorch / Transformers / CUDA", ["Local ViT5 and BARTpho checkpoints"])

    # Legend stays outside all business-flow corridors.
    lines.append('<g data-graph-role="legend">')
    lines.append('<line x1="530" y1="855" x2="570" y2="855" stroke="#2563eb" stroke-width="2" marker-end="url(#arrow-blue)"/>')
    add_text(lines, 585, 859, "Primary data and event flow", size=12, anchor="start", color="#4b5563")
    lines.append('<line x1="830" y1="855" x2="870" y2="855" stroke="#6b7280" stroke-width="2" stroke-dasharray="7,5" marker-end="url(#arrow-gray)"/>')
    add_text(lines, 885, 859, "Local runtime dependency", size=12, anchor="start", color="#4b5563")
    lines.append('</g>')
    lines.append('</svg>')

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
