#!/usr/bin/env python3
"""Generate editable, publication-ready SVG diagrams for the thesis report."""

from __future__ import annotations

from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report_compilation" / "assets"

NAVY = "#17324D"
BLUE = "#0077BB"
TEAL = "#009988"
ORANGE = "#EE7733"
RED = "#CC3311"
GRAY = "#65717E"
LIGHT = "#F5F7F9"
BLUE_BG = "#EAF4FB"
TEAL_BG = "#E8F7F4"
ORANGE_BG = "#FFF2E8"
VIOLET_BG = "#F2EEFA"


def start(width: int, height: int, title: str, desc: str) -> list[str]:
    lines: list[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
    )
    lines.append(f'<title id="title">{escape(title)}</title>')
    lines.append(f'<desc id="desc">{escape(desc)}</desc>')
    lines.append("<defs>")
    for name, color in (("blue", BLUE), ("navy", NAVY), ("orange", ORANGE), ("gray", GRAY)):
        lines.append(
            f'<marker id="arrow-{name}" markerWidth="10" markerHeight="10" refX="8" refY="3" '
            f'orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="{color}"/></marker>'
        )
    lines.append("</defs>")
    lines.append(f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>')
    return lines


def text(lines: list[str], x: float, y: float, value: str, *, size: int = 18,
         weight: int = 400, fill: str = NAVY, anchor: str = "middle") -> None:
    lines.append(
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Liberation Sans, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">{escape(value)}</text>'
    )


def multiline(lines: list[str], x: float, y: float, rows: list[str], *, size: int = 18,
              weight: int = 400, fill: str = NAVY, anchor: str = "middle", gap: int = 24) -> None:
    lines.append(
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Liberation Sans, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}">'
    )
    for idx, row in enumerate(rows):
        dy = 0 if idx == 0 else gap
        lines.append(f'<tspan x="{x}" dy="{dy}">{escape(row)}</tspan>')
    lines.append("</text>")


def box(lines: list[str], x: float, y: float, w: float, h: float, rows: list[str], *,
        fill: str = LIGHT, stroke: str = NAVY, size: int = 17, weight: int = 600,
        radius: int = 10) -> None:
    lines.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.7"/>'
    )
    total = (len(rows) - 1) * 23
    multiline(lines, x + w / 2, y + h / 2 - total / 2 + 6, rows, size=size, weight=weight, gap=23)


def group(lines: list[str], x: float, y: float, w: float, h: float, number: str, title_value: str,
          *, fill: str = "#FAFBFC", stroke: str = "#C6CED6") -> None:
    lines.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"/>'
    )
    lines.append(f'<circle cx="{x + 25}" cy="{y + 25}" r="15" fill="{NAVY}"/>')
    text(lines, x + 25, y + 31, number, size=16, weight=700, fill="#FFFFFF")
    text(lines, x + 49, y + 31, title_value, size=17, weight=700, anchor="start")


def arrow(lines: list[str], x1: float, y1: float, x2: float, y2: float, *, color: str = BLUE,
          marker: str = "blue", dashed: bool = False, width: float = 2.2) -> None:
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    lines.append(
        f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="{width}"'
        f'{dash} marker-end="url(#arrow-{marker})"/>'
    )


def poly_arrow(lines: list[str], points: list[tuple[float, float]], *, color: str = BLUE,
               marker: str = "blue", dashed: bool = False, width: float = 2.2) -> None:
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    path = " ".join(("M" if idx == 0 else "L") + f"{x},{y}" for idx, (x, y) in enumerate(points))
    lines.append(
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}"'
        f'{dash} marker-end="url(#arrow-{marker})"/>'
    )


def chip(lines: list[str], x: float, y: float, w: float, value: str) -> None:
    lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="29" rx="14.5" fill="{ORANGE_BG}" stroke="{ORANGE}"/>')
    text(lines, x + w / 2, y + 20, value, size=13, weight=700, fill=RED)


def save(name: str, lines: list[str]) -> None:
    lines.append("</svg>")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def overall_pipeline() -> None:
    lines = start(1600, 870, "Quy trình tổng thể", "Năm giai đoạn của hệ thống tóm tắt cuộc họp phân cấp dạng luồng.")
    text(lines, 70, 48, "LUỒNG ÂM THANH", size=14, weight=700, fill=GRAY, anchor="start")
    box(lines, 70, 72, 205, 74, ["Âm thanh đầu vào", "Audio stream"], fill=LIGHT)
    arrow(lines, 275, 109, 335, 109)
    box(lines, 335, 72, 205, 74, ["Silero VAD", "Phân đoạn thoại"], fill=BLUE_BG, stroke=BLUE)

    group(lines, 600, 40, 920, 215, "1", "Nhận dạng tiếng nói & phân định người nói", fill="#F7FBFE")
    arrow(lines, 540, 109, 650, 109)
    box(lines, 650, 82, 220, 74, ["Zipformer ASR", "Nội dung văn bản"], fill=BLUE_BG, stroke=BLUE)
    poly_arrow(lines, [(540, 109), (575, 109), (575, 196), (650, 196)], color=TEAL, marker="navy")
    box(lines, 650, 159, 220, 74, ["WeSpeaker", "Nhãn người nói"], fill=TEAL_BG, stroke=TEAL)
    arrow(lines, 870, 119, 990, 119)
    arrow(lines, 870, 196, 930, 196)
    poly_arrow(lines, [(930, 196), (930, 155), (990, 155)], color=BLUE)
    box(lines, 990, 92, 230, 94, ["Tổng hợp lượt lời", "uᵢ = (speaker, text)"], fill="#FFFFFF")
    arrow(lines, 1220, 139, 1280, 139)
    box(lines, 1280, 100, 200, 78, ["Lượt lời", "đã gắn nhãn"], fill=ORANGE_BG, stroke=ORANGE)
    chip(lines, 1288, 199, 184, "utterance-accepted")

    group(lines, 70, 310, 510, 220, "2", "Phân đoạn chủ đề", fill="#F7FBFE")
    box(lines, 115, 375, 185, 82, ["Bộ đệm trượt", "40 lượt lời"], fill=LIGHT)
    arrow(lines, 300, 416, 350, 416)
    box(lines, 350, 375, 190, 82, ["Multi-Scale", "Sliding TextTiling"], fill=BLUE_BG, stroke=BLUE)

    group(lines, 625, 310, 300, 220, "3", "Chia khối hội thoại", fill="#FBFAFE")
    box(lines, 670, 375, 210, 82, ["Chunking tuần tự", "tối đa 8 lượt lời"], fill=VIOLET_BG, stroke="#7655A6")

    group(lines, 970, 310, 300, 220, "4", "Tóm tắt khối", fill="#F6FCFA")
    box(lines, 1015, 375, 210, 82, ["ViT5-base", "Tóm tắt trừu tượng"], fill=TEAL_BG, stroke=TEAL)
    chip(lines, 1037, 476, 166, "chunk-closed")

    group(lines, 1315, 310, 235, 220, "5", "Đặt tiêu đề", fill="#FFFAF6")
    box(lines, 1340, 375, 185, 82, ["BARTpho-syllable-base", "Sinh tiêu đề"], fill=ORANGE_BG, stroke=ORANGE, size=14)
    chip(lines, 1342, 476, 181, "title-emitted")

    poly_arrow(lines, [(1380, 255), (1380, 275), (208, 275), (208, 375)], color=BLUE)
    arrow(lines, 540, 416, 670, 416)
    arrow(lines, 880, 416, 1015, 416)
    arrow(lines, 1225, 416, 1340, 416)
    chip(lines, 1022, 550, 195, "segment-closed")

    lines.append(f'<rect x="190" y="630" width="1220" height="148" rx="16" fill="{LIGHT}" stroke="#C6CED6" stroke-width="1.5"/>')
    text(lines, 240, 668, "ĐẦU RA PHÂN CẤP", size=14, weight=700, fill=GRAY, anchor="start")
    box(lines, 390, 683, 235, 62, ["Tiêu đề chủ đề hₖ"], fill=ORANGE_BG, stroke=ORANGE)
    text(lines, 670, 720, "+", size=30, weight=400, fill=GRAY)
    box(lines, 710, 683, 350, 62, ["Chuỗi tóm tắt khối qₖ,₁ … qₖ,ₘ"], fill=TEAL_BG, stroke=TEAL)
    chip(lines, 1120, 699, 210, "meeting-completed")
    poly_arrow(lines, [(1433, 530), (1433, 593), (800, 593), (800, 630)], color=ORANGE, marker="orange")
    text(lines, 70, 835, "Mũi tên liền: luồng dữ liệu", size=14, fill=GRAY, anchor="start")
    lines.append(f'<line x1="270" y1="830" x2="330" y2="830" stroke="{BLUE}" stroke-width="2.2" marker-end="url(#arrow-blue)"/>')
    text(lines, 390, 835, "Nhãn cam: sự kiện phát ra", size=14, fill=GRAY, anchor="start")
    save("fig01_overall_pipeline", lines)


def texttiling_workflow() -> None:
    lines = start(1600, 900, "Multi-Scale Sliding TextTiling", "Luồng xử lý theo lô và cửa sổ trượt của thuật toán phân đoạn chủ đề.")
    text(lines, 70, 52, "ĐẦU VÀO & CẤU HÌNH THỰC NGHIỆM", size=14, weight=700, fill=GRAY, anchor="start")
    lines.append(f'<rect x="70" y="72" width="1460" height="80" rx="12" fill="{LIGHT}" stroke="#C6CED6"/>')
    box(lines, 95, 91, 265, 43, ["U = (u₁, …, uₙ)"], fill="#FFFFFF", size=16)
    box(lines, 380, 91, 205, 43, ["k = 2"], fill="#FFFFFF", size=16)
    box(lines, 605, 91, 310, 43, ["R = [3, 5, 10, 15, 20]"], fill="#FFFFFF", size=16)
    box(lines, 935, 91, 235, 43, ["α = 1,2 · γ = 0,20"], fill="#FFFFFF", size=16)
    box(lines, 1190, 91, 310, 43, ["W = 40 · S = 5 · L = 20"], fill="#FFFFFF", size=16)

    group(lines, 70, 190, 1460, 170, "1", "Tiền xử lý & biểu diễn từ vựng", fill="#F7FBFE")
    labels = [
        (105, ["Lượt lời thô", "uᵢ"]), (385, ["Chuẩn hóa", "ký tự"]),
        (665, ["Lọc từ dừng", "tiếng Việt"]), (945, ["Túi từ cục bộ", "bᵢ(w)"]),
        (1225, ["Cosine giữa", "hai khối"]),
    ]
    for x, rows in labels:
        box(lines, x, 250, 205, 72, rows, fill=BLUE_BG, stroke=BLUE, size=16)
    for x1, x2 in ((310, 385), (590, 665), (870, 945), (1150, 1225)):
        arrow(lines, x1, 286, x2, 286)

    text(lines, 800, 400, "n ≤ W?", size=20, weight=700)
    lines.append(f'<path d="M800,420 L875,477 L800,534 L725,477 Z" fill="{ORANGE_BG}" stroke="{ORANGE}" stroke-width="2"/>')

    group(lines, 70, 420, 560, 290, "2A", "Chế độ theo lô · n ≤ 40", fill="#F6FCFA", stroke="#A9D8CF")
    box(lines, 115, 485, 470, 63, ["Tính tương đồng trên toàn chuỗi"], fill=TEAL_BG, stroke=TEAL, size=16)
    box(lines, 115, 565, 470, 63, ["Điểm sâu đa bán kính Dᵣ(i)"], fill=TEAL_BG, stroke=TEAL, size=16)
    box(lines, 115, 645, 470, 43, ["τ = μglobal + α·σglobal"], fill="#FFFFFF", stroke=TEAL, size=16)
    arrow(lines, 350, 548, 350, 565, color=TEAL, marker="navy")
    arrow(lines, 350, 628, 350, 645, color=TEAL, marker="navy")

    group(lines, 970, 420, 560, 290, "2B", "Chế độ luồng · n > 40", fill="#FFFAF6", stroke="#EDC2A6")
    box(lines, 1015, 485, 470, 63, ["Cửa sổ W = 40 · bước dịch S = 5"], fill=ORANGE_BG, stroke=ORANGE, size=16)
    box(lines, 1015, 565, 470, 63, ["Dᵣ(i) & Z-score cục bộ từng cửa sổ"], fill=ORANGE_BG, stroke=ORANGE, size=16)
    box(lines, 1015, 645, 470, 43, ["τlocal = μlocal + α·σlocal"], fill="#FFFFFF", stroke=ORANGE, size=16)
    arrow(lines, 1250, 548, 1250, 565, color=ORANGE, marker="orange")
    arrow(lines, 1250, 628, 1250, 645, color=ORANGE, marker="orange")

    poly_arrow(lines, [(800, 420), (800, 387), (350, 387), (350, 420)], color=TEAL, marker="navy")
    text(lines, 565, 402, "Đúng", size=14, weight=700, fill=TEAL)
    poly_arrow(lines, [(875, 477), (930, 477), (930, 460), (970, 460)], color=ORANGE, marker="orange")
    text(lines, 920, 452, "Sai", size=14, weight=700, fill=ORANGE)

    group(lines, 260, 750, 1080, 110, "3", "Trích xuất ranh giới & hậu xử lý", fill="#FBFAFE", stroke="#CCC0DE")
    box(lines, 335, 790, 300, 48, ["Ứng viên D̄(i) > τ"], fill=VIOLET_BG, stroke="#7655A6", size=16)
    arrow(lines, 635, 814, 690, 814)
    box(lines, 690, 790, 330, 48, ["Gộp tham lam · mmin"], fill=VIOLET_BG, stroke="#7655A6", size=16)
    arrow(lines, 1020, 814, 1075, 814)
    box(lines, 1075, 790, 190, 48, ["Ranh giới B"], fill="#FFFFFF", stroke=NAVY, size=16)
    poly_arrow(lines, [(350, 710), (350, 730), (530, 730), (530, 750)], color=TEAL, marker="navy")
    poly_arrow(lines, [(1250, 710), (1250, 730), (1070, 730), (1070, 750)], color=ORANGE, marker="orange")
    save("fig02_sliding_texttiling_workflow", lines)


def hierarchical_summarization() -> None:
    lines = start(1600, 670, "Tích hợp ViT5 và BARTpho", "Kiến trúc tóm tắt phân cấp từ phân đoạn chủ đề đến tiêu đề.")
    group(lines, 55, 55, 450, 520, "1", "Chuẩn bị các khối lượt lời", fill="#F7FBFE")
    box(lines, 100, 125, 360, 68, ["Phân đoạn chủ đề Tₖ"], fill="#FFFFFF")
    arrow(lines, 280, 193, 280, 230)
    text(lines, 100, 260, "CHIA TUẦN TỰ · TỐI ĐA 8 LƯỢT LỜI", size=13, weight=700, fill=GRAY, anchor="start")
    for idx, x in enumerate((100, 220, 340), 1):
        box(lines, x, 280, 100, 76, [f"Cₖ,{idx}", "≤ 8"], fill=BLUE_BG, stroke=BLUE, size=16)
    poly_arrow(lines, [(150, 356), (150, 405), (280, 405)], color=BLUE)
    poly_arrow(lines, [(270, 356), (270, 405), (280, 405)], color=BLUE)
    poly_arrow(lines, [(390, 356), (390, 405), (280, 405)], color=BLUE)
    box(lines, 100, 405, 360, 105, ["Định dạng đầu vào · tối đa 512 tokens", "“Tóm tắt: [Speaker]: [Text] …”"], fill=LIGHT, size=15)

    group(lines, 545, 55, 450, 520, "2", "Tóm tắt từng khối bằng ViT5", fill="#F6FCFA")
    box(lines, 605, 140, 330, 100, ["ViT5-base", "Chunk Summarizer"], fill=TEAL_BG, stroke=TEAL, size=19)
    text(lines, 770, 282, "áp dụng độc lập cho mỗi Cₖ,ⱼ", size=15, fill=GRAY)
    arrow(lines, 770, 305, 770, 350, color=TEAL, marker="navy")
    for idx, x in enumerate((605, 720, 835), 1):
        box(lines, x, 350, 95, 70, [f"qₖ,{idx}"], fill="#FFFFFF", stroke=TEAL, size=17)
    text(lines, 770, 465, "qₖ,₁  /  qₖ,₂  /  …  /  qₖ,ₘ", size=19, weight=700, fill=TEAL)
    box(lines, 605, 495, 330, 48, ["Ghép bằng chuỗi phân tách “ / ”"], fill=LIGHT, size=15)

    group(lines, 1035, 55, 510, 520, "3", "Tạo tiêu đề chủ đề bằng BARTpho", fill="#FFFAF6")
    box(lines, 1090, 125, 400, 76, ["Giữ tối đa 1.500 ký tự cuối", "và tối đa 1.024 tokens"], fill=ORANGE_BG, stroke=ORANGE, size=16)
    arrow(lines, 1290, 201, 1290, 235, color=ORANGE, marker="orange")
    box(lines, 1090, 235, 400, 66, ["“Tạo tiêu đề: …”"], fill="#FFFFFF", stroke=ORANGE, size=17)
    arrow(lines, 1290, 301, 1290, 335, color=ORANGE, marker="orange")
    box(lines, 1090, 335, 400, 92, ["BARTpho-syllable-base", "Topic Titler"], fill=ORANGE_BG, stroke=ORANGE, size=19)
    arrow(lines, 1290, 427, 1290, 465, color=ORANGE, marker="orange")
    box(lines, 1090, 465, 400, 78, ["Tiêu đề chủ đề hₖ"], fill="#FFFFFF", stroke=RED, size=20)

    arrow(lines, 505, 315, 545, 315)
    arrow(lines, 995, 315, 1035, 315, color=ORANGE, marker="orange")
    text(lines, 55, 630, "Đơn vị đầu vào", size=14, fill=GRAY, anchor="start")
    text(lines, 545, 630, "Tầng tóm tắt cục bộ", size=14, fill=TEAL, anchor="start")
    text(lines, 1035, 630, "Tầng tổng hợp chủ đề", size=14, fill=ORANGE, anchor="start")
    save("fig03_hierarchical_summarization", lines)


def event_sequence() -> None:
    lines = start(1600, 950, "Trình tự phát sự kiện", "Trình tự xử lý và phát sự kiện cho một phân đoạn chủ đề đã được xác nhận.")
    participants = [
        (110, 205, "Transcript"), (360, 480, "Bộ điều phối"), (640, 765, "Segmenter"),
        (905, 1025, "ViT5"), (1170, 1300, "BARTpho"), (1420, 1545, "Đầu ra"),
    ]
    centers: list[float] = []
    for x1, x2, label in participants:
        cx = (x1 + x2) / 2
        centers.append(cx)
        box(lines, x1, 55, x2 - x1, 55, [label], fill=LIGHT, stroke=NAVY, size=16)
        lines.append(f'<line x1="{cx}" y1="110" x2="{cx}" y2="900" stroke="#AAB3BC" stroke-width="1.4" stroke-dasharray="7 6"/>')

    def message(y: int, src: int, dst: int, label: str, *, event: bool = False, dashed: bool = False) -> None:
        x1, x2 = centers[src], centers[dst]
        color = ORANGE if event else BLUE
        marker = "orange" if event else "blue"
        arrow(lines, x1, y, x2, y, color=color, marker=marker, dashed=dashed)
        mid = (x1 + x2) / 2
        width = max(170, len(label) * 8.2)
        lines.append(f'<rect x="{mid - width / 2}" y="{y - 29}" width="{width}" height="22" fill="#FFFFFF"/>')
        text(lines, mid, y - 12, label, size=14, weight=700 if event else 400, fill=RED if event else NAVY)

    message(165, 0, 1, "accept_utterance(uᵢ)")
    message(225, 1, 5, "utterance-accepted", event=True)
    message(285, 1, 2, "cập nhật cửa sổ phân đoạn")
    message(345, 2, 1, "ranh giới đã được chốt", dashed=True)

    lines.append(f'<rect x="325" y="385" width="775" height="255" rx="12" fill="#F7FBFE" stroke="{BLUE}" stroke-width="1.4"/>')
    lines.append(f'<path d="M325,385 h190 v34 h-190 z" fill="{BLUE_BG}" stroke="{BLUE}"/>')
    text(lines, 340, 408, "LẶP · MỖI CHUNK ≤ 8 LƯỢT LỜI", size=13, weight=700, fill=BLUE, anchor="start")
    message(465, 1, 3, "văn bản chunk Cₖ,ⱼ")
    message(525, 3, 1, "tóm tắt qₖ,ⱼ", dashed=True)
    message(590, 1, 5, "chunk-closed", event=True)

    message(690, 1, 5, "segment-closed", event=True)
    message(750, 1, 4, "qₖ,₁ / … / qₖ,ₘ")
    message(810, 4, 1, "tiêu đề hₖ", dashed=True)
    message(865, 1, 5, "title-emitted", event=True)

    lines.append(f'<rect x="285" y="905" width="1035" height="34" rx="8" fill="{ORANGE_BG}" stroke="{ORANGE}"/>')
    text(lines, 802, 928, "Khi flush/kết thúc cuộc họp → meeting-completed", size=15, weight=700, fill=RED)
    save("fig10_event_sequence", lines)


def algorithm_plate() -> None:
    lines = start(
        1600,
        1520,
        "Thuật toán Multi-Scale Sliding TextTiling tăng dần",
        "Giả mã có đánh số dòng cho ba thủ tục khởi tạo, cập nhật và kết thúc luồng.",
    )
    lines.append(f'<rect x="55" y="45" width="1490" height="1420" rx="18" fill="#FFFFFF" stroke="#C6CED6" stroke-width="1.8"/>')
    lines.append(f'<rect x="55" y="45" width="1490" height="96" rx="18" fill="{NAVY}"/>')
    lines.append(f'<rect x="55" y="115" width="1490" height="26" fill="{NAVY}"/>')
    text(lines, 92, 90, "THUẬT TOÁN 1", size=17, weight=700, fill="#B9DDF2", anchor="start")
    text(lines, 92, 122, "Multi-Scale Sliding TextTiling tăng dần có trạng thái", size=27, weight=700, fill="#FFFFFF", anchor="start")

    text(lines, 92, 182, "ĐẦU VÀO", size=14, weight=700, fill=GRAY, anchor="start")
    lines.append(f'<rect x="92" y="198" width="1416" height="66" rx="10" fill="{BLUE_BG}" stroke="#B8D9ED"/>')
    text(lines, 120, 239, "Lượt lời uₜ", size=19, weight=700, anchor="start")
    text(lines, 300, 239, "k = 2", size=19, anchor="start")
    text(lines, 440, 239, "R = {3, 5, 10, 15, 20}", size=19, anchor="start")
    text(lines, 750, 239, "α = 1,2", size=19, anchor="start")
    text(lines, 900, 239, "γ = 0,20", size=19, anchor="start")
    text(lines, 1070, 239, "W = 40", size=19, anchor="start")
    text(lines, 1200, 239, "S = 5", size=19, anchor="start")
    text(lines, 1320, 239, "L = 20", size=19, anchor="start")

    text(lines, 92, 298, "ĐẦU RA", size=14, weight=700, fill=GRAY, anchor="start")
    lines.append(f'<rect x="92" y="314" width="1416" height="58" rx="10" fill="{ORANGE_BG}" stroke="#EDC2A6"/>')
    text(lines, 120, 350, "newly_committed — các cặp (chỉ số ranh giới g, điểm sâu D̄(g)) vừa được chốt", size=19, weight=600, anchor="start")

    def section(y: int, height: int, label: str, subtitle: str, fill: str, stroke: str) -> None:
        lines.append(f'<rect x="92" y="{y}" width="1416" height="{height}" rx="12" fill="#FFFFFF" stroke="{stroke}" stroke-width="1.5"/>')
        lines.append(f'<rect x="92" y="{y}" width="1416" height="48" rx="12" fill="{fill}"/>')
        lines.append(f'<rect x="92" y="{y + 36}" width="1416" height="12" fill="{fill}"/>')
        text(lines, 118, y + 31, label, size=19, weight=700, fill=stroke, anchor="start")
        text(lines, 330, y + 31, subtitle, size=16, fill=GRAY, anchor="start")

    def row(number: int, y: int, value: str, indent: int = 0, *, weight: int = 400,
            fill: str = NAVY, highlight: str | None = None) -> None:
        if highlight:
            lines.append(f'<rect x="112" y="{y - 24}" width="1374" height="34" rx="6" fill="{highlight}"/>')
        text(lines, 127, y, f"{number:02d}", size=15, weight=600, fill="#8A95A1", anchor="end")
        lines.append(f'<line x1="145" y1="{y - 21}" x2="145" y2="{y + 8}" stroke="#D7DDE3"/>')
        text(lines, 170 + indent * 38, y, value, size=19, weight=weight, fill=fill, anchor="start")

    section(402, 190, "INITIALIZE()", "Khởi tạo trạng thái cho một cuộc họp mới", TEAL_BG, TEAL)
    row(1, 478, "buffer ← [ ];  next_window_start ← 0")
    row(2, 520, "committed_boundaries ← [ ];  pending_candidates ← { }")
    row(3, 562, "boundary_depths ← { };  last_committed_index ← −1")

    section(616, 555, "UPDATE(uₜ)", "Nhận một lượt lời và chỉ phát các ranh giới đã đủ ngữ cảnh", BLUE_BG, BLUE)
    row(4, 692, "Thêm uₜ vào buffer;  newly_committed ← [ ]")
    row(5, 734, "while  |buffer| − next_window_start ≥ W  do", weight=700, fill=BLUE, highlight="#F4F9FD")
    row(6, 776, "start ← next_window_start;  window ← buffer[start : start + W]", indent=1)
    row(7, 818, "scores ← SimilarityScores(window, k)", indent=1)
    row(8, 860, "depth ← MultiScaleDepth(scores, R, chuẩn hóa Z-score)", indent=1)
    row(9, 902, "τ ← mean(depth) + α · std(depth)", indent=1, weight=600, highlight=ORANGE_BG)
    row(10, 944, "Lưu (g, D̄(g)) nếu D̄(g) > τ và g chưa được chốt", indent=1)
    row(11, 986, "commit_cutoff ← start + W − L", indent=1, weight=600, highlight=TEAL_BG)
    row(12, 1028, "eligible ← {g ∈ pending_candidates | g ≤ commit_cutoff}", indent=1)
    row(13, 1070, "merged ← GreedyMerge(eligible, m_min = max(2, floor(W · γ)))", indent=1)
    row(14, 1112, "Phát (g, D̄(g)) theo thứ tự; cập nhật trạng thái; xóa ứng viên đã xét", indent=1)
    row(15, 1154, "next_window_start ← next_window_start + S", indent=1)

    section(1195, 190, "FLUSH()", "Hoàn tất cửa sổ đuôi khi cuộc họp kết thúc", ORANGE_BG, ORANGE)
    row(16, 1271, "Nếu |buffer| ≤ W: đánh giá toàn bộ buffer; ngược lại: đánh giá cửa sổ đuôi")
    row(17, 1313, "Gộp và phát mọi ứng viên chưa chốt kèm điểm sâu tương ứng")
    row(18, 1355, "Nếu ranh giới cuối ≠ |buffer| − 1: phát (|buffer| − 1, 0)", weight=600)

    lines.append(f'<rect x="92" y="1422" width="1416" height="1" fill="#D7DDE3"/>')
    text(lines, 92, 1452, "Quy ước: W — kích thước cửa sổ; S — bước trượt; L — số lượt lời nhìn trước; D̄(g) — điểm sâu tổng hợp.", size=15, fill=GRAY, anchor="start")
    save("algorithm01_streaming_texttiling", lines)


def main() -> None:
    overall_pipeline()
    texttiling_workflow()
    hierarchical_summarization()
    event_sequence()


if __name__ == "__main__":
    main()
