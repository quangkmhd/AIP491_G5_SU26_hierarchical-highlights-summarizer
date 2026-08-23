# Hệ thống Speaker Diarization Microservice (sd-module)

Dịch vụ **Speaker Diarization Microservice (`sd-module`)** chịu trách nhiệm phân tách giọng nói đa người nói (Multiple Speaker Diarization), lọc nhiễu, phát hiện nói chồng chéo (Overlapped Speech Detection), bóc tách giọng nói (Speaker Beam TSE / Conv-TasNet BSS) và định danh người nói trong cuộc họp theo thời gian thực.

---

## 1. Cấu trúc Thư mục (Clean Architecture)

```text
sd-module/
├── config/                      # Cấu hình hệ thống & Dependency Injection
│   ├── di_container.py          # Bộ DI Container tự động khởi tạo 6 mô hình AI
│   ├── paths.py                 # Xử lý đường dẫn tương đối/tuyệt đối
│   └── settings.yaml            # Cấu hình mô hình, thresholds và thuật toán
├── core/                        # Adapters bọc 6 mô hình AI lõi
│   ├── bss.py                   # Adapter Conv-TasNet (Blind Source Separation)
│   ├── buffer.py                # Smart Audio Buffer phân mảnh âm thanh động
│   ├── denoiser.py              # Adapter DeepFilterNet3 (Lọc nhiễu âm thanh)
│   ├── embedder.py              # Adapter CAM++ (Trích xuất vân tay giọng nói 512-dim)
│   ├── ovd.py                   # Adapter Pyannote OVD (Phát hiện nói chồng chéo)
│   ├── tse.py                   # Adapter SpeakerBeam-SS (Target Speech Extraction)
│   └── vad.py                   # Adapter Silero VAD (Phát hiện giọng nói)
├── data/                        # Thư mục lưu dữ liệu mẫu âm thanh & báo cáo
├── pipeline/                    # Use Cases lõi nghiệp vụ
│   ├── audio_preprocessing.py   # Module 1: Lọc nhiễu, VAD & Quality Gate
│   └── speaker_diarization.py   # Module 2: Định danh, phát hiện Overlap & Rẽ 4 nhánh
├── state/                       # Quản lý Trạng thái 
│   └── voiceprint_pool.py       # Quản lý hồ sơ người nói (Voiceprint) & cập nhật EMA
├── utils/                       # Drivers & Tiện ích bên ngoài
│   └── speakerbeam/             # Mã nguồn mô hình SpeakerBeam-SS tích hợp
├── weights/                     # Trọng số Mô hình AI
│   ├── campplus/                # Trọng số CAM++ (ModelScope)
│   ├── dfn/                     # Trọng số DeepFilterNet3 (model_120.ckpt.best)
│   ├── torch_hub/               # Trọng số Conv-TasNet (torchaudio)
│   ├── ovd.bin                  # Trọng số Pyannote OVD
│   ├── resemblyzer.pt           # Trọng số Resemblyzer VoiceEncoder
│   ├── speakerbeam.pth          # Trọng số SpeakerBeam-SS
│   └── silero_vad.onnx          # Trọng số Silero VAD ONNX
├── api.py                       # REST API Microservice (FastAPI - Port 8002)
├── main.py                      # Terminal CLI Offline Batch Execution
├── run_detailed_diarization.py  # Công cụ kiểm tra & xuất báo cáo chi tiết terminal/JSON
├── test_sd_cases.py             # Kịch bản kiểm thử tự động (Automation Test Suite)
├── sd-module-requirements.txt   # Danh sách thư viện Python
├── Dockerfile                   # Kịch bản triển khai Docker Container
└── README.md                    # Tài liệu hướng dẫn sử dụng & API Spec
```

---

## 2. Hướng dẫn Khởi chạy dịch vụ

### Cách A: Khởi chạy HTTP REST API Server (Port 8002)

1. **Cài đặt môi trường:**
   ```bash
   python -m venv .sd-module-venv
   source .sd-module-venv/bin/activate
   pip install -r sd-module-requirements.txt
   ```

2. **Khởi chạy FastAPI Uvicorn Server:**
   ```bash
   PYTHONPATH=. uvicorn api:create_app --factory --host 0.0.0.0 --port 8002 --reload
   ```

3. **Kiểm tra Health Check:**
   ```bash
   curl http://localhost:8002/healthz
   ```
   *Response:* `{"status": "ready", "service": "Speaker Diarization Microservice"}`

---

## 3. REST API Specification

### A. Phân tách và Định danh Âm thanh (`POST /api/v1/diarize`)

Tải lên file âm thanh (.wav, .mp3, .flac), hệ thống sẽ lọc nhiễu, phân đoạn, rẽ nhánh bóc tách overlap và trả về danh sách các segment kèm stream âm thanh Base64 và mốc thời gian chi tiết của từng người nói (`speaker_timestamps`).

```bash
curl -X POST "http://localhost:8002/api/v1/diarize" \
  -F "file=@data/overlap-audio-sample.wav"
```

#### JSON Response Schema:
```json
{
  "status": "success",
  "duration_seconds": 180.0,
  "processing_time_seconds": 44.76,
  "processing_time_ms": 44763.0,
  "sample_rate": 16000,
  "total_segments": 49,
  "segments": [
    {
      "chunk_index": 0,
      "start_time": 0.0,
      "end_time": 1.5,
      "branch": "BRANCH_A",
      "speakers": ["SPK_001"],
      "speaker_timestamps": [
        {
          "speaker": "SPK_001",
          "start_time": 0.0,
          "end_time": 1.5,
          "speech_duration_sec": 1.5
        }
      ],
      "has_overlap": false,
      "audio_streams_b64": [
        "UklGRiYAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA..."
      ]
    },
    {
      "chunk_index": 16,
      "start_time": 54.0,
      "end_time": 64.0,
      "branch": "BRANCH_B_TSE",
      "speakers": ["SPK_001", "SPK_002"],
      "speaker_timestamps": [
        {
          "speaker": "SPK_001",
          "start_time": 54.0,
          "end_time": 64.0,
          "speech_duration_sec": 10.0
        },
        {
          "speaker": "SPK_002",
          "start_time": 54.0,
          "end_time": 61.5,
          "speech_duration_sec": 7.5
        }
      ],
      "has_overlap": true,
      "audio_streams_b64": [
        "<base64_stream_SPK_001>",
        "<base64_stream_SPK_002>"
      ]
    }
  ]
}
```

---

### B. Reset Trạng thái Cuộc họp (`POST /api/v1/reset`)

Reset danh sách hồ sơ giọng nói (`VoiceprintPool`) và bộ đệm VAD giữa các phiên họp mới.

```bash
curl -X POST "http://localhost:8002/api/v1/reset"
```

---

## 4. Công cụ Kiểm tra Chi tiết Terminal & Xuất Báo cáo JSON

Hệ thống đi kèm công cụ [run_detailed_diarization.py](file:///Users/anhnn/Documents/study/fpt-uni/sem-09/capstone/code/AIP491_G5_SU26_hierarchical-highlights-summarizer/backend/sd-module/run_detailed_diarization.py) giúp hiển thị bảng tổng hợp mốc thời gian từng speaker ngay trên màn hình terminal và xuất file báo cáo JSON chi tiết.

### Cú pháp:
```bash
python run_detailed_diarization.py --audio data/overlap-audio-sample.wav --report data/detailed_diarization_report.json
```

#### Terminal Output Preview:
```text
==========================================================================
                    SPEAKER DIARIZATION SUMMARY REPORT                    
==========================================================================
Status:                 success
Audio Duration:         180.0 seconds (3.0 minutes)
Total Processing Time:  44.76 seconds
Total Speech Segments:  49

-------------------------------------------------------------------------------------
Start (s)  End (s)    Branch           Speakers             Overlap?    
-------------------------------------------------------------------------------------
0.0        1.5        BRANCH_A         SPK_001              No
    └── SPK_001         : 0.0s -> 1.5s (duration: 1.5s)
54.0       64.0       BRANCH_B_TSE     SPK_001, SPK_002     YES ⚡
    └── SPK_001         : 54.0s -> 64.0s (duration: 10.0s)
    └── SPK_002         : 54.0s -> 61.5s (duration: 7.5s)
135.5      145.5      FALLBACK         unresolved_overlap   YES ⚡
    └── unresolved_overlap: 135.5s -> 145.5s (duration: 10.0s)
```

---

## 5. Kiến trúc 4 Nhánh Rẽ (Decision Branches)

| Nhánh Rẽ | Điều kiện kích hoạt | Mô hình & Hành vi |
| :--- | :--- | :--- |
| **`BRANCH_A`** | Một người nói duy nhất | **CAM++ Embedder**: Nhận diện & cập nhật hồ sơ giọng nói EMA trong `VoiceprintPool`. |
| **`BRANCH_B_TSE`** | Phát hiện nói chồng chéo + Đã có gợi ý người nói | **SpeakerBeam-SS**: Dùng d-vector trong pool bóc tách chính xác giọng từng người. |
| **`BRANCH_C_BSS`** | Phát hiện nói chồng chéo + Cold start | **Conv-TasNet**: Phân tách mù 1 kênh âm thanh thành 2 luồng độc lập. |
| **`FALLBACK`** | Mô hình bóc tách thất bại (Nhiễu/mất tiếng) | Giữ nguyên đoạn âm thanh hỗn hợp gốc và gán nhãn **`unresolved_overlap`**. |

---

## 6. Tham khảo Biến cấu hình (`config/settings.yaml`)

| Tham số | Giá trị mặc định | Ý nghĩa |
|---|---|---|
| `audio.sample_rate` | 16000 | Tần số lấy mẫu chung (16kHz Mono). |
| `smart_buffer.chunk_size_ms` | 500 | Độ dài mỗi frame stream âm thanh đầu vào (ms). |
| `branch_a...matching_threshold`| 0.65 | Ngưỡng Cosine Similarity để định danh người nói. |
| `branch_b_tse.theta_low` | 0.45 | Ngưỡng gợi ý người nói để chuyển vào nhánh SpeakerBeam TSE. |
| `voiceprint_pool.base_alpha` | 0.1 | Hệ số học EMA cập nhật vân tay giọng nói (10%). |
