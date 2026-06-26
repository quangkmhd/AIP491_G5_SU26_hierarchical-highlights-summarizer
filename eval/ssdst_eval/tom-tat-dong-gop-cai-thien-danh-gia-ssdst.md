# SS-DST đã đóng góp gì, cải thiện gì, cải thiện bao nhiêu, đang đánh giá kiểu gì, ưu và nhược điểm

**Dự án:** AIP491 — Meeting Recap Webapp
**Nhánh thực hiện:** `feat/ss-dst-meeting-recap`
**Method mới:** `ssdst` — State-Space Dialogue State Tracking
**File code chính:** `tools/09-meeting-recap-webapp/app/methods/ssdst_recap.py`
**Ngày:** 2026-06-25

---

## 1. SS-DST đã đóng góp gì?

SS-DST đóng góp một phương pháp tóm tắt meeting mới tên là **State-Space Dialogue State Tracking**, gọi tắt là **SS-DST**.

Trước khi có SS-DST, hệ thống có hai phương thức chính:

```text
highlights
hierarchical
```

Sau khi thêm SS-DST, hệ thống có thêm method thứ ba:

```text
e
ssdst
```

Đóng góp cốt lõi của SS-DST là:

> Thêm một “bộ nhớ trạng thái hội thoại” — dialogue belief state — để mô hình có thể nhớ thông tin từ các chunk trước khi tóm tắt chunk hiện tại.

Baseline `hierarchical` hiện tại tóm tắt từng chunk gần như độc lập. Với mỗi chunk 8 utterance, model chỉ nhìn thấy nội dung của chunk đó. Điều này làm cho model dễ mất ngữ cảnh nếu một ý quan trọng được nhắc ở chunk trước nhưng được tham chiếu lại ở chunk sau.

SS-DST thay đổi cách xử lý đó thành:

```text
chunk_1 + state_0 -> summary_1 -> state_1
chunk_2 + state_1 -> summary_2 -> state_2
chunk_3 + state_2 -> summary_3 -> state_3
...
```

Trong đó `state_t` là trạng thái nhớ sau chunk thứ `t`.

Belief state hiện tại có dạng:

```json
{
  "current_topic": "chủ đề đang thảo luận",
  "entities": ["Kafka", "API gateway", "schema registry"],
  "decisions": ["Chốt dùng microservices", "Chọn Kafka cho pipeline"],
  "open_actions": ["Tuấn phụ trách cluster Kafka", "Lan review bảo mật"],
  "resolved_references": [
    {"pronoun": "nó", "refers_to": "cluster Kafka"}
  ]
}
```

Như vậy, đóng góp không chỉ là viết prompt mới, mà là thêm một kiến trúc tóm tắt có trạng thái:

```text
state-aware hierarchical summarization
```

---

## 2. SS-DST cải thiện gì?

### 2.1. Cải thiện khả năng nhớ ngữ cảnh xuyên chunk

Baseline `hierarchical` tóm tắt từng chunk riêng lẻ. Ví dụ:

```text
Chunk 1: Chốt dùng Kafka cho pipeline.
Chunk 2: Lan nói sẽ review nó.
```

Nếu model chỉ thấy chunk 2, từ **“nó”** rất mơ hồ. Nó có thể là Kafka, pipeline, cluster, API, hoặc một thứ khác.

SS-DST lưu thông tin từ chunk 1 vào state:

```json
{
  "entities": ["Kafka", "pipeline"],
  "decisions": ["Chọn Kafka làm message broker cho pipeline"]
}
```

Khi xử lý chunk 2, state này được đưa vào prompt. Nhờ vậy model có thêm ngữ cảnh để hiểu:

```text
"nó" -> cluster Kafka / pipeline Kafka
```

Điểm cải thiện:

- Nhớ được entity xuyên chunk.
- Nhớ được quyết định đã chốt.
- Nhớ được action item đang mở.
- Giải quyết tốt hơn các tham chiếu như “nó”, “cái đó”, “pipeline đó”, “API vừa nói”.

---

### 2.2. Cải thiện việc tổng hợp quyết định

Baseline thường chỉ viết quyết định dưới dạng câu văn trong note, ví dụ:

```text
Đội nhóm thống nhất kiến trúc microservices với Kafka cho pipeline.
```

Nhưng baseline không có danh sách riêng để lưu quyết định. Vì vậy, nếu muốn biết meeting đã chốt những gì, người dùng vẫn phải đọc nhiều note rời rạc.

SS-DST tạo thêm trường:

```json
"decisions": [
  "Chốt kiến trúc sử dụng microservices thay vì monolith.",
  "Chọn Kafka làm message broker cho pipeline.",
  "Sử dụng snake_case cho tất cả schema fields.",
  "Dùng URL versioning cho API."
]
```

Điểm cải thiện:

- Quyết định được gom thành danh sách có cấu trúc.
- Dễ kiểm tra meeting đã chốt gì.
- Dễ dùng để viết biên bản chính thức.
- Dễ dùng cho downstream task như tạo ADR, task list hoặc project report.

---

### 2.3. Cải thiện action item tracking

Baseline có thể nhắc action item trong note, nhưng không có bộ nhớ riêng cho các việc cần làm.

SS-DST gom action item vào trường:

```json
"open_actions": [
  "Cấu hình cluster Kafka — Tuấn",
  "Review cấu hình bảo mật cluster Kafka — Lan",
  "Định nghĩa schema qua Schema Registry"
]
```

Điểm cải thiện:

- Action item rõ ràng hơn.
- Có thể biết ai phụ trách nếu transcript có bằng chứng.
- Có thể gom action item rải rác trong nhiều chunk.
- Dễ chuyển thành task list.

---

### 2.4. Cải thiện coreference resolution có provenance

Một điểm mới quan trọng là SS-DST không chỉ tự hiểu đại từ, mà còn lưu lại mapping đã giải quyết.

Ví dụ output có:

```json
"resolved_references": [
  {"pronoun": "nó", "refers_to": "cluster Kafka"}
]
```

Điều này giúp hệ thống trả lời được câu hỏi:

```text
Trong summary, “nó” đang chỉ cái gì?
```

Baseline không có cấu trúc này.

Đây là một đóng góp quan trọng cho paper vì nó làm cho summary có tính **kiểm toán được** — auditability.

---

### 2.5. Cải thiện tính kiểm toán của summary

SS-DST tạo thêm:

```text
belief_state_trace
final_belief_state
```

`belief_state_trace` cho biết sau mỗi chunk, state thay đổi như thế nào. Điều này giúp kiểm tra:

- Chunk nào sinh ra decision nào.
- State có bị mất action item không.
- Model có hallucinate decision/action không.
- Coreference được giải quyết ở bước nào.

Baseline chỉ có final summary, không có intermediate state.

---

## 3. Cải thiện bao nhiêu?

Tôi đã chạy evaluation thật với Ollama local model:

```text
qwen3.5:4b-q4_K_M
```

Transcript test gồm 24 utterance, được thiết kế để có:

- Quyết định nằm ở chunk trước.
- Đại từ/tham chiếu nằm ở chunk sau.
- Action item rải rác ở nhiều chunk.
- Nhiều entity như Kafka, pipeline, API gateway, schema registry, snake_case.

Kết quả chính:

| Chỉ số                           | Hierarchical baseline | SS-DST | Mức cải thiện |
| ---------------------------------- | --------------------: | -----: | ---------------: |
| Gold decision recall               |                   1.0 |    1.0 |     Không tăng |
| Gold action recall                 |                   1.0 |    1.0 |     Không tăng |
| Gold entity recall                 |                   1.0 |    1.0 |     Không tăng |
| Note liên kết đa-chunk          |                     2 |      3 |   **+50%** |
| Structured decisions               |                     0 |      6 | **0 → 6** |
| Structured open actions            |                     0 |      3 | **0 → 3** |
| Resolved references có provenance |                     0 |      1 | **0 → 1** |
| Số LLM runs                       |                     6 |     10 |      Tăng 1.67x |
| Wall-clock time                    |                 11.8s | 26.78s |      Tăng 2.27x |
| Input tokens                       |                 7,086 | 12,336 |      Tăng 1.74x |
| Output tokens                      |                   509 |  1,355 |      Tăng 2.66x |

## Diễn giải trung thực

SS-DST **không cải thiện gold recall** trong evaluation hiện tại vì transcript test khá rõ ràng, baseline `hierarchical` cũng đã tìm đủ các keyword quan trọng.

Cụ thể:

```text
Gold decision recall: 1.0 -> 1.0
Gold action recall:   1.0 -> 1.0
Gold entity recall:   1.0 -> 1.0
```

Điều này nghĩa là SS-DST không nên được claim là:

```text
SS-DST tóm tắt được nhiều ý hơn baseline trong mọi trường hợp.
```

Claim đúng hơn là:

```text
SS-DST cải thiện cấu trúc, tính liên kết xuyên chunk, khả năng kiểm toán, và khả năng biểu diễn decision/action/coreference dưới dạng có cấu trúc.
```

Nói ngắn gọn:

```text
Baseline: biết đủ ý, nhưng các ý nằm rải rác trong prose summary.
SS-DST: biết đủ ý + gom thành state có cấu trúc, có thể kiểm toán.
```

---

## 4. Đang đánh giá kiểu gì?

Hiện tại đang đánh giá theo kiểu **controlled evaluation**.

Nghĩa là tôi tạo một transcript có chủ đích để kiểm tra đúng điểm yếu của baseline và đúng điểm mạnh kỳ vọng của SS-DST.

---

### 4.1. Transcript test được thiết kế như thế nào?

Transcript gồm 24 utterance, chia thành nhiều chunk. Nội dung được thiết kế để có:

#### Decision ở chunk trước

```text
Chốt dùng microservices và Kafka cho pipeline.
```

#### Coreference ở chunk sau

```text
Lan sẽ review nó.
```

#### Action item rải rác

```text
Tuấn phụ trách cluster Kafka.
Lan review security.
Kim Anh viết ADR.
```

Mục tiêu là kiểm tra:

- Model có nhớ quyết định từ chunk trước không?
- Model có hiểu “nó” là gì không?
- Model có gom action item không?
- Model có giữ continuity qua chunk boundary không?
- SS-DST có sinh được state hữu ích không?

---

### 4.2. Các metric hiện tại

#### Metric 1: Gold recall

Tôi định nghĩa một số gold keyword:

```python
GOLD_DECISIONS = ["microservices", "kafka", "gateway", "rate limit", "snake_case"]
GOLD_ACTIONS = ["adr", "cluster", "schema", "ci/cd", "deadline"]
GOLD_ENTITIES = ["kafka", "gateway", "pipeline", "api", "schema"]
```

Sau đó kiểm tra output của từng method có nhắc đến các keyword này không.

Kết quả:

```text
hierarchical = 1.0
ssdst        = 1.0
```

Ý nghĩa:

- Cả hai đều cover đủ các keyword quan trọng.
- SS-DST không tăng recall thô trong test này.

Hạn chế:

- Đây là metric keyword-based, còn thô.
- Không đo được đúng/sai logic sâu.
- Không đo được summary có dễ đọc hay không.
- Không đo được factual consistency đầy đủ.

---

#### Metric 2: Cross-chunk continuity notes

Metric này đếm số note có khả năng nối nhiều ý xuyên chunk.

Ví dụ nếu một note chứa ít nhất 2 trong 3 term:

```text
kafka
pipeline
microservices
```

thì note đó được xem là có tính liên kết đa-chunk.

Kết quả:

```text
hierarchical = 2
ssdst        = 3
```

Mức cải thiện:

```text
+50%
```

Ý nghĩa:

- SS-DST tạo nhiều note có khả năng nối các decision/entity xuyên chunk hơn.
- Đây là tín hiệu tốt cho coherence.

---

#### Metric 3: Structured decisions

Baseline không có belief state, nên số structured decisions là:

```text
hierarchical = 0
```

SS-DST có `final_belief_state.decisions`, kết quả:

```text
ssdst = 6
```

Mức cải thiện:

```text
0 -> 6
```

Ý nghĩa:

- SS-DST không chỉ viết quyết định trong prose mà còn trích chúng thành list có cấu trúc.
- Đây là metric quan trọng nhất để chứng minh đóng góp về auditability.

---

#### Metric 4: Structured open actions

Baseline không có trường riêng để lưu action đang mở:

```text
hierarchical = 0
```

SS-DST có:

```text
ssdst = 3
```

Mức cải thiện:

```text
0 -> 3
```

Ý nghĩa:

- SS-DST có thể biến meeting recap thành task-oriented output tốt hơn.
- Có thể dùng cho follow-up hoặc project management.

---

#### Metric 5: Resolved references

Baseline không xuất mapping coreference:

```text
hierarchical = 0
```

SS-DST xuất được:

```json
{"pronoun": "nó", "refers_to": "cluster Kafka"}
```

Kết quả:

```text
ssdst = 1
```

Mức cải thiện:

```text
0 -> 1 explicit coreference provenance
```

Ý nghĩa:

- SS-DST có khả năng giải thích rõ một đại từ đang chỉ đến thực thể nào.
- Đây là điểm mạnh khi viết paper về robustness/coherence.

---

#### Metric 6: Cost metrics

SS-DST tốn tài nguyên hơn baseline.

| Cost metric   | Baseline | SS-DST | Tăng |
| ------------- | -------: | -----: | ----: |
| LLM runs      |        6 |     10 | 1.67x |
| Wall-clock    |    11.8s | 26.78s | 2.27x |
| Input tokens  |    7,086 | 12,336 | 1.74x |
| Output tokens |      509 |  1,355 | 2.66x |

Ý nghĩa:

- SS-DST tốt hơn về structure/coherence.
- Nhưng chậm hơn và tốn token hơn.
- Đây là trade-off cần nói rõ trong paper.

---

## 5. Ưu điểm của SS-DST

### 5.1. Có bộ nhớ xuyên chunk

Ưu điểm lớn nhất là SS-DST có rolling memory.

Baseline:

```text
summary_t = summarize(chunk_t)
```

SS-DST:

```text
summary_t = summarize(chunk_t, state_{t-1})
state_t = update(state_{t-1}, chunk_t, summary_t)
```

Do đó chunk sau không còn bị cô lập khỏi chunk trước.

---

### 5.2. Có cấu trúc rõ ràng

SS-DST không chỉ tạo text summary, mà còn tạo:

```text
entities
decisions
open_actions
resolved_references
```

Những trường này giúp meeting recap trở thành dạng bán cấu trúc, dễ dùng cho:

- biên bản họp,
- action tracking,
- ADR generation,
- project report,
- downstream automation.

---

### 5.3. Có provenance cho coreference

SS-DST có thể ghi:

```json
{"pronoun": "nó", "refers_to": "cluster Kafka"}
```

Điều này giúp người dùng kiểm tra tại sao summary hiểu một tham chiếu theo cách đó.

Baseline không có khả năng này.

---

### 5.4. Dễ viết thành đóng góp học thuật

SS-DST có nền tảng lý thuyết tốt:

- Dialogue State Tracking,
- State-Space Models,
- Mamba-style recurrence,
- rolling memory,
- belief state,
- forgetting gate,
- coreference-aware summarization.

Vì vậy có thể claim như sau:

```text
We propose a state-aware hierarchical meeting summarization framework that maintains a compact dialogue belief state across transcript chunks.
```

Đây là một contribution rõ hơn nhiều so với chỉ “tối ưu prompt”.

---

### 5.5. Không phá baseline

SS-DST được thêm như method riêng:

```text
ssdst
```

Các method cũ vẫn giữ nguyên:

```text
highlights
hierarchical
```

Ưu điểm:

- Dễ so sánh ablation.
- Dễ rollback.
- Không làm hỏng flow hiện tại.
- Có thể chọn method tùy mục đích.

---

## 6. Nhược điểm của SS-DST

### 6.1. Chậm hơn baseline

Vì state của chunk sau phụ thuộc vào chunk trước, các chunk trong cùng chapter phải xử lý tuần tự.

Baseline có thể chạy chunk song song nhiều hơn. SS-DST phải làm:

```text
chunk 1 -> update state -> chunk 2 -> update state -> chunk 3 -> update state
```

Trong evaluation hiện tại:

```text
wall-clock tăng từ 11.8s lên 26.78s
```

Tức là tăng khoảng:

```text
2.27x
```

---

### 6.2. Tốn token hơn

Vì mỗi chunk phải nhận thêm belief state, và sau mỗi chunk còn có thêm một LLM call để update state.

Kết quả:

```text
input tokens tăng 1.74x
output tokens tăng 2.66x
```

Đây là nhược điểm lớn nếu mục tiêu là summary nhanh hoặc rẻ.

---

### 6.3. Evaluation hiện tại còn nhỏ

Hiện tại mới đánh giá trên một controlled transcript gồm 24 utterance.

Do đó chưa thể claim rộng rằng:

```text
SS-DST luôn tốt hơn trên mọi meeting.
```

Claim hợp lý hiện tại là:

```text
SS-DST cải thiện structural coherence và auditability trong các meeting có coreference/decision/action xuyên chunk.
```

Muốn claim mạnh hơn cần chạy thêm trên:

- AMI,
- ICSI,
- QMSum,
- transcript ASR noisy thật,
- nhiều domain meeting khác nhau.

---

### 6.4. Metric hiện tại còn thô

Một số metric hiện tại là keyword-based. Ví dụ gold recall chỉ kiểm tra output có chứa keyword hay không.

Hạn chế:

- Không biết summary có đúng logic hay không.
- Không biết có hallucination hay không.
- Không biết câu summary có tự nhiên hay không.
- Không đo được factual consistency đầy đủ.

Cần bổ sung:

- Human evaluation.
- LLM-as-judge có rubric rõ.
- Decision extraction F1.
- Action item F1.
- Coreference accuracy.
- Hallucination rate.
- ROUGE / BERTScore / QuestEval.
- Latency/token cost normalized by meeting length.

---

### 6.5. State update phụ thuộc vào LLM

State được cập nhật bởi LLM. Vì vậy state có thể bị lỗi:

- bỏ sót entity,
- merge sai decision,
- hallucinate action,
- ghi sai assignee,
- giải quyết coreference sai.

Cần thêm validation chặt hơn hoặc post-processing rule-based cho các trường quan trọng.

---

### 6.6. Forgetting gate hiện tại còn prompt-based

Prompt yêu cầu LLM giữ state ngắn và ưu tiên decisions/open_actions. Nhưng chưa có thuật toán explicit như:

```text
keep top-k entities by salience
keep most recent decisions
drop low-importance entities
```

Do đó việc quên/thêm thông tin vẫn phụ thuộc khá nhiều vào model.

Hướng cải thiện:

- Dùng scoring salience.
- Dùng recency weighting.
- Dùng entity frequency.
- Dùng explicit state compression.
- Dùng deterministic validator.

---

## 7. Kết luận ngắn gọn

### SS-DST đóng góp gì?

SS-DST thêm một phương pháp meeting summary có **bộ nhớ trạng thái hội thoại xuyên chunk**.

Nó biến hierarchical summary từ:

```text
stateless chunk summarization
```

thành:

```text
state-aware chunk summarization
```

---

### SS-DST cải thiện gì?

SS-DST cải thiện:

- nhớ ngữ cảnh xuyên chunk,
- giải quyết coreference,
- gom quyết định thành structured decisions,
- gom action item thành structured open actions,
- tạo belief state trace để kiểm toán,
- tăng tính liên kết giữa các chunk.

---

### Cải thiện bao nhiêu?

Trên evaluation hiện tại:

```text
Structured decisions:        0 -> 6
Structured open actions:     0 -> 3
Resolved references:         0 -> 1
Cross-chunk continuity notes: 2 -> 3 (+50%)
Gold recall:                 1.0 -> 1.0 (không tăng)
Cost:                        tăng khoảng 1.7x-2.3x
```

---

### Đang đánh giá kiểu gì?

Đang đánh giá bằng controlled evaluation trên transcript 24 utterance có chủ đích chứa:

- decision xuyên chunk,
- action item rải rác,
- coreference như “nó”, “pipeline đó”,
- nhiều entity kỹ thuật như Kafka, API gateway, schema registry.

So sánh:

```text
hierarchical baseline vs ssdst
```

Metric gồm:

- gold keyword recall,
- cross-chunk continuity notes,
- structured decisions,
- structured open actions,
- resolved references,
- token cost,
- wall-clock time.

---

### Ưu điểm chính

```text
Có trí nhớ, có cấu trúc, có provenance, dễ kiểm toán, dễ viết paper.
```

### Nhược điểm chính

```text
Chậm hơn, tốn token hơn, evaluation còn nhỏ, metric còn thô, state update phụ thuộc LLM.
```

---

## 8. Claim nên dùng trong paper

Claim nên viết thận trọng:

> SS-DST does not primarily improve raw content recall when the baseline already covers all salient keywords. Instead, it improves structural coherence, cross-chunk continuity, decision consolidation, and auditability by maintaining a compact dialogue belief state across transcript chunks.

Dịch sang tiếng Việt:

> SS-DST không chủ yếu cải thiện recall thô khi baseline đã bao phủ đủ keyword quan trọng. Thay vào đó, SS-DST cải thiện tính liên kết cấu trúc, continuity xuyên chunk, khả năng gom quyết định, và khả năng kiểm toán bằng cách duy trì một dialogue belief state nhỏ gọn xuyên suốt các chunk của transcript.
