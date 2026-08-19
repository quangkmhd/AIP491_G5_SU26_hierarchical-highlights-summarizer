# 📖 Hierarchical Text Summarization & Topic Segmentation Service

Dịch vụ **Tóm Tắt Văn Bản Phân Cấp & Phân Đoạn Chủ Đề Cuộc Họp** được xây dựng trên framework **FastAPI**, tích hợp thuật toán phân đoạn chủ đề đa tỷ lệ **Multiscale TextTiling** cùng hai mô hình Deep Learning **ViT5 (Chunk Summarizer)** và **BARTpho (Topic Titler)**.

---

## 🚀 1. Khởi Chạy Server

Khởi chạy Uvicorn Web Server ở chế độ Factory:

```bash
uvicorn src.runtime.api:create_app --factory --host 0.0.0.0 --port 8000
```

Hoặc sử dụng `uv`:

```bash
uv run uvicorn src.runtime.api:create_app --factory --host 0.0.0.0 --port 8000
```

Địa chỉ lắng nghe của Server: **`http://localhost:8000`**

---

## 📡 2. Danh Sách API Endpoints & Cách Kết Nối

### 1️⃣ `GET /health` — Kiểm Tra Trạng Thái Dịch Vụ

- **Phương thức:** `GET`
- **URL:** `http://localhost:8000/health`
- **Chức năng:** Kiểm tra dịch vụ Web Server có đang chạy bình thường hay không.

#### Ví dụ kết nối bằng cURL:
```bash
curl -X GET http://localhost:8000/health
```

#### Phản hồi từ Server (JSON):
```json
{
  "status": "healthy",
  "service": "Text Summarization & Topic Segmentation"
}
```

---

### 2️⃣ `POST /api/v1/meetings/process` — Tóm Tắt Hàng Loạt (Batch API)

- **Phương thức:** `POST`
- **URL:** `http://localhost:8000/api/v1/meetings/process`
- **Header:** `Content-Type: application/json`
- **Chức năng:** Nhận toàn bộ danh sách các câu thoại của cuộc họp và trả về kết quả tóm tắt phân cấp đầy đủ (chủ đề, tiêu đề chương, các đoạn tóm tắt khối).

#### Cấu trúc Request Body JSON:
```json
{
  "meeting_title": "Họp Kế Hoạch Đồ Án Tốt Nghiệp",
  "language": "vi",
  "utterances": [
    {
      "speaker": "Sinh viên A",
      "text": "Thưa thầy, nhóm em xin báo cáo tiến độ mô hình tóm tắt văn bản phân cấp.",
      "index": 0
    },
    {
      "speaker": "Giảng viên",
      "text": "Mô hình của các em đã tối ưu tốc độ xử lý chưa?",
      "index": 1
    },
    {
      "speaker": "Sinh viên B",
      "text": "Dạ nhóm em đã tối ưu chạy mượt mà trên cả GPU và CPU ạ.",
      "index": 2
    }
  ]
}
```

#### Ví dụ cURL:
```bash
curl -X POST http://localhost:8000/api/v1/meetings/process \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_title": "Họp Kế Hoạch Báo Cáo",
    "language": "vi",
    "utterances": [
      {"speaker": "Sinh viên A", "text": "Thưa thầy, nhóm em xin báo cáo tiến độ.", "index": 0},
      {"speaker": "Giảng viên", "text": "Mô hình chạy thế nào?", "index": 1}
    ]
  }'
```

#### Ví dụ Python (`requests`):
```python
import requests

url = "http://localhost:8000/api/v1/meetings/process"
payload = {
    "meeting_title": "Họp Báo Cáo Đồ Án",
    "language": "vi",
    "utterances": [
        {"speaker": "Sinh viên A", "text": "Thưa thầy, nhóm em báo cáo tiến độ.", "index": 0},
        {"speaker": "Giảng viên", "text": "Mô hình đã sẵn sàng chưa?", "index": 1}
    ]
}

response = requests.post(url, json=payload)
print(response.json())
```

---

### 3️⃣ `WebSocket /ws` — Kết Nối Real-Time Two-Way Streaming

- **Giao thức:** `WebSocket`
- **URL:** `ws://localhost:8000/ws`
- **Chức năng:** Nhận từng câu thoại trực tiếp từ client khi cuộc họp đang diễn ra và tự động phát các sự kiện tóm tắt/phân đoạn khi có chủ đề mới được chốt.

#### Gửi tin nhắn từ Client lên Server:

1. **Nạp câu thoại mới:**
```json
{
  "type": "utterance",
  "speaker": "Sinh viên A",
  "text": "Nội dung câu phát biểu mới.",
  "index": 0
}
```

2. **Chốt kết thúc cuộc họp (Flush):**
```json
{
  "type": "flush"
}
```

#### Ví dụ JavaScript trên Trình Duyệt (Browser / React / Vue):
```javascript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => {
  console.log("Đã kết nối WebSocket thành công!");

  // Gửi câu thoại 1
  ws.send(JSON.stringify({
    type: "utterance",
    speaker: "Sinh viên A",
    text: "Thưa thầy, em xin phát biểu ạ.",
    index: 0
  }));

  // Gửi câu thoại 2
  ws.send(JSON.stringify({
    type: "utterance",
    speaker: "Giảng viên",
    text: "Mời em trình bày.",
    index: 1
  }));

  // Kết thúc cuộc họp
  ws.send(JSON.stringify({ type: "flush" }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Sự kiện từ Server:", data);
  // Các loại sự kiện nhận được:
  // - "utterance-accepted"
  // - "chunk-closed" (chứa rolling_summary tóm tắt khối)
  // - "segment-closed"
  // - "title-emitted" (chứa tiêu đề chương từ BARTpho)
  // - "meeting-completed" (chứa kết quả tóm tắt phân cấp hoàn chỉnh)
};
```

---

## 💻 3. Sử Dụng Công Cụ Dòng Lệnh (CLI Runner)

Thực thi xử lý cuộc họp trực tiếp bằng Command Line:

### Xử lý Batch và xuất file kết quả JSON:
```bash
python -m src.runtime.cli process path/to/transcript.json --output path/to/output.json
```

### Phát luồng sự kiện đẹp ra Terminal:
```bash
python -m src.runtime.cli stream path/to/transcript.json --pretty
```
