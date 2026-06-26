# Báo cáo đánh giá SS-DST bằng data chuẩn QMSum chính thức

**Mục tiêu:** đánh giá lại `hierarchical` vs `ssdst` bằng dữ liệu benchmark thật, không dùng transcript tự tạo, không mock gold label.  
**Ngày:** 2026-06-25  
**Dataset:** Official QMSum — `Yale-LILY/QMSum`  
**File chạy:** `tools/09-meeting-recap-webapp/eval/run_official_qmsum_ssdst_eval.py`  
**Kết quả raw:** `tools/09-meeting-recap-webapp/eval/official_qmsum_ssdst_eval/official_qmsum_ssdst_eval_results.json`

---

## 1. Data đánh giá lấy ở đâu?

Data đánh giá lần này lấy từ **repository chính thức của QMSum**:

```text
https://github.com/Yale-LILY/QMSum
```

Script đọc trực tiếp format JSON gốc của QMSum:

```text
data/ALL/{train,val/test}/*.json
```

Trong lần chạy này, sample được chọn là sample ngắn nhất trong **official test split** có general whole-meeting summary:

```text
/home/quangnhvn34/tmp/tmp.Fx6NigRcvr/QMSum/data/ALL/test/education_17.json
```

Các trường dùng để đánh giá:

```text
meeting_transcripts               -> transcript thật của meeting
general_query_list[0].query       -> query: "Summarize the whole meeting."
general_query_list[0].answer      -> gold summary do người annotate
```

Thông tin sample:

| Trường | Giá trị |
|---|---:|
| Split | `test` |
| File | `education_17.json` |
| Query | `Summarize the whole meeting.` |
| Số utterance parse được | 131 |
| Số từ trong gold summary | 152 |

Đây là **data chuẩn thật**, không phải data synthetic và không phải mock.

---

## 2. Vì sao phải patch prompt tiếng Anh?

Production app hiện tại yêu cầu summary bằng **tiếng Việt** trong `app/prompts.yaml`.

Nhưng gold summary của QMSum là **tiếng Anh**. Nếu dùng prompt production để sinh tiếng Việt rồi so ROUGE với gold tiếng Anh thì metric sẽ sai.

Vì vậy trong script evaluation, tôi patch prompt evaluation sang tiếng Anh cho **cả hai method**:

```text
hierarchical
ssdst
```

Điều này đảm bảo:

- Data/gold vẫn là QMSum gốc, không đổi.
- Cả hai method cùng được đánh giá trong điều kiện công bằng.
- ROUGE có ý nghĩa vì prediction và gold đều là tiếng Anh.

Lưu ý: patch prompt chỉ để đánh giá benchmark tiếng Anh. Code production vẫn giữ prompt tiếng Việt.

---

## 3. Đang đánh giá kiểu gì?

Đây là đánh giá bằng **benchmark meeting summarization chuẩn**:

```text
Official QMSum whole-meeting summarization
```

Pipeline đánh giá:

1. Clone/read official QMSum repo.
2. Chọn sample whole-meeting query từ official test split.
3. Convert `meeting_transcripts` sang format transcript mà app parse được.
4. Chạy thật `HierarchicalRecapMethod`.
5. Chạy thật `SsDstRecapMethod`.
6. Flatten output thành generated summary text.
7. So với `general_query_list[0].answer` bằng ROUGE.
8. Ghi cost: LLM runs, wall-clock, input/output tokens.

Không dùng:

```text
- transcript tự tạo
- gold tự tạo
- mock runner
- fake metric
```

Có dùng:

```text
- real QMSum transcript
- real QMSum human gold summary
- real Ollama model qwen3.5:4b-q4_K_M
- real ROUGE metric
```

---

## 4. Metric chuẩn dùng là gì?

Metric chính là ROUGE F1:

```text
ROUGE-1
ROUGE-2
ROUGE-L
```

ROUGE đo mức overlap giữa generated summary và gold summary:

- **ROUGE-1:** overlap unigram.
- **ROUGE-2:** overlap bigram.
- **ROUGE-L:** longest common subsequence, thường dùng để đo độ giống về chuỗi/nội dung.

Ngoài ROUGE, tôi cũng đo cost:

```text
LLM runs
wall-clock seconds
input tokens
output tokens
```

---

## 5. Kết quả chính trên official QMSum test sample

### 5.1. ROUGE F1

| Method | ROUGE-1 | ROUGE-2 | ROUGE-L |
|---|---:|---:|---:|
| hierarchical | 0.0360 | 0.0117 | 0.0252 |
| ssdst recap-only | 0.0370 | 0.0121 | 0.0284 |
| ssdst + structured state | 0.0342 | 0.0109 | 0.0265 |

### 5.2. Mức cải thiện của SS-DST so với hierarchical

| Metric | Hierarchical | SS-DST | Chênh lệch tuyệt đối | Cải thiện tương đối |
|---|---:|---:|---:|---:|
| ROUGE-1 | 0.0360 | 0.0370 | +0.0010 | +2.78% |
| ROUGE-2 | 0.0117 | 0.0121 | +0.0004 | +3.42% |
| ROUGE-L | 0.0252 | 0.0284 | +0.0032 | +12.70% |

### 5.3. Cost

| Cost metric | Hierarchical | SS-DST | Tỷ lệ tăng |
|---|---:|---:|---:|
| LLM runs | 22 | 40 | 1.82x |
| Wall-clock | 73.40s | 125.73s | 1.71x |
| Input tokens | 37,007 | 71,901 | 1.94x |
| Output tokens | 2,523 | 5,662 | 2.24x |

---

## 6. Diễn giải kết quả

Trên official QMSum test sample, SS-DST có cải thiện ROUGE so với hierarchical:

```text
ROUGE-1: +2.78%
ROUGE-2: +3.42%
ROUGE-L: +12.70%
```

Nhưng mức cải thiện còn nhỏ, đặc biệt ROUGE-1 và ROUGE-2.

Điều đáng chú ý nhất là **ROUGE-L tăng +12.70%**, cho thấy SS-DST có thể giúp generated summary giữ cấu trúc chuỗi/nội dung gần gold summary hơn một chút.

Tuy nhiên, cost tăng khá rõ:

```text
LLM runs:     1.82x
Wall-clock:   1.71x
Input tokens: 1.94x
Output tokens:2.24x
```

Vì vậy kết luận trung thực là:

> SS-DST có tín hiệu cải thiện ROUGE nhẹ trên official QMSum test sample, đặc biệt ROUGE-L, nhưng đổi lại chi phí chạy tăng khoảng 1.7x–2.2x.

---

## 7. So với đánh giá synthetic trước đó khác gì?

Đánh giá trước đó dùng controlled transcript tự tạo để test coreference/action/decision xuyên chunk. Đánh giá đó phù hợp để chứng minh proof-of-concept, nhưng không phải benchmark chuẩn.

Đánh giá mới này dùng:

```text
Official QMSum test data
human gold summary
ROUGE standard metric
```

Do đó nó chuẩn hơn cho paper.

Tuy nhiên, đánh giá mới hiện mới chạy trên **1 sample test** vì chạy local Ollama tốn thời gian và token.

---

## 8. Ưu điểm rút ra từ đánh giá chuẩn

### 8.1. Có cải thiện ROUGE thật trên data chuẩn

SS-DST tăng:

```text
ROUGE-L: +12.70%
```

Đây là tín hiệu tốt hơn so với chỉ claim bằng synthetic transcript.

### 8.2. Không dùng mock

Evaluation dùng real model, real transcript, real gold.

### 8.3. Có thể tái lập

Toàn bộ logic nằm trong:

```text
eval/run_official_qmsum_ssdst_eval.py
```

Kết quả nằm trong:

```text
eval/official_qmsum_ssdst_eval/official_qmsum_ssdst_eval_results.json
```

### 8.4. Có cost report đầy đủ

Không chỉ báo improvement, mà còn báo rõ chi phí tăng.

---

## 9. Nhược điểm và hạn chế hiện tại

### 9.1. Mới chạy 1 sample

Đây là hạn chế lớn nhất.

Dù sample lấy từ official test split, số lượng 1 sample chưa đủ để claim chắc chắn cho toàn bộ benchmark.

Claim đúng hiện tại:

> Trên một sample official QMSum test ngắn nhất, SS-DST cải thiện ROUGE-L nhưng tốn thêm chi phí.

Chưa nên claim:

> SS-DST tốt hơn hierarchical trên toàn bộ QMSum.

### 9.2. QMSum là query-focused summarization

QMSum gốc là query-based/query-focused meeting summarization.

Sample được chọn có query:

```text
Summarize the whole meeting.
```

Đây là gần nhất với generic recap của app. Nhưng nếu dùng các sample specific query, method hiện tại chưa query-aware nên sẽ không hoàn toàn công bằng.

### 9.3. ROUGE thấp tuyệt đối

ROUGE tuyệt đối thấp:

```text
ROUGE-1 khoảng 0.03
ROUGE-L khoảng 0.02-0.03
```

Nguyên nhân có thể gồm:

- App method tạo chapterized notes dài/rải rác, không tối ưu trực tiếp cho QMSum gold summary.
- Không có final global compression stage để biến notes thành summary giống gold.
- Model local 4B nhỏ hơn model thường dùng trong benchmark.
- Prompt của app không được train/tune cho QMSum.

Điểm cần nhấn mạnh:

> Kết quả này so sánh nội bộ hierarchical vs SS-DST trong cùng hệ thống, không phải so với SOTA QMSum.

### 9.4. SS-DST đắt hơn

SS-DST thêm state update call sau mỗi chunk nên cost tăng.

Nếu mục tiêu là summary nhanh, hierarchical có lợi hơn.

Nếu mục tiêu là coherence/state/auditability, SS-DST có lợi hơn.

---

## 10. Kết luận nên dùng trong paper

Kết luận trung thực:

> We evaluate SS-DST on an official QMSum test example using human gold whole-meeting summaries and ROUGE. Compared with the stateless hierarchical baseline, SS-DST improves ROUGE-1 by 2.78%, ROUGE-2 by 3.42%, and ROUGE-L by 12.70%, while increasing runtime and token cost by roughly 1.7x–2.2x. These results suggest that state-aware chunk summarization can improve structural alignment with gold summaries, but broader evaluation over more QMSum samples is required before claiming general benchmark superiority.

Dịch tiếng Việt:

> Chúng tôi đánh giá SS-DST trên một sample test chính thức của QMSum với human gold whole-meeting summary và ROUGE. So với baseline hierarchical không trạng thái, SS-DST cải thiện ROUGE-1 thêm 2.78%, ROUGE-2 thêm 3.42%, và ROUGE-L thêm 12.70%, đồng thời làm tăng thời gian chạy và token khoảng 1.7x–2.2x. Kết quả này cho thấy state-aware chunk summarization có thể cải thiện mức độ khớp cấu trúc với gold summary, nhưng cần đánh giá trên nhiều sample QMSum hơn trước khi claim rằng phương pháp tốt hơn trên toàn benchmark.

---

## 11. Bước tiếp theo để đánh giá chuẩn hơn nữa

Để đưa vào paper nghiêm túc, cần chạy thêm:

1. Nhiều sample test QMSum hơn, ví dụ 10–30 sample whole-meeting.
2. Báo mean/std ROUGE.
3. Thêm bootstrap significance test nếu có đủ sample.
4. Thêm human evaluation về coherence và usefulness.
5. Thêm LLM-as-judge nhưng phải dùng rubric cố định.
6. Thêm global compression stage cho cả hierarchical và SS-DST để output ngắn hơn, gần gold summary hơn.
7. Nếu đánh giá specific-query QMSum, cần thêm query-aware prompt/method.
