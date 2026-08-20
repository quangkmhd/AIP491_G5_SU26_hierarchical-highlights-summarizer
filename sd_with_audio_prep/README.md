# Hệ thống Target Diarization Pipeline (Phân Cụm Người Nói)

## 1. Cấu trúc Thư mục (Clean Architecture Directory Structure)

```text
target_diarization/
├── config/                  # Các file cấu hình hệ thống & Môi trường
│   ├── di_container.py      # Bộ Dependency Injection khởi tạo tự động
│   ├── paths.py             # Xử lý đường dẫn tuyệt đối/tương đối
│   └── settings.yaml        # File cấu hình chính (Tham số mô hình, Thresholds)
├── core/                    # Lõi nghiệp vụ & Adapter bọc các mô hình AI
│   ├── bss.py               # Adapter bóc tách mù (Blind Source Separation)
│   ├── buffer.py            # Smart Audio Buffer phân mảnh âm thanh động
│   ├── denoiser.py          # Adapter lọc nhiễu âm thanh
│   ├── embedder.py          # Adapter trích xuất vân tay giọng nói (CAM++)
│   ├── ovd.py               # Adapter phát hiện chồng chéo (Pyannote OVD)
│   ├── tse.py               # Adapter bóc tách đích (Target Speech Extraction)
│   └── vad.py               # Adapter phát hiện giọng nói (Silero VAD)
├── pipeline/                # Logic luồng ứng dụng chính (Application Use Cases)
│   ├── audio_preprocessing.py # Module 1: Tiền xử lý, lọc nhiễu và gom chunk
│   └── speaker_diarization.py # Module 2: Định danh, phát hiện Overlap và Rẽ nhánh
├── state/                   # Quản lý Trạng thái 
│   └── voiceprint_pool.py   # Quản lý hồ sơ người nói (Voiceprint) và cập nhật EMA
├── utils/                   # Drivers bên ngoài & Tiện ích
│   └── speakerbeam/         # Mã nguồn mô hình SpeakerBeam-SS tích hợp sâu
├── weights/                 # Trọng số Mô hình (Tải thủ công từ Google Drive)
│   ├── campplus/            # Trọng số mô hình CAM++
│   ├── dfn/                 # Trọng số mô hình DeepFilterNet3
│   ├── torch_hub/           # Trọng số Conv-TasNet (torchaudio)
│   ├── ovd.bin              # Trọng số mô hình OVD
│   ├── resemblyzer.pt       # Trọng số Resemblyzer
│   ├── speakerbeam.pth      # Trọng số SpeakerBeam
│   └── silero_vad.onnx      # Trọng số Silero VAD
├── main.py                  # Entry Point chạy toàn bộ Pipeline qua Terminal
├── requirements.txt         # Danh sách thư viện Python chạy độc lập
├── Dockerfile               # Kịch bản triển khai Docker Production
├── .dockerignore            # Cấu hình bỏ qua file cho Docker
└── README.md                # Tài liệu hướng dẫn sử dụng và triển khai
```

## 2. Tính di động: Di chuyển sang máy chủ khác (Portability)
Để triển khai module này trên một máy tính khác hoặc nhúng vào một Repo lớn hơn:

1. **Nén thư mục:**
   ```bash
   tar -czvf target_diarization.tar.gz target_diarization/
   ```
2. **Chuyển file:** Copy file `target_diarization.tar.gz` sang máy đích thông qua SCP, USB, hoặc Cloud.
3. **Giải nén trên máy đích:**
   ```bash
   tar -xzvf target_diarization.tar.gz
   cd target_diarization
   ```
4. **Tải file Model:** Đảm bảo bạn đã tải bộ trọng số cực nặng từ link Google Drive và giải nén chính xác vào bên trong thư mục `weights/` như cấu trúc ở trên.

Hệ thống hoạt động 100% Offline, không yêu cầu kết nối mạng để tải thêm bất kỳ model nào lúc Runtime!

## 3. Hướng dẫn Khởi chạy (How to Run)

### Cách A: Khởi chạy bằng Docker (Khuyên dùng)
Yêu cầu máy tính đã cài đặt Docker.

1. Build Image:
   ```bash
   docker build -t target-diarization .
   ```
2. Khởi chạy Container (Đảm bảo mount thư mục `weights` từ máy thật vào để Container có thể đọc model):
   ```bash
   docker run -v /path/to/local/weights:/app/weights target-diarization
   ```

### Cách B: Khởi chạy bằng Python thuần (Standalone)
Yêu cầu Python 3.12+.

1. Khởi tạo môi trường ảo và cài đặt thư viện:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Trên Windows dùng lệnh: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Đảm bảo thư mục `weights/` đã có đủ dữ liệu.

## 4. Hướng dẫn Sử dụng (CLI & Output)
Hệ thống cung cấp sẵn file `main.py` đóng vai trò là Entry Point trọn vẹn để chạy Pipeline từ đầu đến cuối đối với một file âm thanh bất kỳ.

### Cú pháp lệnh:
```bash
python main.py --audio /path/to/your/audio.wav --output results.json
```

**Các tham số:**
- `--audio`: Đường dẫn đến file âm thanh cần phân tích (Hỗ trợ .wav, .mp3, .flac... hệ thống tự động resample về 16kHz Mono).
- `--output`: Đường dẫn lưu file kết quả (Mặc định: `diarization_output.json`).

### Định dạng Kết quả (JSON Output):
Kết quả được xuất ra dưới dạng JSON cấu trúc, dễ dàng để gửi ngược lại cho Frontend hoặc đẩy sang hệ thống STT:

```json
{
  "audio_file": "/path/to/your/audio.wav",
  "duration_seconds": 12.5,
  "sample_rate": 16000,
  "total_segments_processed": 3,
  "status": "success",
  "segments": [
    {
      "start_time": 0.0,
      "end_time": 4.5,
      "branch": "BRANCH_A",
      "speakers": ["Speaker_01"],
      "has_overlap": false
    },
    {
      "start_time": 4.5,
      "end_time": 8.0,
      "branch": "BRANCH_B",
      "speakers": ["Speaker_01", "Speaker_02"],
      "has_overlap": true
    }
  ]
}
```

## 5. Tham khảo Biến cấu hình (Configuration Reference)
Bạn có thể tùy chỉnh hành vi của toàn bộ hệ thống thông qua file `config/settings.yaml`:

| Tham số | Giá trị mặc định | Ý nghĩa |
|---|---|---|
| `audio.sample_rate` | 16000 | Tần số lấy mẫu chung của hệ thống (Hz). Mặc định là 16kHz. |
| `smart_buffer.chunk_size_ms` | 500 | Kích thước mỗi chunk luồng âm thanh đầu vào (ms). |
| `smart_buffer.vad_threshold` | 0.5 | Độ tin cậy tối thiểu của VAD để xác nhận là có tiếng người. |
| `branch_a...matching_threshold`| 0.65 | Ngưỡng Cosine Similarity để đối chiếu và nhận diện chính xác 1 người. |
| `voiceprint_pool.base_alpha` | 0.1 | Tốc độ học (Hệ số EMA) để cập nhật vân tay giọng nói (10%). |
