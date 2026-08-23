# Hierarchical Text Summarization & Topic Segmentation Service

A **FastAPI-powered** meeting summarization service that combines **Multiscale TextTiling** for topic segmentation with two Deep Learning models: **ViT5** (Chunk Summarizer) and **BARTpho** (Topic Titler).

---

## 1. Model Weights Setup

Before running the service or ASR module, you must manually download the pre-trained model weights (safetensors & ONNX binaries) from **Google Drive** and place them into their respective model directories.

> **Important Note:** All model binary weights (`*.safetensors`, `*.onnx`, `*.bin`, `*.pt`) exceed GitHub's 100MB per-file limit and are ignored by `.gitignore`. You must manually copy them into place before server startup.

### Expected Directory Structure

```
.
├── models/
│   ├── vit5-chunk-summarizer-v1/
│   │   ├── config.json
│   │   ├── model.safetensors
│   │   ├── tokenizer.json
│   │   ├── spiece.model
│   │   └── ...
│   └── bartpho-topic-titler-v2/
│       └── checkpoint-230/
│           ├── config.json
│           ├── model.safetensors
│           ├── tokenizer.json
│           ├── sentencepiece.bpe.model
│           └── ...
```

### Required Models & Responsibilities

| Model / Module | Expected Local Path | Task / Purpose | Architecture |
| :--- | :--- | :--- | :--- |
| **ViT5 Chunk Summarizer** | `models/vit5-chunk-summarizer-v1` | Generates rolling block summaries for dialogue chunks. | ViT5 (Vietnamese T5) |
| **BARTpho Topic Titler** | `models/bartpho-topic-titler-v2/checkpoint-230` | Generates chapter and topic titles for segmented topics. | BARTpho (Vietnamese BART) |

> **Note:** The model loaders use `local_files_only=True`. The server requires these weight files to be present locally before starting.

---

## 2. Starting the Server

Activate virtual environment and start Uvicorn (with `--reload` for auto-restart on code changes):

```bash
source .llms-module-venv/bin/activate
uvicorn runtime.api:create_app --factory --reload --host 0.0.0.0 --port 8000
```

Server base URL: **`http://localhost:8003`**

---

## 3. Testing Roadmap & API Endpoints

Follow this step-by-step roadmap to test each feature of the service after server startup.

---

### Step 1: Health Check (`GET /health`)

Verify that the server is active and that both ViT5 and BARTpho models are loaded and ready.

- **Method:** `GET`
- **URL:** `http://localhost:8003/health`

#### cURL Command:
```bash
curl -s http://localhost:8003/health | python -m json.tool
```

#### Expected Response (JSON):
```json
{
    "status": "healthy",
    "service": "Text Summarization & Topic Segmentation",
    "models": {
        "vit5_chunk_summarizer": {
            "path": "models/vit5-chunk-summarizer-v1",
            "exists": true,
            "loaded": true
        },
        "bartpho_topic_titler": {
            "path": "models/bartpho-topic-titler-v2/checkpoint-230",
            "exists": true,
            "loaded": true
        }
    }
}
```

---

### Step 2: Batch Meeting Summarization (`POST /api/v1/meetings/process`)

Send a realistic multi-topic meeting transcript to perform automatic topic segmentation (Multiscale TextTiling), chunk summarization (ViT5), and chapter titling (BARTpho).

- **Method:** `POST`
- **URL:** `http://localhost:8003/api/v1/meetings/process`
- **Header:** `Content-Type: application/json`

#### Detailed Meeting Request Body (JSON):
```json
{
  "meeting_title": "Cuộc Họp Đánh Giá Kế Hoạch Kiến Trúc & Tiến Độ Dự Án",
  "language": "vi",
  "utterances": [
    {
      "speaker": "Quản lý Dự án",
      "text": "Chào mọi người, chúng ta bắt đầu buổi họp tổng kết Sprint 14 và thảo luận kế hoạch kiến trúc hệ thống.",
      "index": 0
    },
    {
      "speaker": "Lập trình viên A",
      "text": "Báo cáo anh, nhóm Frontend đã hoàn thành giao diện hiển thị danh sách cuộc họp và tích hợp xong API kiểm tra sức khỏe hệ thống.",
      "index": 1
    },
    {
      "speaker": "Lập trình viên B",
      "text": "Phía Backend cũng đã đóng gói xong các dịch vụ API xử lý tóm tắt văn bản và sẵn sàng thử nghiệm tích hợp.",
      "index": 2
    },
    {
      "speaker": "Quản lý Dự án",
      "text": "Rất tốt. Cảm ơn hai em, tiến độ Sprint này hoàn toàn đáp ứng kế hoạch ban đầu.",
      "index": 3
    },
    {
      "speaker": "Kỹ sư Kiến trúc",
      "text": "Tiếp theo về phần kiến trúc, chúng ta cần thống nhất giải pháp phân đoạn chủ đề bằng thuật toán Multiscale TextTiling.",
      "index": 4
    },
    {
      "speaker": "Lập trình viên B",
      "text": "Thuật toán này sẽ phân tích độ tương đồng từ vựng theo cửa sổ trượt để xác định chính xác ranh giới giữa các chủ đề.",
      "index": 5
    },
    {
      "speaker": "Kỹ sư Kiến trúc",
      "text": "Sau khi phân đoạn, các khối câu thoại sẽ được đưa qua mô hình ViT5 để tóm tắt cuốn chiếu từng khối 8 câu.",
      "index": 6
    },
    {
      "speaker": "Lập trình viên A",
      "text": "Đồng thời mô hình BARTpho sẽ tiếp nhận các câu tóm tắt khối để đặt tiêu đề chương tự động đúng không ạ?",
      "index": 7
    },
    {
      "speaker": "Kỹ sư Kiến trúc",
      "text": "Đúng rồi em, quy trình phân cấp này giúp kết quả tóm tắt mạch lạc và dễ tra cứu hơn.",
      "index": 8
    },
    {
      "speaker": "Kỹ sư DevOps",
      "text": "Về hạ tầng triển khai, chúng ta sẽ chạy dịch vụ FastAPI trên container Docker và quản lý quy trình CI/CD tự động.",
      "index": 9
    },
    {
      "speaker": "Quản lý Dự án",
      "text": "Hệ thống có đảm bảo khả năng mở rộng khi lượng truy cập tăng cao không em?",
      "index": 10
    },
    {
      "speaker": "Kỹ sư DevOps",
      "text": "Dạ có, chúng ta đã cấu hình NGINX load balancer và hỗ trợ tự động chuyển đổi giữa GPU CUDA và CPU.",
      "index": 11
    },
    {
      "speaker": "Lập trình viên B",
      "text": "Ngoài ra các mô hình AI cũng đã được nạp sẵn vào bộ nhớ đệm cache để tối thiểu hóa độ trễ phản hồi API.",
      "index": 12
    },
    {
      "speaker": "Quản lý Dự án",
      "text": "Tuyệt vời. Kế hoạch tiếp theo trong tuần tới sẽ là kiểm thử tải end-to-end cho cả luồng Batch và WebSocket.",
      "index": 13
    },
    {
      "speaker": "Lập trình viên A",
      "text": "Nhóm em sẽ viết thêm bộ kiểm thử tự động cho giao diện và luồng sự kiện real-time.",
      "index": 14
    },
    {
      "speaker": "Quản lý Dự án",
      "text": "Cảm ơn cả nhóm, nếu không còn thắc mắc nào khác chúng ta kết thúc buổi họp tại đây.",
      "index": 15
    }
  ]
}
```

#### cURL Command:
```bash
curl -s -X POST http://localhost:8003/api/v1/meetings/process \
  -H "Content-Type: application/json" \
  -d @data/sample_transcript.json | python -m json.tool --no-ensure-ascii
```
```

#### Python Test Script (`requests`):
```python
import json
import requests

url = "http://localhost:8003/api/v1/meetings/process"
with open("data/sample_transcript.json", "r", encoding="utf-8") as f:
    payload = json.load(f)

response = requests.post(url, json=payload)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

#### Expected Hierarchical Response Structure (JSON):
```json
{
  "meeting_id": "c9a4b2e1-8f3a-4e2b-91d4-1a2b3c4d5e6f",
  "meeting_title": "Cuộc Họp Đánh Giá Kế Hoạch Kiến Trúc và Tiến Độ Dự Án",
  "segments": [
    {
      "segment_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "title": "Tổng kết Sprint 14 và thảo luận kiến trúc hệ thống",
      "utterances_start": 0,
      "utterances_end": 8,
      "chunks": [
        {
          "chunk_id": "f1e2d3c4-b5a6-9f8e-7d6c-5b4a3f2e1d0c",
          "rolling_summary": "Nhóm hoàn thành giao diện Frontend và dịch vụ Backend, tiến độ Sprint 14 đáp ứng kế hoạch.",
          "utterances": [...]
        },
        {
          "chunk_id": "e2f3a4b5-c6d7-8e9f-0a1b-2c3d4e5f6a7b",
          "rolling_summary": "Thống nhất kiến trúc phân đoạn Multiscale TextTiling kết hợp ViT5 tóm tắt khối và BARTpho sinh tiêu đề.",
          "utterances": [...]
        }
      ]
    },
    {
      "segment_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
      "title": "Hạ tầng triển khai Docker và kế hoạch kiểm thử",
      "utterances_start": 9,
      "utterances_end": 15,
      "chunks": [
        {
          "chunk_id": "d3e4f5a6-b7c8-9d0e-1f2a-3b4c5d6e7f8a",
          "rolling_summary": "Triển khai FastAPI trên Docker với NGINX load balancer, nạp sẵn cache mô hình AI và chuẩn bị kiểm thử tải.",
          "utterances": [...]
        }
      ]
    }
  ],
  "generated_at": "2026-08-19T22:18:00Z",
  "processing_time_ms": 1850
}
```

---

### Step 3: Real-Time WebSocket Streaming (`ws://localhost:8000/ws`)

Stream utterances line-by-line during a live meeting. The server automatically emits real-time events as chunks and topic segments close.

- **Protocol:** `WebSocket`
- **URL:** `ws://localhost:8000/ws`

#### Message Types Sent by Client:

1. **Send Utterance:**
   ```json
   {
     "type": "utterance",
     "speaker": "Quản lý Dự án",
     "text": "Chào mọi người, chúng ta bắt đầu buổi họp tổng kết Sprint 14.",
     "index": 0
   }
   ```

2. **Finish Meeting (Flush):**
   ```json
   {
     "type": "flush"
   }
   ```

#### Received Event Types from Server:
- `utterance-accepted`: Confirms ingestion of an utterance.
- `chunk-closed`: Emitted when a 8-utterance chunk closes (includes ViT5 `rolling_summary`).
- `segment-closed`: Emitted when a topic boundary is detected.
- `title-emitted`: Emitted when BARTpho generates the chapter title.
- `meeting-completed`: Emitted on `flush`, returning the complete `hierarchical_summary`.

#### Python WebSocket Test Script:
```python
import asyncio
import json
import websockets

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as ws:
        with open("data/sample_transcript.json", "r", encoding="utf-8") as f:
            utts = json.load(f)["utterances"]

        # 1. Stream utterances line-by-line
        for u in utts:
            payload = {"type": "utterance", "speaker": u["speaker"], "text": u["text"], "index": u["index"]}
            await ws.send(json.dumps(payload))
            print(f"Sent [{u['index']}]: {u['speaker']}")
            await asyncio.sleep(0.1)

        # 2. Finish session
        await ws.send(json.dumps({"type": "flush"}))

        # 3. Listen for incoming events
        while True:
            try:
                msg = await ws.recv()
                event = json.loads(msg)
                print(f"Received Event: {event['type']}")
            except websockets.exceptions.ConnectionClosed:
                break

asyncio.run(test_websocket())
```

#### JavaScript Example (Browser / React / Vue):
```javascript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => {
  console.log("WebSocket connected!");

  ws.send(JSON.stringify({
    type: "utterance",
    speaker: "Quản lý Dự án",
    text: "Chào mọi người, chúng ta bắt đầu buổi họp tổng kết.",
    index: 0
  }));

  ws.send(JSON.stringify({ type: "flush" }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Server Event:", data);
};
```

---

### Step 4: CLI Runner Testing

Run batch processing or stream visualization directly from the project root using the Python CLI module and your activated virtual environment:

#### Process batch JSON transcript and save output:
```bash
PYTHONPATH=. python -m runtime.cli process data/sample_transcript.json --output data/output_summary.json
```

#### Stream summary events pretty-printed directly in terminal:
```bash
PYTHONPATH=. python -m runtime.cli stream data/sample_transcript.json --pretty
```
