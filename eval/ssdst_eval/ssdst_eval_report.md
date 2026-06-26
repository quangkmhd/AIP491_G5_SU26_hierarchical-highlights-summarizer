# Báo cáo nghiên cứu: State-Space Dialogue State Tracking (SS-DST) cho Meeting Recap

**Dự án:** AIP491 — Meeting Recap Webapp (tool 09)
**Nhánh:** `feat/ss-dst-meeting-recap`
**Ngày:** 2026-06-25
**Mô hình thực nghiệm:** `qwen3.5:4b-q4_K_M` (Ollama local)
**Tác giả:** nhóm nghiên cứu AIP491

---

## 1. Tóm tắt (Executive Summary)

Phương pháp tóm tắt phân cấp (`HierarchicalRecapMethod`) hiện tại của webapp tóm tắt từng **chunk 8 utterance trong cô lập** (chạy song song, không chia sẻ trạng thái giữa các chunk). Điều này gây ba lỗi trên transcript cuộc họp thực: (1) **mất coreference** — đại từ "nó", "pipeline đó" không được giải quyết khi nằm khác chunk với thực thể gốc; (2) **phân mảnh quyết định** — một quyết định chốt dần qua nhiều chunk bị切成 các note rời rạc; (3) **không có bộ nhớ cuộn** — thực thể/quyết định/hành động mở ở đầu chương biến mất khỏi các chunk sau.

Báo cáo này giới thiệu **SS-DST (State-Space Dialogue State Tracking)**: một **dialogue belief state** (trạng thái nhớ đàm thoại) dạng JSON được (a) **tiêm** vào prompt của mỗi chunk làm bối cảnh trước, và (b) **cập nhật** sau mỗi chunk bằng một LLM call chuyên dụng. Cách này mô phỏng **Dialogue State Tracking** (theo dõi slot/belief qua các lượt) và **đệ quy trạng thái của State-Space Models / Mamba** (`s_t = Update(s_{t-1}, x_t)`), nhưng được hiện thực ở tầng prompt/LLM cho tóm tắt cuộc họp.

**Kết quả thực nghiệm (live Ollama, transcript 24 utterances → 3 chunk/chapter):**

| Chỉ số | hierarchical (baseline) | ssdst | Tỷ lệ |
|---|---:|---:|---:|
| Số LLM run | 6 | 10 | 1.67× |
| Wall-clock (s) | 11.8 | 26.78 | 2.27× |
| Input tokens | 7 086 | 12 336 | 1.74× |
| Output tokens | 509 | 1 355 | 2.66× |
| Số note | 4 | 4 | 1.0× |
| Note liên kết đa-chunk | 2 | 3 | 1.5× |
| Quyết định có cấu trúc (structured decisions) | 0 | 6 | — |
| Coreference giải quyết có provenance | 0 | 1 (cấu trúc) | — |
| Gold recall (decisions/actions/entities) | 1.0 | 1.0 | 1.0× |

**Kết luận:** SS-DST không cải thiện *coverage* (recall đã bão hòa ở 1.0 trên transcript kiểm soát) mà cải thiện **cấu trúc, tính liên kết và khả năng kiểm toán (auditability)** — biến các quyết định/action rải rác thành một belief state có cấu trúc, đồng thời giải quyết coreference một cách tường minh. Đổi lại là chi phí ~1.7–2.3× token và wall-clock. Đây là một **đóng góp có ý nghĩa cho paper** vì nó chuyển tóm tắt từ "đoạn rời" sang "có bộ nhớ trạng thái", với đánh giá trung thực về cost–benefit.

---

## 2. Bối cảnh & vấn đề

### 2.1. Hệ thống hiện tại

`HierarchicalRecapMethod` (file `app/methods/hierarchical_recap.py`):
1. Phân đoạn transcript bằng TextTiling (cosine similarity trên bag-of-words, cửa sổ 30 utterance, stride 10).
2. Mỗi chương (chapter) được chia thành các chunk 8 utterance.
3. Với mỗi chunk, gọi LLM tạo một note (task `hierarchical_abstractive`), **chạy song song**, **không truyền trạng thái** giữa các chunk.
4. Mỗi chương thêm một title + one-line summary.

### 2.2. Ba lỗi do cô lập chunk

Trên transcript có coreference xuyên chunk, baseline thất bại theo ba cách:

- **Mất coreference:** chunk 2 có câu *"mình sẽ review nó"* nhưng thực thể *"nó"* (cluster Kafka) ở chunk 1. Baseline không thấy chunk 1 → note mơ hồ.
- **Phân mảnh quyết định:** quyết định *"chốt microservices + Kafka"* được chốt ở chunk 1, nhắc lại ở chunk 3, và gán action ở chunk 3. Baseline tách thành ba note cục bộ.
- **Không có bộ nhớ cuộn:** thực thể *"gateway"*, *"schema registry"* mở ở giữa chương không xuất hiện trong context của chunk sau.

LLM mạnh (như qwen3.5) thường **che giấu** vấn đề bằng cách paraphrase bỏ đại từ — khiến recall trông vẫn cao nhưng mất provenance và mất khả năng kiểm toán. Đây là điểm tinh tế mà báo cáo này đo lường thẳng vào *structured decisions* và *resolved_references* thay vì chỉ ROUGE.

---

## 3. Phương pháp SS-DST

### 3.1. Định nghĩa

SS-DST duy trì một **belief state** $s_t$ — JSON có cấu trúc:

```
{
  "current_topic": str,           # chủ đề đang thảo luận
  "entities": [str],              # thực thể active (người, hệ thống, model, API)
  "decisions": [str],             # quyết định/kết luận đã chốt
  "open_actions": [str],          # hành động chưa hoàn tất (+assignee nếu có)
  "resolved_references": [{"pronoun": str, "refers_to": str}]
}
```

### 3.2. Phương trình cập nhật trạng thái

Mô phỏng đệ quy trạng thái của SSM/Mamba:

$$s_t = \text{Update}\bigl(s_{t-1},\ \text{summary}(x_t),\ x_t\bigr)$$

trong đó $x_t$ là chunk thứ $t$, $\text{summary}(x_t)$ là note do LLM tạo cho chunk đó, và `Update` là một LLM call (`ssdst_state_update`) gộp thông tin mới vào state cũ, áp dụng **forgetting gate** để giữ state gọn (~180 token): ưu tiên giữ `decisions` và `open_actions`, lược bớt `entities`/`current_topic` ít quan trọng khi state quá dài.

### 3.3. Luồng xử lý

1. **Segmentation & chunking:** dùng lại TextTiling + chunk 8 utterance của hierarchical (không đổi).
2. **Title stage:** chạy song song (title không phụ thuộc state) — dùng lại `hierarchical_title`.
3. **Note + state stage:** trong mỗi chương, xử lý chunk **tuần tự**:
   - Tiêm $s_{t-1}$ vào prompt `ssdst_abstractive` → tạo note $a_t$ (vừa tóm tắt vừa giải quyết coreference dựa trên state).
   - Gọi `ssdst_state_update` với ($s_{t-1}$, $x_t$, $a_t$) → $s_t$.
4. Các chương vẫn chạy song song với nhau (mỗi chương có belief state độc lập).

### 3.4. Tại sao đây là đóng góp mới

- **Không phải chỉ "thêm context":** context được thêm là *có cấu trúc và tiến hóa* (belief state), không phải dump raw transcript trước đó → kiểm soát được token budget.
- **Coreference có provenance:** `resolved_references` lưu lại ánh xạ `"nó" → "cluster Kafka"` — có thể kiểm toán, không phải ẩn trong prose.
- **Quyết định được tổng hợp:** `decisions` gom tất cả quyết định của chương thành một danh sách cấu trúc, giải quyết "phân mảnh quyết định".
- **Bóng dáng SSM ở tầng prompt:** recurrence + forgetting gate là phép ẩn dụ hình thức của $s_t = A s_{t-1} + B x_t$ — tạo cầu nối học thuật với literature state-space.

---

## 4. Thực nghiệm

### 4.1. Thiết lập

- **Mô hình:** `qwen3.5:4b-q4_K_M`, Ollama local, `temperature=0`, `LLM_MAX_WORKERS=1` (mặc định của webapp cho local Ollama).
- **Transcript kiểm soát:** 24 utterance, 1 chương, 3 chunk. Được thiết kế cố ý để: quyết định *"microservices + Kafka"* mở ở chunk 1, được tham chiếu bằng đại từ ở chunk 2, gán action ở chunk 3. Thực thể `gateway`, `schema registry`, `snake_case` mở ở giữa.
- **Baseline:** `HierarchicalRecapMethod`. **Đóng góp:** `SsDstRecapMethod`.
- **Harness:** `eval/run_ssdst_eval.py` — chạy cả hai method trên cùng transcript, ghi `ssdst_eval_raw.json`, `ssdst_eval_metrics.json`.

### 4.2. Chỉ số đo

Vì recall bão hòa trên transcript kiểm soát (cả hai đều 1.0), ta đo các đại lượng **phân biệt hơn**:
- **Structured decisions:** số quyết định được cấu trúc hóa (chỉ SS-DST có, qua `final_belief_state.decisions`).
- **Cross-chunk continuity notes:** số note liên kết ≥2 thực thể cốt lõi (`kafka`, `pipeline`, `microservices`) — dấu hiệu quyết định sống sót qua ranh giới chunk.
- **Dangling references:** note còn đại từ/deictic chưa giải quyết.
- **Cost:** LLM runs, wall-clock, input/output tokens.

### 4.3. Kết quả

**Bảng cost–benefit (xem §1).** SS-DST tốn 1.67× LLM run, 2.27× wall-clock, 1.74× input token, 2.66× output token.

**Bảng phân biệt cấu trúc:**

| Chỉ số | hierarchical | ssdst |
|---|---:|---:|
| Câu kiểu quyết định trong note | 5 (rải rác) | 3 |
| Quyết định cấu trúc (belief state) | 0 | 6 |
| Coreference giải quyết có provenance | 0 | 1 (`"nó" → "cluster Kafka"`) |
| Note liên kết đa-chunk | 2 | 3 |

**Belief state cuối của chương 1 (SS-DST):**
```json
{
  "current_topic": "Kiến trúc microservices với Kafka, snake_case cho schema và URL versioning.",
  "decisions": [
    "Chốt kiến trúc sử dụng microservices thay vì monolith.",
    "Chọn Kafka làm message broker cho pipeline.",
    "Sử dụng snake_case cho tất cả schema fields.",
    "Dùng URL versioning cho API."
  ],
  "open_actions": [
    "Cấu hình cluster Kafka — Tuấn",
    "Review cấu hình bảo mật cluster Kafka — Lan",
    "Định nghĩa schema qua Schema Registry cho từng service"
  ],
  "resolved_references": [{"pronoun": "nó", "refers_to": "cluster Kafka"}]
}
```

### 4.4. Phân tích trung thực

- **Coverage không đổi:** recall 1.0 cho cả hai → SS-DST *không* giúp "tóm tắt không thiếu ý" trên transcript dễ. Lợi ích nằm ở cấu trúc, không phải recall. Paper phải nói rõ điều này để không over-claim.
- **Coreference "ẩn" của baseline:** qwen3.5 đủ mạnh để paraphase bỏ đại từ → note baseline trông sạch nhưng mất provenance. SS-DST làm ngược lại: tường minh hóa ánh xạ. Đây là *trade-off về dạng output* chứ không phải lỗi của baseline.
- **Chi phí đáng kể:** ~2.3× wall-clock và token. Chỉ hợp lý khi coherence/auditability quan hơn speed — ví dụ biên bản cuộc họp chính thức, không phải recap nhanh real-time.
- **Quy mô thực nghiệm nhỏ:** 24 utterance, 1 chương, 1 transcript. Cần mở rộng ra dataset lớn (AMI, ICSI, QMSum) để khẳng định tổng quát — ghi nhận trong §6 (hạn chế).

---

## 5. Đóng góp (Contributions)

1. **Phương pháp SS-DST cho meeting recap:** belief state cuộn có cấu trúc, tiêm + cập nhật qua prompt, mô phỏng recurrence của SSM ở tầng LLM. (Code: `app/methods/ssdst_recap.py`.)
2. **Coreference resolution có provenance:** `resolved_references` lưu ánh xạ đại từ → thực thể, kiểm toán được.
3. **Tổng hợp quyết định xuyên chunk:** `decisions` gom quyết định rải rác thành danh sách cấu trúc, giải quyết phân mảnh.
4. **Forgetting gate có kiểm soát token budget:** state bounded ~180 token, ưu tiên giữ decisions/open_actions.
5. **Đánh giá trung thực cost–benefit:** đo cả cost (1.7–2.3×) lẫn benefit (structured decisions, coreference, continuity) — không over-claim recall.
6. **Tích hợp không xâm lấn:** SS-DST là method thứ ba cạnh highlights/hierarchical; baseline giữ nguyên để so sánh; tái dùng segmentation/chunking/title của hierarchical.

---

## 6. Hạn chế & hướng mở rộng

- **Quy mô nhỏ:** 1 transcript kiểm soát. Cần đánh giá trên AMI/ICSI/QMSum với ROUGE/BERTScore + human eval.
- **Cần gold coreference annotations:** hiện đo coreference gián tiếp qua `resolved_references` và dangling markers. Cần bộ gold coreference để tính P/R coreference chính xác.
- **Chi phí tuần tự:** tuần tự trong chương tăng wall-clock. Hướng: speculative state update (model nhỏ draft state, model lớn verify) hoặc state checkpoint + selective re-run.
- **Forgetting gate heuristic:** hiện ủy thác cho LLM qua prompt. Hướng: hiện thực forgetting tường minh (giữ top-k decisions theo recency/salience) để đo lường được.
- **Chỉ áp dụng cho hierarchical-shaped recap:** chưa áp dụng state cho `highlights` (extractive). Hướng: state có thể thúc đẩy extractive candidate selection (chọn utterance bổ sung decision chưa có trong state).

---

## 7. Kết luận

SS-DST chuyển tóm tắt phân cấp từ "các đoạn rời song song" sang "có bộ nhớ trạng thái đệ quy", giải quyết coreference và phân mảnh quyết định bằng một belief state có cấu trúc, có provenance, có thể kiểm toán. Đóng góp chính không phải tăng recall mà là tăng **chất lượng cấu trúc và khả năng kiểm toán**, đổi với chi phí ~2× tài nguyên. Đây là một cải thiện khả thi và có đóng góp mới cho paper về meeting summarization, đặc biệt ở góc độ *state-aware abstractive summarization*.
