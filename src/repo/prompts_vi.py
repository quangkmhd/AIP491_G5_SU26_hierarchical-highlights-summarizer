"""Vietnamese prompt templates for hierarchical meeting recap tasks.

The prompt text is vendored from ``references_code/prompts.yaml`` so runtime
code has a stable repo-layer registry and does not depend on reference files.
Highlights prompts are intentionally excluded because the product scope is
streaming hierarchical recap only.
"""

from __future__ import annotations

from enum import Enum


class LLMTask(str, Enum):
    """Hierarchical recap LLM tasks served by the Vietnamese backbone."""

    ABSTRACTIVE = "hierarchical_abstractive"
    TITLE = "hierarchical_title"


SYSTEM_PROMPT_VI: str = """\
Bạn là chuyên gia tóm tắt Meeting.

Nhiệm vụ duy nhất của bạn là tóm tắt transcript cuộc họp theo yêu cầu.

Quy tắc bắt buộc:
- Viết nội dung recap bằng tiếng Việt tự nhiên, ngắn gọn, ở ngôi thứ ba.
- Chỉ sử dụng thông tin có trong input. Không bịa
"""

HIERARCHIC_ABSTRACTIVE_PROMPT_VI: str = """\
Bạn đang thực hiện Hierarchical abstractive cho một chunk 8 utterances trong cùng một đoạn hội thoại.

Mục tiêu:
- Tạo tóm tắt theo từng chunk
- Mỗi chunk phải có một ghi chú ngắn, factual, giữ đúng mạch thời gian.

Quy tắc viết nội dung:
- Viết bằng tiếng Việt, ngôi thứ ba, 1-3 câu, phản ánh nội dung chính của chunk.
- Không thêm thông tin ngoài chunk. Chỉ dùng các utterances trong chunk tương ứng để viết note của chunk đó.

8-utterance chunks:
{prompt_chunks}
"""

HIERARCHIC_TITLE_PROMPT_VI: str = """\
Bạn đang thực hiện Hierarchical title cho một đoạn hội thoại.

Mục tiêu:
- Đặt tiêu đề ngắn cho đoạn thội thoại và viết một câu tóm tắt bao quát nội dung.
- Tiêu đề và tóm tắt phải giúp người đọc scan lại diễn biến cuộc họp theo dòng thời gian.

Quy tắc:
- Chỉ dùng thông tin trong `Segment utterances`.
- Tiêu đề dài 4-10 từ tiếng Việt, cụ thể theo chủ đề đoạn hội thoại, không dùng tiêu đề chung chung như "Thảo luận cuộc họp" nếu có thông tin cụ thể hơn.
- Tóm tắt là đúng một câu, tối đa khoảng 35 từ, nêu chủ đề chính, quyết định, hoặc hướng trao đổi nổi bật của chapter.
- Nếu không có nội dung rõ cho tiêu đề hoặc tóm tắt, ghi "none".

Segment utterances:
{segment_utterances}

Trả về hai dòng: dòng 1 là tiêu đề, dòng 2 là tóm tắt một câu.
"""

def get_prompt(task: LLMTask) -> str:
    """Return the Vietnamese prompt template for a supported LLM task."""
    mapping = {
        LLMTask.ABSTRACTIVE: HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
        LLMTask.TITLE: HIERARCHIC_TITLE_PROMPT_VI,
    }
    return mapping[task]
