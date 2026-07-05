"""Vietnamese prompt templates for the 4 paper-2 LLM tasks.

Per the model-002 design spec (D2), the project collapses paper-2's
4 fine-tuned models (BART/deBERTa) into a single Vietnamese instruct
LLM with one prompt per task. The prompts live in this module so they
can be tuned without touching loader or service code.
"""

from __future__ import annotations

from enum import Enum


class LLMTask(str, Enum):
    """The four paper-2 tasks the LLM backbone must serve."""

    SEGMENT = "segment"
    ABSTRACTIVE = "abstractive"
    TITLE = "title"
    HIGHLIGHTS = "highlights"


HIERARCHIC_SEGMENT_PROMPT_VI: str = (
    "Bạn là trợ lý phân đoạn hội thoại tiếng Việt. "
    "Cho hai câu thoại liên tiếp, hãy trả lời DUY NHẤT một số từ 0 đến 1 "
    "thể hiện xác suất có sự chuyển chủ đề giữa chúng. "
    "1 = chắc chắn chuyển chủ đề, 0 = cùng chủ đề.\n"
    "Câu trước: {prev}\n"
    "Câu sau: {next}\n"
    "Xác suất:"
)

HIERARCHIC_ABSTRACTIVE_PROMPT_VI: str = (
    "Bạn là trợ lý tóm tắt cuộc họp tiếng Việt. "
    "Hãy viết một câu tóm tắt ở ngôi thứ ba (ví dụ: 'Nhóm đã thống nhất...') "
    "cho đoạn hội thoại sau (tối đa 8 câu thoại). "
    "Giữ nguyên các tên riêng và số liệu quan trọng.\n"
    "Đoạn hội thoại:\n{chunk}\n"
    "Tóm tắt:"
)

HIERARCHIC_TITLE_PROMPT_VI: str = (
    "Bạn là trợ lý đặt tiêu đề chương cho biên bản họp tiếng Việt. "
    "Hãy đặt một tiêu đề ngắn (tối đa 8 từ) bằng tiếng Việt, "
    "phản ánh chủ đề chính của đoạn hội thoại sau.\n"
    "Đoạn hội thoại:\n{segment}\n"
    "Tiêu đề:"
)

HIGHLIGHTS_PROMPT_VI: str = (
    "Bạn là trợ lý trích xuất điểm nhấn cuộc họp tiếng Việt. "
    "Cho một đoạn hội thoại (khoảng 10 câu), hãy trích ra các ý chính "
    "(KEY_POINT) và các hành động cần làm (ACTION_ITEM) dưới dạng JSON "
    "với các khóa 'type' (key_point | action_item) và 'text'. "
    "Mỗi mục nên ngắn gọn, dùng ngôi thứ ba.\n"
    "Đoạn hội thoại:\n{window}\n"
    "JSON:"
)


def get_prompt(task: LLMTask) -> str:
    """Return the Vietnamese prompt template for a given LLM task."""
    mapping = {
        LLMTask.SEGMENT: HIERARCHIC_SEGMENT_PROMPT_VI,
        LLMTask.ABSTRACTIVE: HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
        LLMTask.TITLE: HIERARCHIC_TITLE_PROMPT_VI,
        LLMTask.HIGHLIGHTS: HIGHLIGHTS_PROMPT_VI,
    }
    return mapping[task]
