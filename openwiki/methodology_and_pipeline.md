# 🔬 Phương pháp luận (Methodology) & Quy trình xử lý (Pipeline)

Tài liệu này cung cấp cái nhìn chi tiết và toàn diện nhất về mặt lý thuyết, công thức toán học và thiết kế kỹ thuật của hệ thống tóm tắt cuộc họp phân cấp kết hợp phân mảnh chủ đề. 

Hệ thống được phát triển dựa trên sự kết hợp độc đáo giữa giải thuật phân mảnh chủ đề phi giám sát có độ chính xác cao (**Sliding TextTiling**) và mô hình sinh tóm tắt học sâu có giám sát theo mô hình cuộn phân cấp (**Hierarchical Chunk Summarization** và **Deferred Topic Titling**).

---

## 🗺️ Quy trình tổng quan hệ thống (System Pipeline)

Hệ thống hỗ trợ cả hai luồng xử lý chính: **Async Streaming Pipeline** (Dành cho việc thu nhận hội thoại thời gian thực qua Web-socket/SSE) và **Batch Processing Pipeline** (Dành cho phân tích ngoại tuyến).

```
 📥 Dòng hội thoại (Utterance Stream / Dialogue Transcript)
                       │
                       ▼
 ┌────────────────────────────────────────────────────────┐
 │ 1. Phân mảnh chủ đề bằng Sliding TextTiling            │  <-- Phi giám sát (Unsupervised)
 │    - Tách từ, lọc Stopwords Tiếng Việt                 │
 │    - Tính toán Cosine Similarity qua cửa sổ Block      │
 │    - Xác định Cực tiểu độ sâu trên đa bán kính (Radii)  │
 │    - Lọc ngưỡng Động (Dynamic Thresholding)            │
 │    - Gom cụm Segment nhỏ (Greedy Small Segment Merge) │
 └────────────────────────────────────────────────────────┘
                       │
             [Mốc ranh giới chủ đề]
                       │
                       ▼ (Chia luồng xử lý theo Segment)
 ┌────────────────────────────────────────────────────────┐
 │ 2. Gom cụm phân chia đoạn hội thoại (Chunking Service) │  <-- Tối đa 8 câu hội thoại/Chunk
 └────────────────────────────────────────────────────────┘
                       │
                [Danh sách Chunk]
                       │
                       ▼ 
 ┌────────────────────────────────────────────────────────┐
 │ 3. Tóm tắt phân đoạn (ViT5 Chunk Summarizer)           │  <-- Tóm tắt cuộn (Rolling Summaries)
 │    - Định dạng: "speaker: text" -> Tóm tắt rời         │
 └────────────────────────────────────────────────────────┘
                       │
            [Các bản tóm tắt trung gian]
                       │
                       ▼ (Nối các bản tóm tắt bằng ký tự " / ")
 ┌────────────────────────────────────────────────────────┐
 │ 4. Tạo tiêu đề trì hoãn (BARTpho Topic Titler)        │  <-- Độc lập ngữ cảnh thô (Summary-only)
 └────────────────────────────────────────────────────────┘
                       │
                       ▼
 📤 Báo cáo phân cấp hoàn chỉnh (HierarchicalRecap)
```

---

## 📊 1. Phương pháp phân mảnh chủ đề Sliding TextTiling

Thuật toán phân mảnh của hệ thống là một biến thể nâng cấp phi mạng (network-free) từ giải thuật **TextTiling** truyền thống của Hearst, được điều chỉnh để tối ưu hóa trên cấu trúc đối thoại dạng hội thoại ngắn (utterances) thay vì văn bản viết thông thường.

### Bước 1.1: Trích xuất đặc trưng Bag-of-Words (BoW)
Với mỗi câu thoại $u_i$ trong danh sách hội thoại $U = \{u_1, u_2, ..., u_n\}$, hệ thống tiến hành:
1. Chuẩn hóa chữ thường (lowercase).
2. Loại bỏ các ký tự đặc biệt (`.,!?"'()[]:;-`).
3. Lọc bỏ các từ dừng (Stopwords) Tiếng Việt sử dụng thư viện `stopwordsiso` (Mã ngôn ngữ `"vi"`).
4. Biểu diễn câu thoại dưới dạng một từ điển tần suất từ (Bag-of-Words):
   $$BoW(u_i) = \{w: count(w)\}$$

*Mã nguồn cụ thể:* `src/segmenters/sliding_texttiling.py -> def bow()`

### Bước 1.2: Tính toán độ tương đồng Cosine giữa các block thoại (Gap Cosine Similarity)
Để xác định mức độ nhất quán chủ đề tại mỗi điểm phân tách giữa câu thoại $u_i$ và $u_{i+1}$ (gọi là khe nứt / gap $i$), hệ thống trượt một cửa sổ có kích thước $k$ (biến số `block_size`).
- Tập hợp các câu thoại bên trái khe nứt $i$ (từ vị trí thoại $max(1, i-k+1)$ đến $i$) được gộp chung thành một BoW lớn $B_1$.
- Tập hợp các câu thoại bên phải khe nứt $i$ (từ vị trí $i+1$ đến $min(n, i+k)$) được gộp thành BoW lớn $B_2$.
- Tính toán giá trị tương đồng Cosine giữa hai vector này:
  $$Similarity(i) = \frac{B_1 \cdot B_2}{\|B_1\| \|B_2\|} = \frac{\sum_{w} count_{B_1}(w) \times count_{B_2}(w)}{\sqrt{\sum_w count_{B_1}^2(w)} \sqrt{\sum_w count_{B_2}^2(w)}}$$

*Mã nguồn cụ thể:* `src/segmenters/sliding_texttiling.py -> def similarity_scores()`

### Bước 1.3: Tính toán điểm sâu đa bán kính (Multi-Scale Depth Scoring)
Một điểm phân tách chủ đề tiềm năng thương xuất hiện tại đáy thung lũng của đồ thị độ tương đồng (nơi cuộc đối thoại chuyển nội dung và sự lặp lại từ vựng giữa hai phía giảm mạnh). Độ sâu của thung lũng tại vị trí gap $i$ được tính bằng cách tìm giá đỉnh tương đồng cao nhất về hai phía Trái và Phải trong một phạm vi bán kính khảo sát $r$ (radius):
$$hl_r(i) = \max(\{Similarity(j) \mid i - r \leq j \leq i \text{ và đồ thị dốc lên về bên trái}\})$$
$$hr_r(i) = \max(\{Similarity(j) \mid i \leq j \leq i + r \text{ và đồ thị dốc lên về bên phải}\})$$

Độ sâu tại vị trí $i$ ứng với bán kính $r$ là:
$$Depth_r(i) = \frac{1}{2} (hl_r(i) + hr_r(i) - 2 \times Similarity(i))$$

Để thuật toán bắt được cả các dịch chuyển chủ đề vi mô (bán kính nhỏ) và vĩ mô (bán kính lớn), hệ thống khảo sát đa bán kính (Mặc định `radii = [3, 5, 10, 15, 20]`). Mỗi bản đồ độ sâu $Depth_r(i)$ sau đó được chuẩn hóa Z-score:
$$Normalized\_Depth_r(i) = \frac{Depth_r(i) - \mu_r}{\sigma_r + \epsilon}$$

Và sau đó tổng hợp lại (bằng phép toán trung bình `mean`):
$$MultiScale\_Depth(i) = \frac{1}{|R|} \sum_{r \in R} Normalized\_Depth_r(i)$$

*Mã nguồn cụ thể:* `src/segmenters/sliding_texttiling.py -> def depth_scores(), normalize(), multiscale_depth()`

### Bước 1.4: Lọc ngưỡng động thích ứng (Dynamic Thresholding)
Một khe nứt $i$ được ghi nhận là một ranh giới chủ đề (boundary) nếu độ sâu đa cực của nó vượt qua một ngưỡng tự thích ứng thích nghi theo toàn bộ cấu trúc văn bản:
$$Ngưỡng = \mu_{all} + \alpha \times \sigma_{all}$$

*Trong đó:*
- $\mu_{all}$: Trung bình của mảng điểm độ sâu tổng hợp $MultiScale\_Depth$.
- $\sigma_{all}$: Độ lệch chuẩn của mảng điểm độ sâu tổng hợp $MultiScale\_Depth$.
- $\alpha$: Hệ số nhạy cảm (`alpha` mặc định thường là `0.4` đến `0.6`).

*Mã nguồn cụ thể:* `src/segmenters/sliding_texttiling.py -> def find_boundaries()`

### Bước 1.5: Gộp phân đoạn tham lam kích thước nhỏ (Greedy Small Segment Merge)
Để tránh hiện tượng phân mảnh vụn vặt (oversubdivision) tạo ra các phân đoạn quá ngắn chỉ có 1-2 câu thoại, hệ thống áp dụng bộ lọc gộp tham lam:
- Nếu khoảng cách giữa hai boundary kề nhau nhỏ hơn $N \times min\_segment\_ratio$ (với $N$ là số lượng câu thoại trong toàn bộ cuộc họp, tỷ lệ mặc định là $0.05$ hay $5\%$), phân đoạn nhỏ này sẽ bị gộp vào phân đoạn lân cận trái hoặc phải ưu tiên phía có độ sâu nông hơn (ít biến động chủ đề hơn).

*Mã nguồn cụ thể:* `src/segmenters/sliding_texttiling.py -> def merge_small_segments()`

---

## 📝 2. Tóm tắt hierarchical (Hierarchical Summarization & Titling)

Theo nghiên cứu từ **Paper 2**, việc cố gắng nhồi nhét hàng nghìn câu thoại thô trực tiếp vào một cửa sổ ngữ cảnh của mô hình LLM để sinh tóm tắt hoặc viết tiêu đề đem lại hiệu suất rất kém, mất mát thông tin (hiện tượng "lost in the middle"). Hệ thống áp dụng cấu trúc tóm tắt cuộn phân cấp.

### Bộ tóm tắt phân đoạn: `ViT5 Chunk Summarizer`
- **Nhiệm vụ:** Nhận một Chunk tối đa 8 câu thoại liên tiếp từ một phân đoạn phân mảnh, viết một bản tóm tắt ngắn đầy đủ ý cho Chunk đó.
- **Dòng dữ liệu đầu vào:** Để giữ ngữ cảnh về người nói, danh sách câu thoại trong Chunk được định dạng dưới dạng chuỗi nối có phân cách xuống dòng và kèm tên:
  ```text
  Tóm tắt: Speaker A: Chào mọi người, hôm nay chúng ta bàn về tính năng streaming.
  Speaker B: Tôi nghĩ nên sử dụng Server-Sent Events (SSE) để truyền dữ liệu nhẹ hơn.
  Speaker A: Hoàn toàn đồng ý, giải pháp này vừa đơn giản vừa tối ưu.
  ```
- **Kỹ thuật thu hẹp & Sinh:**
  - Chuỗi đầu vào được cắt góc (truncated) nghiêm ngặt tại **512 tokens** để phù hợp hoàn hảo với kiến trúc encoder của ViT5 Tiếng Việt.
  - Sử dụng giải thuật sinh Beam Search với bộ tham số tối ưu: **4 beams**, số lượng sinh token mới tối đa `max_new_tokens = 128`.
- **Mã nguồn:** `src/repo/seq2seq_inference.py -> class ViT5ChunkSummarizer`

### Bộ gán tiêu đề độc lập: `BARTpho Topic Titler`
- **Nhiệm vụ:** Tạo một tiêu đề súc tích mang tính khái quát cao cho toàn bộ Segment sau khi Segment đó đã đóng.
- **Kỹ thuật tóm tắt tóm tắt (Summary-only):** Mô hình BARTpho tạo tiêu đề không bao giờ đọc trực tiếp cuộc hội thoại thô của Segment. Thay vào đó, nó tận dụng các kết quả tóm tắt Chunk trung gian đã được ViT5 tạo ra trước đó.
- **Đầu vào xử lý:**
  - Nối toàn bộ các bản tóm tắt Chunk trong Segment lại với nhau bằng ký tự phân tách: `[Summary 1] / [Summary 2] / [Summary 3]`.
  - Chỉ lấy **1.500 ký tự cuối cùng** của chuỗi nối này, thêm tiền tố định hướng `Tạo tiêu đề: ` để đưa vào mô hình viết tiêu đề. Cách tiếp cận này giúp cô đọng hoàn hảo tính chất của chương mà không bị loãng ngữ cảnh.
  - Cắt góc đầu vào tại **1024 tokens**.
  - Sinh tiêu đề thông qua Beam Search: **4 beams**, độ dài tiêu đề tối đa `max_new_tokens = 200`.
- **Mã nguồn:** `src/repo/seq2seq_inference.py -> class BARTphoTopicTitler`

---

## ⚡ 3. Async Streaming Pipeline (Quy trình truyền phát không đồng bộ)

Hệ thống được thiết kế tối ưu hóa cho trải nghiệm người dùng cuối theo triết lý hiển thị sớm cấu trúc nội dung. Sơ đồ tuần tự các sự kiện truyền dữ liệu thời gian thực được thể hiện qua các mốc thời gian dưới đây:

```
[Bắt đầu gửi] ──► Mốc 0: Gửi và duyệt Utterance đơn lẻ
                     │ Emits event: "utterance-accepted" (Mỗi khi có câu thoại mới)
                     ▼
                 Mốc 1: Toàn bộ Transcript thô được gom lại và chuyển qua bộ phân đoạn
                     │ 
                     ▼
                 Mốc 2: Tính toán xong ranh giới Sliding TextTiling
                     │ Emits event: "segment-closed" (Một phân đoạn chủ đề được xác định)
                     ▼
                 Mốc 3: Lần lượt phân chia Chunk tối đa 8 câu thoại trong phân đoạn đó
                     │ Gọi mô hình ViT5 tóm tắt từng đoạn
                     │ Emits event: "chunk-closed" (Chứa `rolling_summary` của phân đoạn con)
                     ▼
                 Mốc 4: Sau khi toàn bộ các Chunk của một Segment đã có tóm tắt
                     │ Gộp các tóm tắt Chunk lại, gọi BARTpho viết tiêu đề chủ đề
                     │ Emits event: "title-emitted" (Trực tiếp cập nhật tiêu đề chương thoại)
                     ▼
[Kết thúc]   ──► Mốc 5: Kết thúc toàn bộ tiến trình
                     │ Gom toàn bộ dữ liệu đối tượng cấu trúc HierarchicalRecap
                     │ Emits event: "meeting-completed" (Kết thúc kết nối SSE)
```

### Các sự kiện chuẩn của Orchestrator (`OrchestratorEvent`)

| Tên sự kiện (`type`) | Mô tả hành vi kích hoạt | Dữ liệu mang theo (`data`) |
| :--- | :--- | :--- |
| `utterance-accepted` | Phát ra cho mọi câu thoại từ câu thứ 2 trở đi để xác nhận việc hệ thống đã ghi nhận câu thoại. | `{"index": int, "speaker": str, "text": str}` |
| `chunk-closed` | Xuất hiện ngay khi một nhóm khối (tối đa 8 thoại) hoàn tất và được sinh tóm tắt thành công bởi ViT5. | `{"chunk_id": str, "segment_id": str, "utterances_start": int, "utterances_end": int, "rolling_summary": str}` |
| `segment-closed` | Phát ra ngay sau khi ranh giới phân mảnh của Sliding TextTiling được xác nhận. Giúp giao diện Front-end vẽ ngay khung Card của Segment. | `{"segment_id": str, "utterances_start": int, "utterances_end": int}` |
| `title-emitted` | Phát ra sau khi tất cả các chunk thuộc Segment đã hoàn tất tóm tắt và mô hình BARTpho viết xong tiêu đề. | `{"segment_id": str, "title": str}` |
| `meeting-completed` | Sự kiện cuối cùng báo hiệu toàn bộ tiến trình tóm tắt phân cấp cuộc họp hoàn tất. | `{"hierarchical_recap": HierarchicalRecap}` |

*Mã nguồn cụ thể:* `src/service/meeting_recap_orchestrator.py -> StreamingOrchestrator.process_stream()`

---

## 📦 4. Batch Processing Pipeline (Quy trình xử lý khối đồng bộ)

Để đảm bảo hiệu năng tối ưu và tránh chạy các mô hình học sâu đắt đỏ nhiều lần trên cùng một tệp dữ liệu đầu vào, quá trình xử lý toàn bộ cuộc họp một lần duy nhất (one-shot batch processing) được định nghĩa hoàn toàn dựa trên luồng Async Streaming.

Khi gọi hàm `orchestrator.process_batch(dialogue)`:
1. Orchestrator khởi tạo generator truyền phát và tự động lắng nghe luồng stream cục bộ.
2. Trình gom dữ liệu duyệt qua tất cả các sự kiện phát sinh.
3. Khi nhận được dữ liệu từ các sự kiện `chunk-closed`, hệ thống đẩy trực tiếp chúng vào cấu trúc dữ liệu lưu trữ Segment đại diện.
4. Khi nhận sự kiện `title-emitted`, tiêu đề được gán trực tiếp vào segment tương ứng.
5. Sự kiện kết thúc `meeting-completed` kích hoạt kiểm tra tính hợp lệ dữ liệu bằng Pydantic model (`HierarchicalRecap.model_validate()`) và trả về kết hợp chất lượng cao, đồng nhất cấu trúc dữ liệu xuất khẩu.

Cách thiết kế này đảm bảo tỷ lệ lỗi (error rate) giữa quá trình hiển thị thời gian thực SSE và cơ sở dữ liệu lưu trữ là $0\%$, vì hai luồng xử lý dùng chung một logic xây dựng lõi.

*Mã nguồn cụ thể:* `src/service/meeting_recap_orchestrator.py -> StreamingOrchestrator.process_batch()`
