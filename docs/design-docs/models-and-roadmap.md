# Lộ Trình Phát Triển & Thiết Kế Các Models

Dựa trên phân tích `ARCHITECTURE.png` và `system-architecture.md`, dưới đây là lộ trình phát triển hệ thống (thứ tự ưu tiên xây dựng) cùng với danh sách toàn bộ các Model (bao gồm Data Models và AI Models) sẽ cần được tạo lập.

## 1. Trình Tự Thiết Kế & Phát Triển (Implementation Roadmap)

Kiến trúc hệ thống tuân thủ mô hình phân lớp nghiêm ngặt:
`Types -> Config -> Repo -> Service -> Runtime -> UI`

Dựa trên luồng dữ liệu, trình tự phát triển lý tưởng là đi từ **lõi (Khung Dữ Liệu) -> Tầng Lưu Trữ & AI -> Tầng Nghiệp Vụ -> Tầng Giao Diện (Từ trong ra ngoài)**:

1. **Bước 1: Thiết kế Khung Dữ Liệu (Data Models / Types)**
   - *Làm ĐẦU TIÊN*. Cần định nghĩa hình dáng của các cấu trúc dữ liệu cốt lõi (Bản ghi, Câu thoại, Phân đoạn, Khối 8 câu, Kết quả tóm tắt) bằng `Pydantic` hoặc `Dataclasses`. Điều này đảm bảo tất cả các tầng phía trên có thể giao tiếp thống nhất với nhau qua các interface mạnh.

2. **Bước 2: Xây dựng Model Loader & File Repository (Repo Layer)**
   - Viết các Repository quản lý File System (đọc file raw txt/json đầu vào và lưu file kết quả).
   - Viết `Model Loader` để tải trước (preload) các checkpoint của AI Models (BERT, deBERTa, BART) vào bộ nhớ (CPU/GPU). *Load mô hình AI phải làm trước khi viết logic gọi chúng.*

3. **Bước 3: Viết Thuật Toán & Xử Lý Nghiệp Vụ (Service Layer)**
   - *Thuật toán Chunking*: Viết bộ tách `Segment` thành các `Chunk` <= 8 câu thoại.
   - *TextTiling Service*: Cài đặt thuật toán TextTiling sử dụng `CoherenceScorer` (NSP BERT) để tính toán điểm phân tách biên giới giữa các câu thoại.
   - *Summarization Orchestrator (MeetingRecapOrchestrator)*: Viết luồng Orchestrator để kết nối dữ liệu: Gọi TextTiling để cắt đoạn -> Gọi Chunking -> Gọi deBERTa/BART để sinh tiêu đề và tóm tắt.

4. **Bước 4: Xây Dựng Khung Giao Tiếp API (Runtime / FastAPI)**
   - Bọc toàn bộ các Services ở Bước 3 lại thành các Restful API Endpoints (`POST /api/v1/meetings/process`, `GET /api/v1/meetings/{id}/recap`, v.v.).

5. **Bước 5: Phát triển Giao Diện (Client / UI)**
   - *Làm CUỐI CÙNG*. Xây dựng Web App hoặc CLI tool gọi đến các API đã tạo ở Bước 4.

=> **Tóm tắt mức độ ưu tiên**: **Data Model (Khung Types)** -> **AI Model Loader** -> **Thuật toán Chunking/TextTiling** -> **API Framework (FastAPI)** -> **Giao diện (UI)**.

---

## 2. Danh Sách Toàn Bộ Model Sẽ Tạo

Trong hệ thống này, "Model" chia thành 2 loại: **Data Models** (Cấu trúc dữ liệu) và **AI Models** (Mô hình Trí tuệ nhân tạo).

### 2.1. Khung Cấu Trúc Dữ Liệu (Data Models - Tầng Types)

Các model này thường được triển khai bằng `pydantic.BaseModel` để đảm bảo validate tự động:

1. **`Utterance` (Câu thoại)**:
   - Người nói (`speaker`).
   - Nội dung văn bản (`text`).
   - Thứ tự / Timestamp (`index`, `timestamp`).
2. **`Chunk` (Khối thoại)**:
   - Chứa một mảng các `Utterance` (Giới hạn tối đa 8 câu do Context window).
   - Chứa kết quả nội dung tóm tắt ngôi thứ 3 (`abstractive_summary`).
3. **`Segment` (Phân đoạn / Chương)**:
   - Chứa mảng các `Chunk`.
   - Tiêu đề chương (`chapter_title`).
   - Vị trí bắt đầu và kết thúc (`start_idx`, `end_idx`).
4. **`Highlight` (Ghi chú nổi bật)**:
   - Phân loại (`type`: Key-point hoặc Action Item).
   - Nội dung chi tiết (`text`).
   - Trạng thái thao tác UI (`is_starred`, `is_checked`).
5. **`HierarchicalRecap` (Kết quả họp phân cấp)**:
   - Metadata cơ bản (`meeting_id`, `date`).
   - Danh sách các `Segment` theo thứ tự thời gian.
   - Danh sách các `Highlight` toàn cục của cuộc họp.
6. **API Request / Response Models**:
   - `TranscriptIngestionRequest`: Dữ liệu gửi lên API.
   - `HighlightUpsertRequest`: Dữ liệu cập nhật Highlight thủ công.

### 2.2. Các Mô Hình Trí Tuệ Nhân Tạo (AI Models - Tầng Repo & Service)

Các AI Models này được tải từ bộ trọng số checkpoint thông qua thư viện `transformers` của Hugging Face:

1. **NSP BERT / CoherenceNet**:
   - *Mục đích*: Chấm điểm độ liên kết (Coherence Score) giữa 2 câu thoại liền kề.
   - *Vị trí dùng*: Xử lý trong thuật toán Neural TextTiling để tìm ra lúc nào người dùng chuyển chủ đề.
2. **deBERTa (hierarchical_title_model)**:
   - *Mục đích*: Sinh ra Tiêu Đề Chương (Chapter Title).
   - *Cách hoạt động*: Nhận đầu vào là toàn bộ văn bản của 1 `Segment` và trả ra 1 câu tiêu đề cực ngắn (VD: "Thiết kế UI Dark Mode").
3. **deBERTa (hierarchical_abstractive_model)**:
   - *Mục đích*: Chuyển đổi hội thoại thành dạng văn bản trần thuật (Summary ở ngôi thứ 3).
   - *Cách hoạt động*: Đọc từng `Chunk` (8 câu thoại) để trích xuất nội dung tóm tắt tránh bị quá tải 512 tokens giới hạn.
4. **BART (highlights_extractive & highlights_abstractive)**:
   - *Mục đích*: Trích xuất (Extractive) và Sinh mới nội dung (Abstractive) cho các Điểm chính (Key-Points) và Hành động (Action Items).
   - *Cách hoạt động*: Chắt lọc từ nội dung của `Segment` hoặc toàn cuộc họp.
