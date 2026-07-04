# Lộ Trình Phát Triển & Thiết Kế Các Models

Dựa trên phân tích `ARCHITECTURE.png` và `system-architecture.md`, dưới đây là lộ trình phát triển hệ thống (thứ tự ưu tiên xây dựng) cùng với danh sách toàn bộ các Model (bao gồm Data Models và AI Models) sẽ cần được tạo lập.

## 1. Trình Tự Thiết Kế & Phát Triển (Implementation Roadmap)

Kiến trúc hệ thống tuân thủ mô hình phân lớp nghiêm ngặt:
`Types -> Config -> Repo -> Service -> Runtime -> UI`

Dựa trên luồng dữ liệu, trình tự phát triển lý tưởng là đi từ **lõi (Khung Dữ Liệu) -> Tầng Lưu Trữ & AI -> Tầng Nghiệp Vụ -> Tầng Giao Diện (Từ trong ra ngoài)**:

1. **Bước 1: Thiết kế Khung Dữ Liệu (Data Models / Types)**
   - *ĐÃ HOÀN THÀNH 2026-07-04 (model-001)*. Định nghĩa hình dáng của các cấu trúc dữ liệu cốt lõi bằng Pydantic v2. Đảm bảo tất cả các tầng phía trên có thể giao tiếp thống nhất với nhau qua các interface mạnh.

2. **Bước 2: Xây dựng Model Loader & File Repository (Repo Layer)** — *TIẾP THEO (model-002)*
   - Repository quản lý File System (đọc raw transcript, lưu recap JSON).
   - `ModelLoader` preload các checkpoint AI Models (BERT, deBERTa, BART) vào CPU/GPU. *Phải làm trước khi viết logic gọi chúng.*

3. **Bước 3: Viết Thuật Toán & Xử Lý Nghiệp Vụ (Service Layer)**
   - `svc-001`: TextTiling + Chunking dùng `CoherenceScorer` (NSP BERT).
   - `svc-002`: `MeetingRecapOrchestrator` kết nối TextTiling -> deBERTa title/abstractive -> BART highlights.

4. **Bước 4: Khung Giao Tiếp API (Runtime / FastAPI)** — `api-001`
   - Bọc services thành RESTful API Endpoints.

5. **Bước 5: Giao Diện (Client / UI)** — `ui-001`
   - Web App hoặc CLI gọi các API ở Bước 4.

=> **Trạng thái tiến độ** (2026-07-04): **Data Model (Khung Types)** ✅ done →
**AI Model Loader** ⏭ next → **TextTiling/Chunking** → **API** → **UI**.

---

## 2. Danh Sách Toàn Bộ Model Sẽ Tạo

Trong hệ thống này, "Model" chia thành 2 loại: **Data Models** (Cấu trúc dữ liệu) và **AI Models** (Mô hình Trí tuệ nhân tạo).

### 2.1. Khung Cấu Trúc Dữ Liệu (Data Models - Tầng Types)

Triển khai bằng `pydantic.BaseModel` thông qua `BaseSchema` chung
(`src/types/_base.py`, `extra="forbid"`, `populate_by_name`,
`str_strip_whitespace`). Tất cả dưới đây đã có code thật và 38/38 unit
test pass (xem `tests/unit/test_types.py`).

| Model | File | Mô tả | Trạng thái |
|-------|------|-------|-----------|
| `Utterance` | `src/types/utterance.py` | Câu thoại đơn lẻ; `frozen=True`, `speaker`/`text` không rỗng, `index >= 0` | ✅ done |
| `DialogueTranscript` | `src/types/transcript.py` | Chuỗi `Utterance` theo thứ tự; validate chỉ số liên tục 0..N-1, enforce `MAX_UTTERANCES = 5000` | ✅ done |
| `Chunk` | `src/types/segment.py` | Khối thoại ≤ 8 câu; enforce `MAX_CHUNK_SIZE = 8` qua `ClassVar` | ✅ done |
| `SegmentResult` | `src/types/segment.py` | Chương (Chapter) gồm nhiều `Chunk`; có `user_title_override` + `display_title` | ✅ done |
| `HighlightType` | `src/types/highlight.py` | Enum: `KEY_POINT` (UI "note") / `ACTION_ITEM` (UI "task"); canonical wire value `"key_point"` / `"action_item"` | ✅ done |
| `HighlightSource` | `src/types/highlight.py` | Enum: `AUTO` / `MANUAL` | ✅ done |
| `Highlight` | `src/types/highlight.py` | Key-point hoặc action-item; `toggle_star` / `toggle_check` trả về `model_copy` | ✅ done |
| `MeetingStatus` | `src/types/hierarchical_recap.py` | Enum: `QUEUED` / `PROCESSING` / `COMPLETED` / `FAILED` | ✅ done |
| `HierarchicalRecap` | `src/types/hierarchical_recap.py` | Kết quả cuối; gồm `segments`, `highlights_notes`, `highlights_tasks`, `generated_at`, `processing_time_ms` | ✅ done |
| `TranscriptIngestionRequest` | `src/types/schemas.py` | API request: nhận `utterances` *hoặc* `flat_texts`; có `materialize()` enforce `MAX_UTTERANCES` | ✅ done |
| `HighlightUpsertRequest` | `src/types/schemas.py` | API request: tạo / sửa highlight | ✅ done |
| `MeetingProcessResponse` | `src/types/schemas.py` | API response: `meeting_id`, `status`, optional `recap`, optional `error` | ✅ done |

### 2.2. Các Mô Hình Trí Tuệ Nhân Tạo (AI Models - Tầng Repo & Service)

Các AI Models này được tải từ bộ trọng số checkpoint thông qua thư viện
`transformers` của Hugging Face. Chưa có code thật (chờ `model-002`).

1. **NSP BERT / CoherenceNet** — *Chưa tải*
   - Chấm điểm độ liên kết giữa 2 câu thoại liền kề.
   - Checkpoint gợi ý: `vibert_checkpoints_vi/cpt_1000.pth` (đã có sẵn trong repo).
   - Vị trí dùng: TextTiling trong `svc-001`.

2. **deBERTa (hierarchical_title_model)** — *Chưa tải*
   - Sinh Chapter Title ngắn gọn từ full `Segment`.
   - Vị trí dùng: `MeetingRecapOrchestrator` trong `svc-002`.

3. **deBERTa (hierarchical_abstractive_model)** — *Chưa tải*
   - Sinh rolling summary 3rd-person từ mỗi `Chunk`.
   - Vị trí dùng: `MeetingRecapOrchestrator` trong `svc-002`.

4. **BART (highlights_extractive & highlights_abstractive)** — *Chưa tải*
   - Trích xuất và paraphrase Key-Points / Action Items.
   - Vị trí dùng: `MeetingRecapOrchestrator` trong `svc-002`.

---

## 3. Mapping Data Models ↔ Paper Concepts

| Paper 1 (Topic Segmentation) | Paper 2 (Hierarchical Recap) | Code Model |
|----|----|----|
| Dialogue | Meeting | `DialogueTranscript` |
| Turn / Utterance | Utterance | `Utterance` |
| Topic boundary | Chapter / Segment | `SegmentResult` |
| Window of 8 utterances | Chunk (context window for 512-token limit) | `Chunk` |
| NSP coherence score (not stored) | — | computed by `CoherenceScorer` (svc-001) |
| — | Chapter title | `SegmentResult.title` / `user_title_override` |
| — | Chunk rolling summary | `Chunk.rolling_summary` |
| — | Key-point (note) | `Highlight(type=KEY_POINT)` |
| — | Action-item (task) | `Highlight(type=ACTION_ITEM)` |
| — | Full recap | `HierarchicalRecap` |
