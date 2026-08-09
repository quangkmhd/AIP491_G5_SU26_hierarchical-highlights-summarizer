# Custom 10h Topic Summary Evaluation Design

## 1. Mục tiêu và phạm vi

Xây dựng một bộ đánh giá có thể chạy lại và tiếp tục từ lần chạy trước cho dữ liệu `training-eval-suite/data/Custom_10h`. Mỗi tệp WAV được xem là một lượt lời. Hệ thống chạy chuỗi xử lý từ ASR, nhận diện người nói, phân đoạn chủ đề, tóm tắt khối đến sinh tiêu đề, nhưng chỉ chấm chất lượng đầu ra tóm tắt ở cấp chủ đề bằng AI judge.

Đơn vị đánh giá là một topic hoàn chỉnh. Mỗi topic gồm toàn bộ transcript ASR thuộc topic, topic title và các chunk summary kèm transcript nguồn của từng chunk. Bộ đánh giá không tính WER, chỉ số ranh giới chủ đề hoặc điểm riêng cho ASR.

## 2. Nguồn dữ liệu và thứ tự lượt lời

Nguồn dữ liệu gồm `recordings.jsonl`, `supervisions.jsonl` và thư mục `wavs/`. Tên bản ghi có dạng `<source_id>_<utterance_index>`. Bộ nạp dữ liệu tách tên bằng `rsplit("_", 1)`, nhóm theo `source_id` và sắp xếp tăng dần theo `utterance_index`. Cách tách này vẫn đúng khi `source_id` chứa dấu gạch dưới.

Mỗi WAV tạo đúng một utterance. Không chạy VAD để chia nhỏ WAV lần nữa. Mỗi utterance được đưa độc lập qua CAM++ để trích speaker embedding; các embedding trong cùng một `source_id` sau đó được phân cụm và ánh xạ ổn định thành `Speaker 01`, `Speaker 02`, … theo thứ tự lần xuất hiện đầu tiên. Các bản ghi thiếu WAV, trùng chỉ số, sai tần số lấy mẫu hoặc không giải mã được được ghi vào `failures.jsonl`; lỗi của một tệp không làm mất kết quả đã hoàn thành trước đó.

## 3. Chuỗi xử lý

1. ASR dùng thư viện `sherpa-onnx` với checkpoint cục bộ `models/Zipformer-SSL-100h`, cấu hình streaming chunk 32, left context 128, greedy search và âm thanh PCM 16 kHz.
2. Nhận diện người nói dùng toolkit 3D-Speaker và checkpoint CAM++ `iic/speech_campplus_sv_zh-cn_16k-common`. CAM++ trích một embedding 192 chiều cho mỗi WAV 16 kHz; `CommonClustering` với spectral clustering tự ước lượng số người nói trong từng `source_id`.
3. Nhãn cụm được chuẩn hóa thành `Speaker 01`, `Speaker 02`, … theo lần xuất hiện đầu tiên để cùng một run luôn tạo cùng nhãn. Với nhóm không đủ điều kiện phân cụm, toàn bộ utterance được gán `Speaker 01` và lý do fallback được lưu trong artifact.
4. Các transcript có nhãn người nói được sắp theo thứ tự utterance trong từng `source_id` và đưa vào Multi-Scale Sliding TextTiling hiện có.
5. Mỗi topic được chia tuần tự thành các chunk tối đa tám utterance.
6. ViT5 tạo một summary cho mỗi chunk.
7. BARTpho tạo topic title từ danh sách chunk summary theo thứ tự thời gian, giữ quy tắc lấy tối đa 1.500 ký tự cuối như pipeline hiện tại.
8. AI judge nhận toàn bộ gói topic và trả về kết quả có cấu trúc.

Các stage ASR, CAM++ speaker labeling, pipeline sinh recap và AI judge phải có thể chạy độc lập, resume và tái sử dụng artifact từ stage trước. Checkpoint CAM++ được tải một lần vào cache của ModelScope/3D-Speaker; runner không tải lại model theo từng WAV.

## 4. Bảo đảm tương đương đầu vào huấn luyện

Đầu vào ViT5 phải khớp với `training-eval-suite/src/train/chunk_summarizer/data_utils.py`:

- Mỗi chunk có từ một đến tám utterance.
- Mỗi dòng có dạng chính xác `speaker: text`; không thêm dấu gạch đầu dòng.
- Prompt đầy đủ bắt đầu bằng `Tóm tắt: `.
- Tokenizer được nạp bằng cơ chế ViT5 hiện có và giữ `extra_ids=96` khi áp dụng.
- Đầu vào giới hạn 512 token.
- Sinh văn bản bằng beam search 4, tối đa 128 token, `no_repeat_ngram_size=3`, `length_penalty=1.0`, `early_stopping=True` và `do_sample=False`.

Runtime hiện định dạng `- speaker: text`, khác dữ liệu huấn luyện. Thay đổi triển khai phải thống nhất runtime về `speaker: text` và bổ sung regression test cho định dạng này.

Trước khi sinh summary, bộ đánh giá tạo `input_compatibility.json` chứa số chunk, phân phối số utterance, ký tự và token, tỷ lệ vượt 512 token, tỷ lệ transcript rỗng, phân phối số speaker trong mỗi nguồn, cùng thống kê tương ứng từ tập train/dev AliMeeting nếu có. Một chunk vượt giới hạn vẫn được xử lý theo cơ chế truncation của mô hình nhưng phải được đánh dấu `was_truncated=true`. Báo cáo phải nêu tỷ lệ utterance dùng speaker fallback và tỷ lệ topic chỉ có một speaker để làm rõ độ lệch dữ liệu còn lại.

## 5. AI judge và rubric

AI judge đọc `DEEPSEEK_API_KEY` và `LLM_MODEL` từ file `.env` ở project root. Khóa API không được ghi vào command line, log, cache, manifest hoặc báo cáo. Mỗi topic dùng một yêu cầu đánh giá với temperature bằng 0 và yêu cầu JSON có cấu trúc.

Đầu vào judge gồm:

- `source_id`, topic index và phạm vi utterance;
- transcript đầy đủ của topic, đánh số ổn định;
- topic title;
- từng chunk với phạm vi utterance, transcript nguồn và predicted summary;
- rubric, hướng dẫn chỉ dựa trên transcript và schema đầu ra.

Rubric tổng 100 điểm:

### 5.1. Chunk summaries: 60 điểm

Điểm từng chunk nằm trên thang 0–5 và được tổng hợp có trọng số theo số utterance:

- Faithfulness: 30 điểm. Summary chỉ chứa thông tin được transcript hỗ trợ.
- Key-point coverage: 20 điểm. Summary giữ được các ý quan trọng của chunk.
- Conciseness and coherence: 10 điểm. Summary rõ ràng, ngắn gọn và không lặp không cần thiết.

### 5.2. Topic title: 15 điểm

- Topic representativeness: 7 điểm.
- Specificity and clarity: 5 điểm.
- Factual faithfulness: 3 điểm.

### 5.3. Whole-topic quality: 25 điểm

- Overall coverage across summaries: 10 điểm.
- Cross-chunk consistency: 8 điểm.
- Non-redundancy and recap usefulness: 7 điểm.

Judge trả điểm riêng cho title, từng chunk và toàn topic; đồng thời trả `total_score`, nhận xét ngắn, cùng các cờ `hallucination`, `contradiction`, `major_omission` và `redundancy`. Mỗi cờ dương phải kèm mô tả và danh sách utterance ID làm bằng chứng. Code tính lại `total_score` từ các điểm thành phần và không tin trực tiếp tổng điểm do model trả về.

Phản hồi sai JSON/schema được retry tối đa hai lần với thông báo lỗi schema. Sau lần thứ ba, topic được ghi vào `failures.jsonl` và không được giả lập điểm mặc định.

## 6. Lưu trữ, cache và khả năng tái sử dụng

Kết quả đặt tại `training-eval-suite/eval_results/custom_10h_summary`:

```text
custom_10h_summary/
├── cache/
│   ├── asr/
│   ├── speaker_embeddings/
│   ├── speaker_labels/
│   ├── pipeline/
│   └── ai_judgments/
└── runs/<run_id>/
    ├── manifest.json
    ├── input_compatibility.json
    ├── asr_transcripts.jsonl
    ├── speaker_labels.jsonl
    ├── topic_outputs.jsonl
    ├── ai_judgments.jsonl
    ├── failures.jsonl
    ├── aggregate.json
    └── report.md
```

ASR cache key gồm SHA-256 của WAV, ASR model files, phiên bản `sherpa-onnx` và decode config. Speaker-embedding cache key gồm SHA-256 của WAV, CAM++ model ID/revision và phiên bản 3D-Speaker; speaker-label cache key gồm danh sách embedding hash và clustering config. Pipeline cache key gồm transcript kèm speaker label, segmentation config, ViT5 checkpoint/config và BARTpho checkpoint/config. Judge cache key gồm topic payload, rubric version, judge model và generation config. Cache chỉ chứa dữ liệu và kết quả, không chứa secret.

Ghi JSONL theo kiểu append an toàn sau mỗi item hoàn thành. Khi resume, runner bỏ qua item có cache hợp lệ và tiếp tục item chưa hoàn thành. CLI hỗ trợ ít nhất `--run-id`, `--resume`, `--limit`, `--source-id`, `--device`, `--skip-asr`, `--skip-speaker`, `--campp-model-id` và `--force-stage` để chạy smoke test hoặc tái chấm có kiểm soát. `--skip-speaker` chỉ hợp lệ khi một artifact speaker-label tương thích đã tồn tại; không âm thầm thay bằng `unknown`.

`manifest.json` lưu timestamp, Git commit, đường dẫn và hash checkpoint, cấu hình từng stage, rubric version, judge model, số lượng item và trạng thái run. `aggregate.json` lưu trung bình, trung vị, độ lệch chuẩn và các phân vị điểm; tỷ lệ từng cờ lỗi; phân phối theo độ dài topic và số chunk. `report.md` trình bày cấu hình, kiểm tra input compatibility, kết quả tổng hợp, các topic tốt/xấu tiêu biểu và danh sách thất bại.

## 7. Cấu trúc mã nguồn

Tạo package chuyên biệt trong `training-eval-suite/src/evaluate/custom_10h_summary/` với các module tách biệt cho manifest loading, ASR qua `sherpa-onnx`, CAM++ embedding và clustering qua 3D-Speaker, pipeline recap, input compatibility, AI judge, cache, aggregation và CLI. Tạo wrapper `training-eval-suite/scripts/eval_custom_10h_summary.sh`. Logic dùng lại service/model hiện có thay vì sao chép thuật toán segmentation hoặc inference.

Các interface lõi phải cho phép dependency injection để unit test không cần GPU hoặc API thật. Chỉ smoke/integration test được đánh dấu mới được tải checkpoint thật hoặc gọi dịch vụ ngoài.

## 8. Kiểm thử và điều kiện hoàn thành

Unit test bao phủ:

- nhóm `source_id` và sắp xếp hậu tố số;
- ánh xạ một WAV thành một utterance;
- ánh xạ CAM++ cluster thành speaker label ổn định theo lần xuất hiện đầu tiên;
- fallback có ghi lý do khi một nhóm không đủ điều kiện clustering;
- định dạng ViT5 giống byte-for-byte với dữ liệu train;
- chia chunk tối đa tám utterance;
- phát hiện truncation và tạo thống kê compatibility;
- tạo cache key ổn định và cache invalidation khi model/rubric đổi;
- validation JSON judge, retry và tính lại tổng điểm;
- resume không chạy lại item đã hoàn thành;
- aggregation và tạo báo cáo từ fixture nhỏ.

Smoke test dùng một `source_id` hoặc `--limit` nhỏ để xác nhận luồng `sherpa-onnx` ASR → CAM++ speaker labeling → segmentation → ViT5 → BARTpho → judge. Full run chỉ bắt đầu khi smoke test sinh đủ artifact, không lộ secret và không có lỗi định dạng đầu vào.

Tính năng hoàn thành khi runner có thể xử lý lại một run bị ngắt mà không mất kết quả, mỗi topic có transcript/title/chunk summaries/judgment truy vết được, và báo cáo tổng hợp được tái tạo hoàn toàn từ các JSONL đã lưu mà không gọi lại model hoặc API.
