# Meeting Recap Webapp (Tổng Quan Kiến Trúc Hệ Thống)

Dự án này là hệ thống xử lý và tóm tắt cuộc họp tự động từ văn bản Speech-to-Text (ASR transcript) thô. Mục tiêu chính của hệ thống là chuẩn hóa cấu trúc hội thoại đầu vào, sửa lỗi từ vựng/thuật ngữ, và áp dụng các phương thức tóm tắt đa dạng để tạo ra thông tin cô đọng, dễ hiểu cho người dùng.

---

## 1. Các Tài Liệu Chuyên Sâu (Documentation)

*   📖 **[Tài liệu Kiến Trúc Chi Tiết & Biểu Đồ Luồng Dữ Liệu (readme-architecture.md)](file:///home/quangnhvn34/dev/me/AIP491/tools/09-meeting-recap-webapp/readme-architecture.md)**: Phân tích sâu luồng đi của dữ liệu từ ASR thô qua Lexnorm đến tóm tắt, kèm biểu đồ đường đi (Mermaid diagram).
*   🚀 **[Hướng dẫn Vận Hành & Đánh giá (readme-huong-dan.md)](file:///home/quangnhvn34/dev/me/AIP491/tools/09-meeting-recap-webapp/readme-huong-dan.md)**: Quy trình tạo tập dữ liệu test và quy trình tính toán các chỉ số lỗi WER/CER, ma trận nhầm lẫn.
*   📊 **[Báo cáo Kết quả Đánh giá Lexnorm (eval/bao-cao-danh-gia-lexnorm.md)](file:///home/quangnhvn34/dev/me/AIP491/tools/09-meeting-recap-webapp/eval/bao-cao-danh-gia-lexnorm.md)**: Kết quả đo lường thực tế trên tập dữ liệu thử nghiệm 239 phân đoạn hội thoại.

---

## 2. Thiết Kế Kiến Trúc & Luồng Xử Lý Đầu Cuối (End-to-End Architecture)

Hệ thống được thiết kế dạng đường ống (pipeline) chia làm 3 tầng xử lý chính:

```
[ASR Transcript Thô] 
        │
        ▼
┌─────────────────────────────────┐
│ 1. Chuẩn Hóa Từ Vựng (Lexnorm)  │ ──► Dùng LLM cục bộ sửa lỗi chính tả, thêm dấu câu,
└─────────────────────────────────┘     khôi phục thuật ngữ chuyên ngành (Docker, deploy...)
        │
        ▼
┌─────────────────────────────────┐
│ 2. Tóm Tắt Biên Bản (Summary)   │
└─────────────────────────────────┘
        ├─► Highlights Recap (DR1) ──► Trích xuất phẳng AI Notes & AI Tasks
        │
        └─► Hierarchical Recap (DR2) ─► Semantic Chunking & tóm tắt theo chương (Chapters)
        │
        ▼
[JSON Result & Langfuse Tracing]
```

### 2.1. Tầng Chuẩn Hóa Từ Vựng (Lexical Normalization - Lexnorm)
ASR thô từ các mô hình Speech-to-Text thường gặp vấn đề: viết hoa toàn bộ, không có dấu câu, sai âm vị hoặc viết bồi thuật ngữ tiếng Anh. Module Lexnorm khắc phục bằng cách:
*   Phân rã văn bản thô thành các lượt thoại tương ứng với mốc thời gian và người nói.
*   Sử dụng phương pháp **Cửa sổ trượt (Sliding Window)** (3 lượt thoại trước + 3 lượt thoại sau) làm ngữ cảnh bổ trợ gửi cho LLM.
*   Thiết lập **Prompt Hệ thống (System Prompt) với 7 quy tắc an toàn nghiêm ngặt** để LLM chỉ thực hiện thay thế từ lỗi cục bộ dưới dạng JSON có cấu trúc, không tự ý viết lại văn phong hoặc thêm bớt thông tin.

### 2.2. Tầng Tóm Tắt Đa Phương Thức (Summarization Methods)
Sau khi có transcript sạch, hệ thống chạy song song hai thuật toán tóm tắt độc lập:
*   **Highlights Recap (DR1):** Tóm tắt dạng danh sách phẳng, chia rõ ràng thành **Ghi chú quan trọng (AI Notes)** và **Nhiệm vụ cần thực hiện (AI Tasks)** (kèm thông tin phân công người thực hiện).
*   **Hierarchical Recap (DR2):** Phân đoạn biên bản cuộc họp theo tiến trình thời gian và chủ đề (**Semantic Chunking**). Tạo ra mục lục cuộc họp bao gồm các **Chương (Chapters)**, trong mỗi chương có tóm tắt chương và các **Ý chính thảo luận (Key Points)**.

### 2.3. Tầng Quản Lý Tài Nguyên & Quan Sát (Lifecycle & Observability)
*   **Ollama Lifecycle Management:** Giải phóng tài nguyên hệ thống bằng cách tự động tắt mô hình ngôn ngữ lớn khỏi bộ nhớ GPU (`ollama stop`) ngay sau khi hoàn thành phiên xử lý.
*   **Langfuse Tracing:** Ghi vết tự động toàn bộ quy trình: từ đầu vào thô, các bước trung gian gọi LLM sửa lỗi từ, cho đến bước tóm tắt cuối cùng. Cho phép đồng nghiệp và nhà phát triển theo dõi trực quan độ trễ, prompt và kết quả của từng node trên dashboard Langfuse.
