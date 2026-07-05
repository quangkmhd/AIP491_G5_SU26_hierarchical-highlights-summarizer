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
    SSDST_ABSTRACTIVE = "ssdst_abstractive"
    SSDST_STATE_UPDATE = "ssdst_state_update"


SYSTEM_PROMPT_VI: str = """\
Bạn là engine tạo meeting recap cho ứng dụng AIP491 Meeting Recap Webapp.

Nhiệm vụ duy nhất của bạn là đọc transcript hoặc các đoạn transcript đã được tiền xử lý, sau đó trả về một đối tượng JSON hợp lệ theo đúng schema mà user prompt yêu cầu.

Quy tắc bắt buộc:
- Chỉ trả về JSON parseable. Không dùng Markdown, không dùng code fence, không thêm lời chào, giải thích, phân tích, ghi chú ngoài JSON.
- Không viết mã nguồn, không đưa hướng dẫn triển khai, không mô tả prompt.
- Viết nội dung recap bằng tiếng Việt tự nhiên, ngắn gọn, ở ngôi thứ ba.
- Giữ nguyên technical terms quan trọng nếu chúng xuất hiện trong transcript, ví dụ: API, frontend, backend, model, pipeline, benchmark, test, report.
- Chỉ sử dụng thông tin có trong input. Không bịa người thực hiện, deadline, quyết định, số liệu, nguyên nhân, hoặc kết quả chưa được nói rõ.
- Khi một text field không có bằng chứng trong input, ghi đúng chuỗi "none"; không để trống text field.
- Khi một boolean field không có bằng chứng trong input, dùng false.
- Tôn trọng chính xác ID trong input. Không tự tạo utterance_id, chunk_id, chapter number, speaker name, hoặc timestamp mới.
- Bảo toàn đầy đủ các key bắt buộc trong schema, kể cả khi mảng rỗng.
"""

HIERARCHIC_ABSTRACTIVE_PROMPT_VI: str = """\
Bạn đang thực hiện DR2 Hierarchical abstractive pass cho một hoặc nhiều chunk 8 utterances trong cùng một chapter.

Mục tiêu:
- Tạo ghi chú theo từng chunk để webapp ghép lại thành biên bản cuộc họp dạng chapterized recap.
- Mỗi chunk phải có một ghi chú ngắn, factual, giữ đúng mạch thời gian.

Quy tắc coverage:
- Trả về đúng một note cho mỗi `chunk_id` trong `Required chunk_ids in order`.
- Không bỏ sót chunk_id, không đổi tên chunk_id, không tự tạo chunk_id mới.
- Sắp xếp notes theo đúng thứ tự `Required chunk_ids in order`.
- Nếu không có nội dung rõ cho `summary`, ghi "none".

Quy tắc viết nội dung:
- `summary` viết bằng tiếng Việt, ngôi thứ ba, 1-3 câu, phản ánh nội dung chính của chunk.
- Nếu chunk có quyết định, kết luận, scope, kiến trúc, rủi ro, blocker, hoặc kết quả quan trọng, đặt `contains_key_point` = true.
- Nếu chunk có việc cần làm, phân công, cam kết follow-up, kiểm thử, báo cáo, sửa lỗi, triển khai, hoặc deadline, đặt `contains_action_item` = true.
- Nếu chunk chỉ là trao đổi nền hoặc cập nhật không có điểm chính/action item rõ ràng, vẫn tóm tắt ngắn và đặt các boolean phù hợp là false.
- Giữ speaker names, model names, APIs, metrics, file paths, timestamps, và thuật ngữ kỹ thuật nếu chúng là thông tin quan trọng.
- Không thêm thông tin ngoài chunk. Chỉ dùng các utterances trong chunk tương ứng để viết note của chunk đó.

Input file: {input_name}
Chapter number: {chapter_number}

Required chunk_ids in order:
{required_chunk_ids}

8-utterance chunks:
{prompt_chunks}

Return strict JSON only:
{
  "notes": [
    {
      "chunk_id": "{example_chunk_id}",
      "summary": "Ghi chú factual 1-3 câu bằng tiếng Việt cho đúng chunk này.",
      "contains_key_point": true,
      "contains_action_item": false
    }
  ]
}
"""

HIERARCHIC_TITLE_PROMPT_VI: str = """\
Bạn đang thực hiện DR2 Hierarchical title pass cho một chapter được tạo bởi TextTiling-style segmentation.

Mục tiêu:
- Đặt tiêu đề ngắn cho chapter và viết một câu tóm tắt bao quát nội dung chapter.
- Tiêu đề và tóm tắt phải giúp người đọc scan lại diễn biến cuộc họp theo dòng thời gian.

Quy tắc:
- Chỉ dùng thông tin trong `Segment utterances`.
- `title` dài 4-10 từ tiếng Việt, cụ thể theo chủ đề chapter, không dùng tiêu đề chung chung như "Thảo luận cuộc họp" nếu có thông tin cụ thể hơn.
- `one_line_summary` là đúng một câu, tối đa khoảng 35 từ, nêu chủ đề chính, quyết định, hoặc hướng trao đổi nổi bật của chapter.
- Nếu không có nội dung rõ cho `title` hoặc `one_line_summary`, ghi "none".
- Không nhắc `Chapter number` trong title trừ khi transcript tự nói như vậy.
- Không thêm action item, deadline, hoặc kết quả nếu không có trong segment.

Input file: {input_name}
Chapter number: {chapter_number}

Segment utterances:
{segment_utterances}

Return strict JSON only:
{
  "title": "tiêu đề chapter ngắn gọn bằng tiếng Việt",
  "one_line_summary": "một câu tóm tắt chapter bằng tiếng Việt"
}
"""

SSDST_ABSTRACTIVE_PROMPT_VI: str = """\
Bạn đang thực hiện SS-DST (State-Space Dialogue State Tracking) abstractive pass cho một chunk trong một chapter.

Khác với hierarchical thông thường, bạn KHÔNG tóm tắt chunk trong cô lập. Bạn được cung cấp một "dialogue belief state" (trạng thái nhớ đàm thoại) tích lũy từ các chunk trước đó trong cùng chapter. Dùng belief state này để:
- Giải quyết đại từ và tham chiếu (coreference): "nó", "vấn đề đó", "anh ấy" phải được hiểu dựa trên state.
- Không lặp lại thông tin đã ghi trong state; tập trung vào thông tin MỚI hoặc CẬP NHẬT trong chunk hiện tại.
- Ghi chú factual, giữ đúng mạch thời gian, ngôi thứ ba, tiếng Việt, 1-3 câu.

Quy tắc coverage:
- Trả về đúng một note cho mỗi `chunk_id` trong `Required chunk_ids in order`.
- Không bỏ sót chunk_id, không đổi tên chunk_id, không tự tạo chunk_id mới.
- Sắp xếp notes theo đúng thứ tự `Required chunk_ids in order`.
- Nếu không có nội dung rõ cho `summary`, ghi "none".

Quy tắc viết nội dung:
- `summary` phản ánh nội dung CHÍNH của chunk, có thể tham chiếu thực thể/quyết định từ belief state để câu đầy đủ ý.
- Nếu chunk có quyết định, kết luận, scope, kiến trúc, rủi ro, blocker, hoặc kết quả quan trọng, đặt `contains_key_point` = true.
- Nếu chunk có việc cần làm, phân công, cam kết follow-up, kiểm thử, báo cáo, sửa lỗi, triển khai, hoặc deadline, đặt `contains_action_item` = true.
- Giữ speaker names, model names, APIs, metrics, file paths, timestamps, và thuật ngữ kỹ thuật quan trọng.
- Chỉ dùng các utterances trong chunk tương ứng và belief state để viết note; không bịa thông tin ngoài state và chunk.

Input file: {input_name}
Chapter number: {chapter_number}
Chunk index trong chapter: {chunk_index}

Dialogue belief state (tích lũy từ các chunk trước, dùng để giải quyết tham chiếu):
{belief_state}

Required chunk_ids in order:
{required_chunk_ids}

8-utterance chunks:
{prompt_chunks}

Return strict JSON only:
{
  "notes": [
    {
      "chunk_id": "{example_chunk_id}",
      "summary": "Ghi chú factual 1-3 câu, dùng belief state để giải quyết đại từ/tham chiếu.",
      "contains_key_point": true,
      "contains_action_item": false
    }
  ]
}
"""

SSDST_STATE_UPDATE_PROMPT_VI: str = """\
Bạn đang thực hiện SS-DST state update: cập nhật dialogue belief state sau khi xử lý một chunk.

Belief state là bộ nhớ cuộn (rolling memory) theo kiểu state-space: state mới = cập nhật(state cũ, nội dung chunk mới). Giữ state NGẮN GỌN (dưới ~180 token) bằng cách:
- Thêm thực thể/quyết định/hành động MỚI xuất hiện trong chunk.
- Cập nhật (không trùng lặp) các mục đã thay đổi.
- Áp dụng "forgetting gate": nếu state cũ đã quá dài, ưu tiên giữ decisions và open_actions, lược bớt current_topic/entities ít quan trọng.
- Giải quyết tham chiếu: nếu chunk nhắc "nó"/"vấn đề đó" và state có thực thể phù hợp, ghi rõ thực thể đó vào resolved_references.

Trả về belief state MỚI (toàn bộ, không phải diff) dưới dạng JSON với đúng các key:
- `current_topic`: chủ đề đang thảo luận (1 cụm ngắn).
- `entities`: mảng tên thực thể/người/hệ thống/model quan trọng đang active.
- `decisions`: mảng quyết định/kết luận đã chốt (mỗi mục 1 câu ngắn).
- `open_actions`: mảng hành động cần làm chưa hoàn tất (mỗi mục 1 câu ngắn, kèm assignee nếu có).
- `resolved_references`: mảng tham chiếu đã được giải quyết, dạng {"pronoun": "...", "refers_to": "..."}.

Nếu một key không có nội dung, trả mảng rỗng (hoặc "" cho current_topic). Không bịa thông tin ngoài state cũ và chunk mới.

Chapter number: {chapter_number}
Chunk index: {chunk_index}

Previous belief state (state cũ):
{previous_state}

Chunk vừa xử lý (utterances):
{chunk_text}

Chunk summary vừa tạo:
{chunk_summary}

Return strict JSON only:
{
  "current_topic": "chủ đề ngắn",
  "entities": ["thực thể 1", "thực thể 2"],
  "decisions": ["quyết định 1"],
  "open_actions": ["hành động 1"],
  "resolved_references": [{"pronoun": "nó", "refers_to": "pipeline mới"}]
}
"""


def get_prompt(task: LLMTask) -> str:
    """Return the Vietnamese prompt template for a supported LLM task."""
    mapping = {
        LLMTask.ABSTRACTIVE: HIERARCHIC_ABSTRACTIVE_PROMPT_VI,
        LLMTask.TITLE: HIERARCHIC_TITLE_PROMPT_VI,
        LLMTask.SSDST_ABSTRACTIVE: SSDST_ABSTRACTIVE_PROMPT_VI,
        LLMTask.SSDST_STATE_UPDATE: SSDST_STATE_UPDATE_PROMPT_VI,
    }
    return mapping[task]
