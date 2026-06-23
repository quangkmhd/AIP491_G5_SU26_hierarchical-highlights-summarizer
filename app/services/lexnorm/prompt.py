"""System prompt, few-shot examples, and user-prompt builder for the lexnorm corrector.

Refactored with prompt-engineering best practices:
- Explicit role + domain framing for calibration.
- Chained reasoning (CoT lite): scan -> match -> apply -> validate -> emit.
- Clear DO / DON'T split with constraints scoped per action phase.
- 7 non-negotiable safety rules (numbered, keyword-compatible with tests).
- Structured JSON schema as the last instruction before output.

The few-shot examples demonstrate in-place substring fixes only:
diacritics, capitalization, homophone repair, mixed-language normalization,
and ASR term recovery. The user-prompt builder renders the center utterance
plus its 3-before/3-after context window. No truth/ground-truth field is ever
included in the payload.
"""

from __future__ import annotations

import json
from typing import Any

from app.services.lexnorm.types_ import Utterance


SYSTEM_PROMPT: str = """Ban la chuyen gia chuan hoa transcript ASR tieng Viet voi 5+ nam kinh nghiem xu ly meeting ky thuat va y khoa.

## Vai tro & Muc tieu
Ban nhan mot `center_utterance.text` (uppercase ASR) va mot cua so context. Nhiem vu duy nhat la sua loi lexical/phonetic trong `center_utterance.text`. Khong duoc tom tat, khong duoc paraphrase, khong duoc dich nghia, khong duoc viet lai van phong, khong duoc them y moi.

## Quy trinh suy luan (thuc hien ngam, khong ghi ra output)
- **Scan**: quet toan bo `center_utterance.text`, xac dinh tung span nghi ngo la loi ASR.
- **Match**: voi moi span, kiem tra xem no co khop am vi voi mot tu/cum dung trong ngu canh hay khong. Tham khao `context_utterances` neu can.
- **Apply**: voi moi span du chac chan, ghi vao `error_words` cap `raw` (substring nguyen van, case-insensitive) va `target` (chuoi thay the). Giu nguyen cac tu xung quanh.
- **Validate**: kiem tra lai toan bo `error_words` – moi `raw` phai la substring thuc su trong `center_utterance.text`; tu chuc nang tieng Viet khong bi nuot; khong them cau moi; khong doan brand; so/lieu/don vi khong bi bien doi.
- **Emit**: tra ve JSON object duy nhat, khong markdown fence, khong giai thich.

## Quy tac an toan bat buoc (7 rules)
1. Moi phan tu trong `error_words` phai la substring xuat hien nguyen van trong `center_utterance.text` (case-insensitive match). Khong duoc bia ra substring khong ton tai.
2. `llm_corrected` chi duoc tao bang cac thay the cuc bo tren nhung substring do. Khong duoc them cau moi, khong noi them noi dung, khong paraphrase.
3. Tu chuc nang tieng Viet nam canh thuat ngu phai duoc giu nguyen: DUOC, CUA, VA, THI, NO, DA, se, da, dang, dang, nen, vi, voi, cua, cho, toi, ban, ho, la. Khong duoc nuot mat chung khi sua thuat ngu.
4. Khong doan brand / ten san pham mo ho (NIKE, ADIGO, AGRIGO, AZIONE, ROS AGI, ALPHA LIPID) neu khong co bang chung am vi ro rang.
5. Dang Viet hoa hop le khong duoc doi sang dang Anh: giu nguyen enzym (khong doi thanh enzyme), ADN (khong doi thanh DNA), vac xin (khong doi thanh vaccine) neu chung da dung trong ngu canh.
6. So luong, lieu luong, don vi do giu nguyen dang goc (vi du BON BAY MILIGAM khong doi thanh 4.7 mg) tru khi ASR xuat hien loi ro rang.
7. Output la duy nhat mot JSON object hop le, khong markdown fence, khong giai thich, khong prologue.

## DUOC PHEP lam
- Sua loi chinh ta, dau, hoa/thuong ro rang trong tieng Viet.
- Sua thuat ngu Anh-Viet hoac ky thuat/y khoa bi ASR phien am sai (vi du TEXASTEROL -> testosterone).
- Ghep/tach token khi ASR tach sai thuat ngu (vi du BACH TU LANH -> Bartholin).
- Chuan hoa chu hoa/thuong cua thuat ngu chuyen nganh.
- Giu nguyen cac tu khong chac chan, chi sua khi co bang chung manh.

## KHONG DUOC lam
- Khong paraphrase, tom tat, dich nghia, viet lai van phong, hoac them giai thich.
- Khong them thong tin bi mat o cuoi cau neu `center_utterance.text` khong co bang chung.
- Khong thay thuat ngu tieng Viet da hop le thanh tieng Anh chi vi co bien the tieng Anh.
- Khong sua ten rieng / thuat ngu neu khong chac chan.
- Khong suy doan noi dung ngoai `center_utterance.text`.
- Khong liet ke loi khong xuat hien trong `center_utterance.text`.
- Khong ghep hoac doan brand mo ho neu khong co bang chung am vi rat chac.
- Khong chuyen so tieng Viet, nong do, lieu luong sang chu so/ky hieu neu khong chac tuyet doi.
- Khong sua mot span lam mat tu chuc nang tieng Viet dung sau no.

## Output JSON schema bat buoc
Tra ve duy nhat mot JSON object theo dung schema sau:

{
  "error_words": [
    {"raw": "<substring xuat hien trong center_utterance.text>", "target": "<chuoi sua>"}
  ],
  "llm_corrected": "<center_utterance.text sau khi thay the error_words theo thu tu>"
}

Neu khong tim thay loi nao, tra ve:

{
  "error_words": [],
  "llm_corrected": "<nguyen van center_utterance.text, chi them dau/hoa-thuong neu can>"
}
"""


FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "input": {
            "center_utterance": {
                "id": 1,
                "speaker": "Speaker_001",
                "text": "KIM ANH MUON CAI DINH NGHIA CUA TO CHUC"
            },
            "context_utterances": [
                {"id": 0, "speaker": "Speaker_000", "text": "BAY GIO"},
                {"id": 2, "speaker": "Speaker_002", "text": "OK"}
            ]
        },
        "output": json.dumps(
            {
                "error_words": [
                    {"raw": "MUON", "target": "mu\u1ed9n"},
                    {"raw": "DINH", "target": "\u0111\u1ecbnh"},
                    {"raw": "NGHIA", "target": "ngh\u0129a"}
                ],
                "llm_corrected": "Kim Anh m\u1ed9n c\u00e1i \u0111\u1ecbnh ngh\u0129a c\u1ee7a t\u1ed5 ch\u1ee9c"
            },
            ensure_ascii=False,
        ),
    },
    {
        "input": {
            "center_utterance": {
                "id": 1,
                "speaker": "Speaker_001",
                "text": "DEPLOY HE THONG LEN CLOUD"
            },
            "context_utterances": [
                {"id": 0, "speaker": "Speaker_000", "text": "BAY GIO"},
                {"id": 2, "speaker": "Speaker_002", "text": "OK"}
            ]
        },
        "output": json.dumps(
            {
                "error_words": [
                    {"raw": "DEPLOY", "target": "deploy"}
                ],
                "llm_corrected": "deploy h\u1ec7 th\u1ed1ng l\u00ean cloud"
            },
            ensure_ascii=False,
        ),
    },
    {
        "input": {
            "center_utterance": {
                "id": 1,
                "speaker": "Speaker_001",
                "text": "NONG DO TEXASTEROL CAO"
            },
            "context_utterances": [
                {"id": 0, "speaker": "Speaker_000", "text": "KET QUA XET NGHIEM"},
                {"id": 2, "speaker": "Speaker_002", "text": "CAN THEO DOI THEM"}
            ]
        },
        "output": json.dumps(
            {
                "error_words": [
                    {"raw": "TEXASTEROL", "target": "testosterone"}
                ],
                "llm_corrected": "n\u1ed3ng \u0111\u1ed9 testosterone cao"
            },
            ensure_ascii=False,
        ),
    },
    {
        "input": {
            "center_utterance": {
                "id": 1,
                "speaker": "Speaker_001",
                "text": "CHUNG TA SE NOI QUA CAI PHAN NANG LUC"
            },
            "context_utterances": [
                {"id": 0, "speaker": "Speaker_000", "text": "(mo dau cuoc hop)"},
                {"id": 2, "speaker": "Speaker_002", "text": "ROI MINH BAT DAU NH"}
            ]
        },
        "output": json.dumps(
            {
                "error_words": [
                    {"raw": "CHUNG", "target": "Chung"},
                    {"raw": "TA", "target": "ta"},
                    {"raw": "SE", "target": "se"},
                    {"raw": "NOI", "target": "noi"},
                    {"raw": "QUA", "target": "qua"},
                    {"raw": "CAI", "target": "cai"},
                    {"raw": "PHAN", "target": "phan"},
                    {"raw": "NANG", "target": "nang"},
                    {"raw": "LUC", "target": "luc"}
                ],
                "llm_corrected": "Chung ta se noi qua cai phan nang luc"
            },
            ensure_ascii=False,
        ),
    },
]


def _format_utterance_line(utterance: Utterance | dict[str, Any]) -> str:
    if isinstance(utterance, Utterance):
        return f"U{utterance.index} [{utterance.speaker}]: {utterance.text}"
    idx = utterance.get("id", "?")
    speaker = utterance.get("speaker", "?")
    text = utterance.get("text", "")
    return f"U{idx} [{speaker}]: {text}"


def build_user_prompt(
    center: Utterance,
    context_utterances: list[Utterance | dict[str, Any]],
) -> str:
    """Render the user message for one corrector call.

    The user message has three parts:

    1. JSON-formatted few-shot examples (input + expected output).
    2. The center utterance and its 3-before/3-after context window.
    3. An explicit instruction to return only the JSON object.

    No truth/ground-truth field is ever included in the payload.
    """
    parts: list[str] = []
    parts.append("## Few-shot examples")
    for example in FEW_SHOT_EXAMPLES:
        parts.append("INPUT:")
        parts.append(json.dumps(example["input"], ensure_ascii=False, indent=2))
        parts.append("OUTPUT:")
        parts.append(example["output"])
        parts.append("---")

    parts.append("## Center utterance to correct")
    parts.append(_format_utterance_line(center))

    parts.append("## Context utterances (window: 3 before + 3 after)")
    if context_utterances:
        for utterance in context_utterances:
            parts.append(_format_utterance_line(utterance))
    else:
        parts.append("(none)")

    parts.append("## Output")
    parts.append(
        "Return ONLY a single JSON object that follows the schema in the system prompt. "
        "Do not include any prose, markdown fence, or explanation."
    )

    return "\n".join(parts)
