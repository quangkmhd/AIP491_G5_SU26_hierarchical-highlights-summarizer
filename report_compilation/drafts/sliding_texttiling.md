# Phương Pháp Luận & Kiến Trúc Multi-Scale Sliding TextTiling

Tài liệu này trình bày chi tiết về kiến trúc, các công thức toán học, thuật toán và phương pháp luận (**Methodology**) của thuật toán phân đoạn chủ đề hội thoại **Sliding TextTiling** (`SlidingTextTilingSegmenter`). Đây là thành phần lõi thuộc phân hệ **Dialogue Topic Segmentation (DTS)** của hệ thống, giúp tự động nhận diện các điểm chuyển tiếp chủ đề (topic shifts/boundaries) trong văn bản hội thoại dài dựa trên nền tảng thuật toán ý tưởng gốc TextTiling kết hợp phân tích đa quy mô.

---

## 1. Bản chất Phương pháp luận (Methodology)

### 1.1 Khơi nguồn ý tưởng
Các thuật toán phân đoạn văn bản truyền thống thường đánh giá mức độ gắn kết ngữ nghĩa dựa trên một kích thước cửa sổ cố định dốc (single-scale) dựa theo thuật toán TextTiling gốc. Tuy nhiên, các hội thoại thường tồn tại cấu trúc chủ đề đa tầng (**hierarchical/multi-layer structure**):
- **Chủ đề hạt mịn (Fine-grained topics / Micro-shifts):** Là những cuộc trao đổi ngắn, diễn ra nhanh chóng, biến đổi từ ý này sang ý khác chỉ sau vài câu thoại (utterances). Lúc này ta cần xem xét ở một bán kính rất nhỏ ($r$ từ $3$ đến $5$).
- **Chủ đề hạt thô (Coarse-grained topics / Macro-shifts):** Là những mảng chủ đề lớn (ví dụ: Chuyển từ "Tổng kết doanh số" sang "Thảo luận kế hoạch marketing"). Sự chuyển tiếp này cần một cái nhìn bao quát ở bán kính rộng hơn ($r = 15$ hoặc $20$).

Thuật toán **Sliding TextTiling** (là phương pháp do chúng tôi thiết kế và đề xuất trong nghiên cứu này) kết hợp hoàn hảo hai nguồn ý tưởng chính đại diện cho hai trường phái:
1. **Lý thuyết Sliding Window từ bài báo của Microsoft (Asthana et al., 2025):** "LLM-powered Meeting Recap System" (Section 3.2.2). Trong nghiên cứu đó, họ sử dụng mô hình Transformer với cửa sổ trượt dài 30 câu thoại (stride 10) để xử lý các biên chủ đề cục bộ, sau đó đồng bộ kết quả bằng cơ chế bỏ phiếu cực đại (max-voting).
2. **Cơ chế Phân tích Depth Score đa tỷ lệ dựa trên nền tảng TextTiling:** Do việc phân đoạn bằng biểu diễn Bag-of-Words (BoW) không chịu giới hạn token ngặt nghèo của Transformer, phương pháp đề xuất của chúng tôi thay thế việc trượt cửa sổ vật lý bằng việc **tính toán Depth Score song song trên nhiều bán kính tìm đỉnh khác nhau** (Multi-scale peaks). Cách tiếp cận này giúp ghi nhận luân phiên cả sự thay đổi chủ đề ngắn lẫn các cột mốc thay đổi chuyên đề lớn của cuộc họp.

---

## 2. Kiến trúc Hệ thống (Architecture Diagram)

Hội thoại đầu vào là danh sách các câu thoại luân phân ($U_1, U_2, \dots, U_n$). Luồng xử lý của Sliding TextTiling được biểu diễn qua kiến trúc phân tầng dưới đây:

```
                      [ Danh sách Câu thoại Đầu vào (Utterances) ]
                                          │
                                          ▼
                         [ Tiền xử lý & Trích xuất BoW ]
                 (Loại bỏ dấu câu, chuyển chữ thường, dừng stopwordsiso - vi)
                                          │
                                          ▼
                         [ Tính toán Cosine Similarity ]
                       (Giữa các khối kích thước block_size)
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   ▼                                             ▼
          Bán kính r = 3 (Micro)                       Bán kính r = 20 (Macro)
    [ Tìm đỉnh trái/phải cực đại ]               [ Tìm đỉnh trái/phải cực đại ]
    [ Tính toán Depth Score cục bộ ]              [ Tính toán Depth Score cục bộ ]
                   │                                             │
                   ▼                                             ▼
          [ Chuẩn hóa Z-Score ]                         [ Chuẩn hóa Z-Score ]
                   └──────────────────────┬──────────────────────┘
                                          │
                                          ▼
                               [ Tích hợp Aggregation ]
                          (Tính giá trị trung bình Mean)
                                          │
                                          ▼
                             [ Tổng phổ Multi-scale Depth ]
                                          │
                                          ▼
                          [ Thiết lập Ngưỡng Động (Threshold) ]
                            \tau = \mu_{depth} + \alpha * \sigma_{depth}
                                          │
                                          ▼
                       [ Hậu xử lý (Sàng lọc khoảng cách tối thiểu) ]
                          (Gộp các tiểu phân đoạn quá ngắn bằng min_seg)
                                          │
                                          ▼
                     [ Danh sách Số lượng Câu thoại mỗi Phân đoạn ]
```

---

## 3. Các Công thức Toán học Chi tiết

### 3.1 Biểu diễn Văn bản Bag-of-Words (BoW)
Với mỗi câu thoại $U_i$, chúng ta chuẩn hóa văn bản $T(U_i)$ bằng cách chuyển về dạng viết thường, loại bỏ các ký tự đặc biệt ngữ pháp và các từ dừng tiếng Việt (sử dụng thư viện `stopwordsiso`).
Vector tần suất từ vựng $b_i$ được biểu diễn dưới dạng:
$$b_i = \{w: \text{tf}(w, U_i)\}$$

### 3.2 Độ tương đồng Cosine giữa các khối (Block-level Cosine Similarity)
Nhằm tăng tính ổn định về mặt ngữ cảnh, thay vì tính tương đồng trực tiếp giữa hai câu thoại đơn lẻ cạnh nhau, ta gộp nhóm các câu thoại xung quanh biên thành hai khối trái $B1_i$ và phải $B2_i$ có độ dài $k$ (`block_size`):

- Khối bên trái tại vị trí $i$:
  $$B1_i(w) = \sum_{j=\max(1, i-k+1)}^{i} \text{tf}(w, U_j)$$
- Khối bên phải tại vị trí $i$:
  $$B2_i(w) = \sum_{j=i+1}^{\min(n, i+k)} \text{tf}(w, U_j)$$

Độ tương đồng Cosine $S_i$ tại biên $i$ (khoảng trống giữa câu thoại $U_i$ và $U_{i+1}$) được xác định bởi:
$$S_i = \text{Cosine}(B1_i, B2_i) = \frac{\sum_{w} B1_i(w) \cdot B2_i(w)}{\sqrt{\sum_{w} B1_i(w)^2} \cdot \sqrt{\sum_{w} B2_i(w)^2}}$$
Trả về chuỗi độ tương đồng dài $n-1$: $S = [S_0, S_1, \dots, S_{n-2}]$.

### 3.3 Điểm dốc sâu chiều sâu đa tỷ lệ (Multi-Scale Depth Score)

Tại mỗi vị trí biên thứ $i$, nếu độ tương đồng $S_i$ là một điểm cực tiểu cục bộ (valley), nó đại diện cho một điểm chuyển giao tiềm năng của chủ đề. Để đo lường mức độ "sâu" của thung lũng tương đồng này, ta quét sang hai phía trái và phải để tìm kiếm đỉnh tương đồng cục bộ cao nhất trong phạm vi bán kính tìm kiếm $r$:

- **Đỉnh cực đại phía trái (Left Peak):**
  $$p_L(i, r) = \max \{S_{j} \mid \max(1, i-r) \le j \le i\}$$
  được tìm bằng cách dò ngược từ $i-1$ về phía trước, giữ nguyên giá trị đỉnh nếu độ tương đồng tăng dần và chặn đứng nếu có xu hướng đi xuống trở lại.
  
- **Đỉnh cực đại phía phải (Right Peak):**
  $$p_R(i, r) = \max \{S_{j} \mid i \le j \le \min(n-1, i+r)\}$$
  được tìm tương tự bằng cách dò tiến từ $i+1$ về phía sau.

Điểm dốc sâu (Depth Score) tại vị trí $i$ ứng với bán kính $r$ là trung bình cộng khoảng cách từ hai đỉnh tới thung lũng:
$$D_r(i) = \frac{1}{2} \left[ (p_L(i, r) - S_i) + (p_R(i, r) - S_i) \right]$$

### 3.4 Chuẩn hóa Thang đo (Normalization)
Mỗi bán kính $r$ sẽ sinh ra một thang đo Depth Score có phân phối biên độ khác nhau (bán kính lớn thường cho dốc sâu cao hơn). Để tổng hợp khách quan, chúng ta cần đưa chúng về cùng một hệ quy chiếu bằng phân phối chuẩn hóa **Z-Score**:
$$\hat{D}_r(i) = \frac{D_r(i) - \mu(D_r)}{\sigma(D_r) + \epsilon}$$
Trong đó:
- $\mu(D_r)$ và $\sigma(D_r)$ lần lượt là trung bình và độ lệch chuẩn của mảng điểm dốc tương ứng tại bán kính $r$.
- $\epsilon = 10^{-10}$ là hằng số chống chia cho $0$.

*(Hệ thống cũng hỗ trợ chuẩn hóa **Min-Max** tùy biến thông qua cấu hình `normalize="minmax"`)*

### 3.5 Tích hợp Đa tỷ lệ (Multi-Scale Aggregation)
Với tập hợp các bán kính mặc định $R = \{3, 5, 10, 15, 20\}$, tổng phổ chiều sâu hợp nhất $\bar{D}(i)$ thu được bằng cách tính trung bình cộng (Mean) hoặc lấy giá trị lớn nhất (Max) các điểm dốc đã chuẩn hóa tại vị trí $i$:
$$\bar{D}(i) = \frac{1}{|R|} \sum_{r \in R} \hat{D}_r(i)$$

### 3.6 Xác định Ngưỡng động (Dynamic Thresholding)
Một biên phân đoạn $i$ được coi là ứng viên chuyển đổi chủ đề tiềm năng nếu tổng phổ dốc sâu vượt qua ngưỡng thống kê:
$$\tau = \mu(\bar{D}) + \alpha \cdot \sigma(\bar{D})$$
Trong đó $\alpha$ là hệ số điều chỉnh độ nhạy biên (mặc định $\alpha = 1.5$). Danh sách biên ứng viên được chọn:
$$C = \{ i \mid \bar{D}(i) > \tau \}$$

### 3.7 Hậu xử lý: Gộp Tiểu phân đoạn (Post-Processing: Small Segment Merger)
Để tránh hiện tượng phân đoạn quá mức (**over-segmentation**), thuật toán áp đặt số câu thoại tối thiểu cho một chủ đề dưới dạng tỉ lệ:
$$\text{min\_seg} = \max\left(2, \lfloor n \cdot \omega \rfloor\right)$$
Trong đó $\omega$ (`min_segment_ratio`) mặc định là $0.1$ (10% tổng số câu thoại hội thoại).

Nếu tồn tại phân đoạn $s_k$ có độ rộng nhỏ hơn $\text{min\_seg}$, hệ thống thực hiện sáp nhập thông minh dựa trên độ dốc biên:
- Sắp xếp các tiểu phân đoạn theo độ dài tăng dần.
- Giữa ranh giới bên trái và bên phải của tiểu phân đoạn ngắn nhất, thực hiện xóa bỏ (pop) biên có Depth Score $\bar{D}$ thấp hơn để sáp nhập nó vào phân đoạn lân cận vững mạnh hơn.

---

## 4. Thuật toán Chi tiết (Algorithm Steps)

Dưới đây là mô tả thuật toán bằng mã giả mô phỏng cấu trúc hoạt động trong lớp `SlidingTextTilingSegmenter`:

```python
def predict(utterances, block_size, radii, alpha, min_segment_ratio):
    n = len(utterances)
    if n == 0: return []
    if n == 1: return [1]
    
    # Bước 1 & 2: Trích xuất BoW và tính toán Cosine Similarity song song
    sim_scores = calculate_block_cosine_similarities(utterances, block_size)
    if len(sim_scores) < 2:
        return [n]
    
    # Bước 3 & 4: Tính toán dốc sâu đa tỷ lệ và chuẩn hóa Z-score
    all_normalized_depths = []
    for r in radii:
        depth_r = compute_single_scale_depth(sim_scores, radius=r)
        norm_depth_r = zscore_normalize(depth_r)
        all_normalized_depths.append(norm_depth_r)
        
    # Bước 5: Tổng hợp tích hợp các chiều sâu (Mean Aggregation)
    aggregated_depth = mean(all_normalized_depths, axis=0)
    
    # Bước 6: Đặt ngưỡng lọc ứng viên biên
    threshold = mean(aggregated_depth) + alpha * std(aggregated_depth)
    candidates = [(i, aggregated_depth[i]) for i in range(len(aggregated_depth)) if aggregated_depth[i] > threshold]
    
    # Lưu vết và thêm điểm chốt chặn kết thúc cuộc hội thoại
    boundaries = [c[0] for c in candidates]
    boundaries.append(n - 1)
    boundaries = sorted(list(set(boundaries)))
    
    # Bước 7: Áp dụng ràng buộc kích thước tối thiểu để gộp mảnh nhỏ
    min_seg = max(2, int(n * min_segment_ratio))
    if min_seg > 2 and len(boundaries) > 2:
        boundaries = merge_small_segments(boundaries, aggregated_depth, n, min_seg)
        
    # Chuyển đổi định dạng danh sách ranh giới thành khoảng cách phân đoạn
    segments = []
    prev = -1
    for b in boundaries:
        segments.append(b - prev)
        prev = b
    return segments
```

---

## 5. Đánh giá Ưu và Nhược điểm

### 5.1 Ưu điểm vượt trội
- **Phản ứng linh hoạt với độ dài phân khúc khác nhau:** Khác với TextTiling thông thường (chỉ hiệu quả khi kích thước bài nói tương đồng), Sliding TextTiling có thể phát hiện đồng thời cả các câu hỏi đáp nhanh (nhớ $r=3$) lẫn các chương thuyết trình dài (nhớ $r=20$).
- **Hạn chế nhiễu cục bộ tốt:** Quá trình chuẩn hóa Z-score và lấy trung bình đa tỷ lệ hoạt động như một bộ lọc thông thấp (low-pass filter), làm phẳng các dao động nhỏ vô nghĩa từ các từ bộc phát tự nhiên trong văn bản hội thoại (ASR transcripts).
- **Phù hợp tuyệt vời với Tiếng Việt:** Kết hợp tiền xử lý mượt mà và loại bỏ từ dừng tự động, thích ứng tốt với đặc thù hội thoại giao tiếp của người Việt.

### 5.2 Nhược điểm / Hạn chế
- **Tính phi tuyến tính thấp:** Do dựa trên sự gắn kết từ vựng cục bộ tuần tự (lexical cohesion), thuật toán sẽ hoạt động kém hiệu quả hơn trong các cuộc họp có cấu trúc thảo luận chồng chéo kéo dài (quay lại chủ đề cũ liên tục). Lúc này các mô hình học máy cấp cao như **1DOD** (`bamibert_1dod`) thể hiện ưu thế hơn nhờ cơ chế hiểu ngữ cảnh ngữ nghĩa sâu.

---
## 6. Thông số mặc định (Default Parameters)

Bộ thông số của `SlidingTextTilingSegmenter` được cố định dựa trên kết quả tuning trên dev set của `meeting_committee` dataset (6 mẫu), sử dụng combined score $P_k + (1 - F_1)$:

- `block_size` = 2
- `radii` = [3, 5, 10, 15, 20]
- `alpha` = 1.5
- `min_segment_ratio` = 0.1

Các thông số này được dùng chung cho mọi dataset, không có bước `fit()` hay grid search tại inference.

### 1.2 Sliding Window & Max-Voting (Asthana et al., Microsoft 2025)
Trong bài báo khoa học *“Summaries, Highlights, and Action Items: Design, Implementation and Evaluation of an LLM-powered Meeting Recap System” (Section 3.2.2)*, nhóm nghiên cứu sử dụng mô hình Transformer (BART) kết thuật toán trượt cửa sổ (sliding window) kích thước $30$ câu hội thoại (utterances), sải bước $10$ câu (stride) để phân đoạn các văn bản hội thoại dài. Sau đó họ áp dụng phương pháp bỏ phiếu cực đại (**max-voting**) để hợp nhất các ranh giới dự đoán từ các cửa sổ trượt trùng lặp chéo lên nhau.

### 1.3 Ý Tưởng Cốt Lõi Của Multi-Scale Sliding TextTiling
Hội thoại thực tế (đặc biệt là cuộc họp, thảo luận nhóm) thường chứa các chủ đề lồng nhau hoặc các khoảng chuyển dịch nhanh (micro-shift) nằm trong một chủ đề vĩ mô (macro-topic). 
- Một cửa sổ thu hẹp (**radius nhỏ**) sẽ nhạy bén với các thay đổi chủ đề ngắn hạn nhưng dễ bị nhiễu.
- Một cửa sổ mở rộng (**radius lớn**) nắm bắt tốt cấu trúc vĩ mô nhưng dễ bỏ qua các ranh giới chuyển giao cục bộ quan trọng.

Để giải quyết mâu thuẫn này mà không làm tăng độ phức tạp tính toán của các mô hình học sâu, giải pháp **Multi-Scale Sliding TextTiling** thực hiện **phân tích độ sâu đa chiều (multi-scale depth analysis)**. Thay vì dùng một ban kính đơn lẻ, thuật toán tính toán các điểm độ sâu (depth scores) đồng thời trên nhiều bán kính tìm đỉnh khác nhau ($R = [3, 5, 10, 15, 20]$), chuẩn hóa chúng, rồi tổng hợp (aggregate) lại tạo thành một đồ thị độ sâu hợp nhất mạnh mẽ trước nhiễu.

---

## 2. Kiến Trúc Chi Tiết Hệ Thống (Architectural Pipeline)

Luồng xử lý của hệ thống `SlidingTextTilingSegmenter` trải qua 7 bước tuần tự và chặt chẽ:

```
                  ┌──────────────────────────────┐
                  │ 1. Tiền xử lý hội thoại      │ (Loại ký tự đặc biệt, lọc stopword tiếng Việt)
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │ 2. Bag-of-Words (BoW)        │ (Mỗi utterance được biểu diễn dạng Vector Tần suất)
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │ 3. Tính Cosine Similarity    │ (Similarity vector giữa các khối kề nhau)
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │ 4. Phân tích độ sâu đa scale │ (Tính toán depth profile với các bán kính r ∈ R)
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │ 5. Chuẩn hóa & Hợp nhất      │ (Z-Score/MinMax normalization & Mean/Max aggregation)
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │ 6. Lọc ngưỡng động (Alpha)   │ (Tính ngưỡng μ + α * σ để chọn ranh giới)
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │ 7. Hậu xử lý (Merge Small)   │ (Áp dụng min_segment_ratio để tối ưu phân mảnh)
                  └──────────────────────────────┘
```

---

## 3. Hệ Thống Công Thức Toán Học & Thuật Toán (Mathematical Formulations)

### 3.1 Biểu Diễn Văn Bản Dạng Vector Từ Vựng (Bag-of-Words)
Với mỗi câu hội thoại (utterance) $u_t$ trong danh sách cuộc hội thoại $U = \{u_1, u_2, ..., u_n\}$, ta tiến hành làm sạch, loại bỏ dấu câu, chuyển thành chữ thường, và lọc bỏ các từ dừng (stopwords) tiếng Việt dựa trên thư viện `stopwordsiso`. 

Biểu diễn Bag-of-Words của utterance $u_t$ là một tập các cặp từ và tần suất:
$$BOW(u_t) = \{ (w, f(w)) \mid w \in u_t \land w \notin Stopwords \}$$

### 3.2 Độ Tương Đồng Từ Vựng Khối (Cosine Similarity Over Block Window)
Để giảm nhiễu cục bộ và tăng độ mượt cho tín hiệu từ vựng, ta nhóm các vector từ vựng kề nhau thành hai khối liên tiếp (Trái và Phải) xung quanh vị trí ranh giới tiềm năng $i$ (nằm giữa $u_i$ và $u_{i+1}$). Độ rộng của khối được điều khiển bởi tham số `block_size` ($k$).

Vector tổng hợp cho Khối Trái ($B_1$) và Khối Phải ($B_2$) tại ranh giới thứ $i$ được xác định bởi:
$$B_1(i) = \sum_{j = \max(1, i - k + 1)}^{i} BOW(u_j)$$
$$B_2(i) = \sum_{j = i + 1 Min(n, i + k + 1)}^{n} BOW(u_j)$$

Trong đó, tần số của mỗi từ $w$ trong khối là tổng tần số xuất hiện của từ đó tại các câu trong khối tương ứng:
$$B_1(i)[w] = \sum_{j} f_{u_j}(w)$$

Độ tương đồng cosine giữa $B_1(i)$ và $B_2(i)$ tại ranh giới thứ $i$ được tính bằng công thức:
$$S(i) = \text{Cosine}(B_1(i), B_2(i)) = \frac{\sum_{w} B_1(i)[w] \cdot B_2(i)[w]}{\sqrt{\sum_{w} (B_1(i)[w])^2} \cdot \sqrt{\sum_{w} (B_2(i)[w])^2}}$$

Nếu mẫu số bằng $0$, $S(i) = 0.0$. Từ đó ta nhận được chuỗi điểm tương đồng: $S = [S_0, S_1, ..., S_{n-2}]$.

### 3.3 Điểm Độ Sâu Đơn Quy Mô (Single-Scale Depth Scores)
Tại mỗi điểm ranh giới thứ $i$, điểm độ sâu biểu thị khoảng sụt giảm độ tương đồng từ vựng so với hai đỉnh cao nhất gần nhất về bên trái và bên phải. Điểm cực tiểu sâu (valley) có độ tương đồng thấp hơn các đỉnh lân cận sẽ nhận được điểm độ sâu lớn, hứa hẹn là một điểm chuyển dịch đề tài.

Với một bán kính tìm kiếm đỉnh truyền thống (hay bán kính kiểm soát cục bộ) là $r$:
- **Tìm đỉnh bên trái cao nhất trong bán kính $r$**:
  $$S_{left\_peak}(i, r) = \max_{j \in [\max(1, i - r), i]} S(j)$$
  Với điều kiện chuỗi tương đồng từ $i$ ngược về trái phải đơn điệu tăng hoặc đạt đỉnh, tức là:
  $$S(j) \ge S(j+1) \quad \text{với mọi } j \text{ từ } i-1 \text{ về phía sau, dừng lại nếu } S(j) < S(j+1).$$

- **Tìm đỉnh bên phải cao nhất trong bán kính $r$**:
  $$S_{right\_peak}(i, r) = \max_{j \in [i, \min(n-1, i + r)]} S(j)$$
  Với điều kiện chuỗi tương đồng từ $i$ xuôi về phải phải đơn điệu tăng hoặc đạt đỉnh:
  $$S(j) \ge S(j-1) \quad \text{với mọi } j \text{ từ } i+1 \text{ xuôi về trước, dừng lại nếu } S(j) < S(j-1).$$

Điểm độ sâu tại quy mô bán kính $r$ được tính là:
$$D_r(i) = \frac{1}{2} \left[ S_{left\_peak}(i, r) + S_{right\_peak}(i, r) - 2S(i) \right]$$

### 3.4 Chuẩn Hóa Điểm Độ Sâu (Normalization)
Do các giá trị điểm độ sâu giữa các quy mô bán kính khác nhau có biên độ lệch nhau lớn (bán kính lớn thường tạo ra khoảng sụt giảm danh nghĩa lớn hơn), ta cần đưa chúng về cùng một hệ quy chiếu bằng bộ chuẩn hóa Z-Score (hoặc MinMax):

$$Z(D_r(i)) = \frac{D_r(i) - \mu(D_r)}{\sigma(D_r) + \epsilon}$$

Trong đó:
- $\mu(D_r)$ là trị trung bình của mảng độ sâu tại scale $r$.
- $\sigma(D_r)$ là độ lệch chuẩn của mảng độ sâu tại scale $r$.
- $\epsilon = 10^{-10}$ là hằng số chống chia cho $0$.

### 3.5 Hỗn Hợp Đa Quy Mô (Multi-Scale Aggregation)
Tổng hợp các tín hiệu độ sâu đã chuẩn hóa từ tất cả các bán kính trong tập hợp bán kính $R = \{r_1, r_2, ..., r_m\}$ để thu được đồ thị độ sâu hợp nhất bền vững (Multi-Scale Depth Profile):

$$\bar{D}(i) = \frac{1}{|R|} \sum_{r \in R} Z(D_r(i))$$

*(Lưu ý: Hệ thống cũng hỗ trợ phép toán `max` hoặc `sum` để tổng hợp, nhưng mặc định dùng trung bình `mean` để giữ tính ổn định tổng thể).*

### 3.6 Thiết Lập Ngưỡng Biên Động (Dynamic Thresholding)
Một ranh giới thứ $i$ được ghi nhận là một ứng viên đánh dấu ranh giới phân nhóm nếu điểm độ sâu tổng hợp vượt qua ngưỡng thống kê:

$$\text{Threshold} = \mu(\bar{D}) + \alpha \cdot \sigma(\bar{D})$$

Ranh giới hợp lệ: 
$$B_{candidates} = \{ i \mid \bar{D}(i) > \text{Threshold} \}$$

Trong đó, $\alpha$ là hệ số điều chỉnh độ nhạy (hyperparameter). $\alpha$ nhỏ hơn sẽ sinh ra nhiều phân nhánh, $\alpha$ lớn hơn sẽ lọc chặt chẽ hơn.

### 3.7 Hậu Xử Lý Tránh Phân Mảnh Quá Mức (Minimum Segment Resolution - Post-Processing)
Sau khi thu được các ranh giới tạm thời $B_{candidates} \cup \{n-1\}$, hệ thống thực thi thuật toán gộp khối kích thước bé nhằm đảm bảo phân mảnh không quá vụn vặt dựa trên tỷ lệ `min_segment_ratio` ($\gamma$):

$$\text{min\_seg} = \max(2, \lfloor n \cdot \gamma \rfloor)$$

Thuật toán duyệt tìm mọi phân đoạn có độ dài nhỏ hơn $\text{min\_seg}$:
1. Tìm phân đoạn ngắn nhất có kích thước nhỏ hơn `min_seg`. Giả sử phân đoạn đó nằm từ ranh giới biểu thị $b_{k-1}$ đến $b_k$.
2. Nếu nằm ở đầu cuộc hội thoại ($k=0$), ranh giới đầu tiên $b_0$ bị loại bỏ (gộp vào phân khúc sau).
3. Nếu nằm ở cuối cuộc hội thoại ($k=last$), ranh giới sát cuối bị loại bỏ (gộp vào phân khúc trước).
4. Nếu nằm ở giữa, thuật toán so sánh điểm độ sâu của ranh giới trái $b_{k-1}$ và ranh giới phải $b_k$. Ranh giới có điểm độ sâu thấp hơn (biểu diễn sự chuyển dịch chủ đề yếu hơn) sẽ bị hủy bỏ (pop), giữ lại ranh giới mạnh hơn nhằm tối ưu hóa tính gắn kết chủ đề.
5. Lặp lại quá trình tới khi không còn mảnh hội thoại nào vi phạm điều kiện kích thước tối thiểu.

---

## 4. Phương Pháp Luận Đánh Giá Trên Tập Thử Nghiệm (Experimental Evaluation)

Bộ tham số mặc định của `SlidingTextTilingSegmenter` được chọn dựa trên tuning trên dev set của `meeting_committee` (6 mẫu) với combined score:

$$\text{Combined Score} = P_k + (1.0 - F_1)$$

Các tham số này được cố định làm mặc định trong constructor và dùng chung cho mọi dataset. Khi đánh giá, không có bước `fit()` — chỉ chạy `predict()` duy nhất trên test set với tham số đã fixed.

| Tham số | Giá trị mặc định | Mô tả |
|---|---|---|
| `block_size` | 2 | Kích thước khối gộp utterance trước/sau |
| `radii` | [3, 5, 10, 15, 20] | Các bán kính tìm đỉnh đa quy mô |
| `alpha` | 1.5 | Hệ số ngưỡng động: $\mu + \alpha \cdot \sigma$ |
| `min_segment_ratio` | 0.1 | Tỉ lệ kích thước tối thiểu mỗi phân đoạn |

---

## 5. Đánh Giá Khách Quan Bản Chất Phương Pháp

| Tiêu Chí So Sánh | Phương Pháp Đơn Quy Mô (Single-scale) | Sliding TextTiling Đề Xuất (Multi-Scale) |
|---|---|---|
| **Độ nhạy phân giải** | Cố định bởi tham số bán kính đơn $r$ | Rất cao, quét đồng thời ở nhiều quy mô độ sâu ($R$) |
| **Khả năng triệt tiêu nhiễu** | Kém, dễ bị phân đoạn sai ở cuộc thoại ngắn | Xuất sắc nhờ quá trình chuẩn hóa Z-Score và tính trung bình độ sâu thích ứng |
| **Hậu xử lý kích thước** | Thường không có | Có cơ chế gộp phân đoạn yếu thông minh dựa trên dốc chiều sâu |
| **Vận hành trên dữ liệu tiếng Việt** | Không tự động tối ưu hóa biệt lập | Xuất sắc nhờ kết hợp làm sạch từ vựng tiếng Việt, hạ từ dừng và bộ lọc đa quy mô |
| **Độ ổn định chỉ số $P_k$** | Thấp và dễ dao động | Rất cao (ổn định nhất trong phân lớp không giám sát) |

Multi-Scale Sliding TextTiling chứng minh tính năng thực tiễn vượt trội khi vận hành trực tiếp (production inference) trên các tệp dữ liệu hội thoại dài thực tế như cuộc họp AMI, ICSI hay Alimeeting, giúp thiết lập chân đế phân đoạn vững chắc trước khi chuyển giao các khối nội dung sang cho mô hình ViT5 tóm tắt và mô hình BARTpho đặt tiêu đề.
Sau khi phân đoạn, các phân đoạn (segments) được cấu tạo trực tiếp thành các **Chapter** lồng kép trong cấu trúc Hierarchical giúp Con người/Agent nhanh chóng định vị mục tiêu hiệu quả cao nhất.
