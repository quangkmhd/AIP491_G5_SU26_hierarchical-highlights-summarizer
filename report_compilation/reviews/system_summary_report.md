# BÁO CÁO TỔNG HỢP HỆ THỐNG TÓM TẮT CUỘC HỌP PHÂN CẤP KẾT HỢP PHÂN ĐOẠN CHỦ ĐỀ
## (LLM-Powered Hierarchical Meeting Recap System with Topic Segmentation - DTS-TSL)

> **Ngày lập báo cáo**: 12 tháng 07, 2026  
> **Tác giả**: Antigravity AI Partner & Quang Nguyễn  
> **Ngữ cảnh hệ thống**: Phân hệ xử lý hội thoại dài tiếng Việt bằng thuật toán phân đoạn phi giám sát Sliding TextTiling và bộ đôi mô hình sinh tóm tắt phân cấp (ViT5-base & BARTpho-syllable-base) chạy cục bộ (on-device).

---

## 🧭 1. TỔNG QUAN HỆ THỐNG & KIẾN TRÚC (SYSTEM OVERVIEW & ARCHITECTURE)

Hệ thống cung cấp một giải pháp đầu-cuối (end-to-end) để xử lý các cuộc hội thoại cuộc họp tiếng Việt dài và nhiều nhiễu. Bằng cách kết hợp thuật toán phân đoạn chủ đề phi giám sát có độ chính xác cao (**Sliding TextTiling**) với quy trình tóm tắt cuộn phân cấp dưới-lên (**Bottom-Up Roll-up Summarization**), hệ thống giải quyết triệt để vấn đề quá tải ngữ cảnh (context bloating) và hiện tượng mất thông tin ở giữa văn bản (lost-in-the-middle) thường gặp trên các LLM thương mại lớn.

### 🏛️ Kiến trúc 6 Lớp Một Chiều (Strict 6-Layer Directional Architecture)
Hệ thống tuân thủ nghiêm ngặt mô hình kiến trúc phân tầng một chiều, được kiểm tra tự động qua AST code-scans để ngăn chặn các phụ thuộc chéo (circular dependencies):

```
Types ──► Config ──► Repo ──► Service ──► Runtime ──► UI
```

| Tầng (Layer) | Đường dẫn (Path) | Vai trò & Nhiệm vụ chính | Ràng buộc & Quy tắc biên |
| :--- | :--- | :--- | :--- |
| **Types** | `src/types/` | Định nghĩa các cấu trúc dữ liệu cơ sở như `Utterance`, `DialogueTranscript`, `HierarchicalRecap`. | **Tuyệt đối không import từ bất kỳ tầng nào khác.** |
| **Config** | `src/config/` | Chứa cấu hình tham số hệ thống (block size, radii, alpha, API ports) thông qua Pydantic Settings. | Chỉ được phép import `Types`. |
| **Repo** | `src/repo/` | Quản lý việc đọc/ghi dữ liệu, tải trọng số mô hình (ViT5, BARTpho, ViBERT) cục bộ. | Không chứa logic nghiệp vụ cấp cao. |
| **Service** | `src/service/` | Thực thi logic thuật toán phân đoạn (TextTiling), chunking và điều phối luồng (Orchestrator). | Phối hợp các Repo và Config để xử lý nghiệp vụ cốt lõi. |
| **Runtime** | `src/runtime/` | Cung cấp giao diện thực thi (giao thức CLI, web server API Fast HTTP, SSE streaming). | Khởi tạo các Service một cách lazy, đóng vai trò vỏ bọc runtime. |
| **UI** | `src/ui/` | Giao diện người dùng tương tác thời gian thực (Vanilla JS + HTML). | Chỉ giao tiếp với Runtime thông qua REST API hoặc SSE streams. |

---

## 📊 2. PHÂN ĐOẠN CHỦ ĐỀ HỘI THOẠI (DIALOGUE TOPIC SEGMENTATION - DTS)

Phân đoạn chủ đề hội thoại (DTS) có nhiệm vụ chia nhỏ một luồng hội thoại dài, liên tục thành các phân vùng ngữ nghĩa (topic segments) độc lập. Khác với tài liệu viết thông thường, hội thoại tự do không có ngắt trang, tiêu đề chương hay định dạng rõ ràng, đồng thời chứa nhiều từ thừa và có xu hướng lặp lại từ vựng lớn.

### 2.1. Bốn thuật toán phân đoạn được hỗ trợ

Hệ thống triển khai và đánh giá 4 thuật toán phân đoạn thuộc hai nhóm phương pháp luận:

1. **Unsupervised (Phi giám sát - Không cần huấn luyện)**:
   - **`nltk_texttiling`**: Sử dụng thư viện NLTK cổ điển. Hạn chế lớn là bộ tách từ gốc NLTK không tối ưu cho ngôn ngữ đơn âm tiết tiếng Việt.
   - **`sliding_texttiling`**: Thuật toán đa thang đo đề xuất của chúng tôi. Thay vì đo độ dốc sâu ở một kích thước cửa sổ cố định, thuật toán chạy song song nhiều bán kính trượt khác nhau để bắt được cả chuyển dịch chủ đề mịn (micro-shift) lẫn thô (macro-shift).

2. **Supervised (Có giám sát - Học sâu)**:
   - **`vibert_texttiling`**: Được chúng tôi tinh chỉnh (fine-tune) dựa trên phương pháp của Xing và Carenini (2021) [@Xing2021] trên tập huấn luyện (train set) của các bộ dữ liệu tiếng Việt thực nghiệm tương ứng. Mô hình thay thế vector BoW tĩnh bằng vector nhúng ngữ nghĩa dày đặc sinh ra từ mô hình `Sentence-BERT` (`models/vibert/cpt_3818.pth`).
   - **`bamibert_1dod`**: Được chúng tôi tinh chỉnh (fine-tune) dựa trên phương pháp phát hiện vật thể một chiều (1D Object Detection) của He và cộng sự (2025) [@He2025] trên tập huấn luyện (train set) của các bộ dữ liệu tiếng Việt thực nghiệm tương ứng, phân loại trực tiếp biên lượt thoại (`models/bamibert-1dod-vi-v1`).

---

### 2.2. Toán học chi tiết của giải thuật Multi-Scale Sliding TextTiling

```
[Utterances] ──► BoW extraction ──► Cosine Similarity ──► Multi-scale Depth [3,5,10,15,20] ──► Z-Score Norm ──► Mean Aggregation ──► Thresholding ──► Greedy Merge
```

#### Bước 2.2.1: Biểu diễn Bag-of-Words (BoW)
Với mỗi câu thoại $U_i$ trong danh sách hội thoại $U = \{u_1, u_2, ..., u_n\}$, hệ thống chuẩn hóa bằng cách loại bỏ ký tự đặc biệt, chuyển chữ thường và lọc stopword tiếng Việt:
$$b_i = \{w: \text{tf}(w, U_i)\}$$

#### Bước 2.2.2: Tính Cosine Similarity giữa các khối (Gap Cosine Similarity)
Tại mỗi ranh giới $i$ (nằm giữa câu thoại $U_i$ và $U_{i+1}$), hệ thống trượt một cửa sổ có bán kính $k$ (`block_size`) để gộp các câu thoại bên trái thành khối $B_1$ và bên phải thành khối $B_2$:
$$B_1(i)[w] = \sum_{j=\max(1, i-k+1)}^{i} \text{tf}(w, U_j)$$
$$B_2(i)[w] = \sum_{j=i+1}^{\min(n, i+k)} \text{tf}(w, U_j)$$

Tính toán Cosine Similarity $S_i$ tại biên $i$:
$$S_i = \text{Cosine}(B_1(i), B_2(i)) = \frac{\sum_{w} B_1(i)[w] \cdot B_2(i)[w]}{\sqrt{\sum_{w} (B_1(i)[w])^2} \cdot \sqrt{\sum_{w} (B_2(i)[w])^2}}$$

#### Bước 2.2.3: Điểm sâu thung lũng đa quy mô (Multi-Scale Depth Scoring)
Tại vị trí biên $i$, điểm dốc sâu (Depth Score) đại diện cho khoảng sụt giảm tương đồng từ vựng so với hai đỉnh lân cận cao nhất bên trái ($p_L$) và phải ($p_R$) trong phạm vi bán kính khảo sát $r$:
$$p_L(i, r) = \max \{S_{j} \mid \max(1, i-r) \le j \le i\}$$
$$p_R(i, r) = \max \{S_{j} \mid i \le j \le \min(n-1, i+r)\}$$

Điểm độ sâu tương ứng với quy mô $r$:
$$D_r(i) = \frac{1}{2} \left[ p_L(i, r) + p_R(i, r) - 2S_i \right]$$

#### Bước 2.2.4: Chuẩn hóa & Hợp nhất đa tỷ lệ (Normalization & Aggregation)
Hệ thống sử dụng các bán kính $R = \{3, 5, 10, 15, 20\}$. Do bán kính lớn có độ dốc danh nghĩa cao hơn, các mảng được đưa về cùng phân phối thông qua chuẩn hóa Z-Score trước khi tính trung bình cộng:
$$\hat{D}_r(i) = \frac{D_r(i) - \mu(D_r)}{\sigma(D_r) + \epsilon}$$
$$\bar{D}(i) = \frac{1}{|R|} \sum_{r \in R} \hat{D}_r(i)$$

#### Bước 2.2.5: Ngưỡng động & Hậu xử lý gộp phân đoạn (Dynamic Thresholding & Merge)
Ứng viên ranh giới được kích hoạt nếu vượt ngưỡng động:
$$\tau = \mu(\bar{D}) + \alpha \cdot \sigma(\bar{D}) \quad (\text{Mặc định } \alpha = 1.5)$$

Để loại bỏ hiện tượng phân mảnh quá vụn vặt, các phân đoạn có độ dài ngắn hơn tỉ lệ kích thước tối thiểu $\text{min\_seg} = \max(2, \lfloor n \cdot \gamma \rfloor)$ (với $\gamma = 0.1$) sẽ được gộp một cách tham lam vào phân đoạn lân cận bằng cách xóa bỏ biên có điểm dốc sâu $\bar{D}$ thấp hơn.

---

### 2.3. Kết quả thực nghiệm và bảng xếp hạng phân đoạn (DTS Benchmark)

Đánh giá benchmark được thực hiện trên 6 tập dữ liệu có độ dài và độ phức tạp đa dạng:
- **dialseg_711.json** (711 hội thoại AMI dịch Việt)
- **doc2dial.json** (3,270 hội thoại dịch vụ công)
- **meeting_ami.json** (137 cuộc họp nhóm dài, nhiều nhiễu)
- **meeting_committee.json** (36 cuộc thảo luận hội đồng chuyên sâu)
- **meeting_icsi.json** (59 cuộc họp học thuật cực dài)
- **tiage.json** (500 cuộc tư vấn y tế ngắn)

> [!NOTE]
> Chỉ số đánh giá gồm: **$P_k$** (xác suất lỗi phân đoạn, càng thấp càng tốt), **$W_d$** (WindowDiff, càng thấp càng tốt), và **$F_1$-score** (chỉ số đo trùng khớp biên, càng cao càng tốt).

#### Bảng xếp hạng tổng hợp (Overall Performance Ranking):

| Hạng | Thuật toán | Điểm Composite (↑) | Avg Pk (↓) | Avg WD (↓) | Avg F1 (↑) | Nhận xét hiệu năng thực tế |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **`sliding_texttiling`** (Ours) | **0.7052** | **0.5259** | **0.6531** | **0.6089** | Đạt Composite cao nhất, cân bằng tốt giữa độ chính xác biên và tối ưu hóa phân đoạn trong streaming. |
| **2** | **`bamibert_1dod`** | **0.4284** | 0.5288 | 0.6519 | 0.0360 | Phân đoạn tốt trên tập ngắn, kém ổn định trên họp dài. |
| **3** | **`nltk_texttiling`** | **0.3558** | 0.5441 | 0.7029 | 0.1108 | Thấp do không tối ưu hóa từ vựng và đặc thù ngôn ngữ tiếng Việt. |
| **4** | **`vibert_texttiling`** | **0.1929** | 0.5552 | 0.7991 | 0.2461 | Hiệu năng phân đoạn bị ảnh hưởng nhiều do trôi lệch ranh giới khi tính toán toàn cục trên văn bản dài. |

---

## 📝 3. HỒ SƠ HUẤN LUYỆN CÁC MÔ HÌNH TẠO SINH (GENERATIVE MODELS TRAINING)

Hệ thống tinh chỉnh đồng thời hai mô hình tạo sinh cục bộ để đảm bảo xử lý độc lập và nhanh chóng:
1. **Vietnamese Chunk Summarizer** (Tóm tắt khối 8 lượt thoại - mô hình nền `ViT5-base`).
2. **Vietnamese Topic Segment Titler** (Tạo tiêu đề chủ đề phân đoạn - mô hình nền `BARTpho-syllable-base`).

### 3.1. Vietnamese Chunk Summarizer (ViT5-base)

#### 3.1.1. Biểu diễn dữ liệu & Hàm mục tiêu
Với một khối gồm 8 câu thoại $B = \{u_1, u_2, \dots, u_8\}$ có định dạng `speaker: text`, chuỗi đầu vào $x$ được nối thêm token chỉ dẫn tác vụ `"Tóm tắt: "`:
$$x = \text{"Tóm tắt: "} \mathbin{\Vert} \left[ \big(s_1 \mathbin{\Vert} \text{": "} \mathbin{\Vert} t_1\big) \mathbin{\Vert} \text{"\n"} \mathbin{\Vert} \dots \mathbin{\Vert} \big(s_8 \mathbin{\Vert} \text{": "} \mathbin{\Vert} t_8\big) \right]$$

Mô hình học theo phương pháp Cross-Entropy (Negative Log-Likelihood) trên chuỗi nhãn mục tiêu sinh ra bởi mô hình Gemma giáo viên:
$$\mathcal{L}_{\text{summarize}}(\theta) = -\frac{1}{N} \sum_{i=1}^{N} \sum_{j=1}^{L_i} \log P_{\theta}(y_{i, j} \mid y_{i, <j}, x_i)$$

#### 3.1.2. Thống kê dữ liệu huấn luyện
- **Nguồn**: Trích xuất từ tập dữ liệu cuộc họp `Alimeeting4MUG_vi`.
- **Quy mô**: **28,079 cặp** câu song song `(block, summary)`. Phân chia theo mức độ cuộc họp (meeting-level group split) với tỷ lệ **90% train (265 cuộc họp, tương đương 25,051 mẫu)** và **10% validation (30 cuộc họp, tương đương 3,028 mẫu)**.
- **Phân phối độ dài**: Trung bình 137 tokens, phân vị 99 là 296 tokens. Chỉ có $0.01\%$ mẫu vượt ngưỡng 512 tokens. Do đó, thiết lập `max_input_length = 512` và `max_target_length = 128` là cực kỳ tối ưu.

> [!NOTE]
> **Đồng bộ kích thước Embedding**:
> Hệ thống sử dụng tham số `extra_ids = 96` để đồng bộ kích thước từ vựng của tokenizer khớp chính xác với ma trận nhúng trọng số thiết kế của ViT5 ($36,000 + 96 = 36,096$), tránh các lỗi tràn chỉ mục GPU (out-of-bounds).

#### 3.1.3. Tiến trình và Kết quả huấn luyện
Sử dụng phương pháp đánh giá 2 bước (kiểm tra nhanh trên 200 mẫu ngẫu nhiên mỗi epoch để tránh chậm trễ, và đánh giá toàn bộ 3,028 mẫu khi kết thúc huấn luyện):

| Epoch | Loss | R-1 | R-2 | R-L | Nhận xét thực nghiệm |
| :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | 0.9289 | 0.7017 | 0.4487 | 0.5190 | Bắt đầu huấn luyện |
| 3 | **0.7755** | 0.7168 | 0.4803 | 0.5418 | Đạt cực tiểu Loss (Bắt đầu overfit sau điểm này) |
| **6** | 0.8320 | 0.7316 | 0.4967 | **0.5559** | **Checkpoint tốt nhất** (Peak ROUGE-L) - Lưu lại |
| 10 | 1.1964 | 0.7352 | 0.4968 | 0.5545 | Overfit nặng, Loss tăng gấp đôi |

- **Kết quả trên tập Dev Benchmark (`dev_vi.jsonl` - 6,038 khối)**:
  - **Mean ROUGE-1**: **0.7265**
  - **Mean ROUGE-2**: **0.4854**
  - **Mean ROUGE-L**: **0.5486**
  *(Mô hình ViT5 khôi phục xuất sắc phong cách viết của giáo viên Gemma và cho tốc độ suy luận nhanh gấp hơn 100 lần).*

---

### 3.2. Vietnamese Topic Segment Titler (BARTpho-syllable-base)

#### 3.2.1. Nén dồn ngữ cảnh & Lựa chọn mục tiêu huấn luyện
Sau khi các câu tóm tắt khối $\{S_1, S_2, \dots, S_m\}$ được sinh ra bởi ViT5, chúng được ghép nối bằng dấu phân cách `" / "` để làm đầu vào cho BARTpho:
$$X_{\text{title}} = \text{"Tạo tiêu đề: "} \mathbin{\Vert} \big(S_1 \mathbin{\Vert} \text{" / "} \mathbin{\Vert} S_2 \mathbin{\Vert} \dots \mathbin{\Vert} S_m\big)$$

Để tránh tràn cửa sổ tự chú ý của BARTpho, hệ thống giới hạn chiều dài ở **1500 ký tự cuối** ($X_{\text{title}}[-1500:]$). Chiến lược cắt đuôi bên phải này giúp mô hình tập trung vào các kết luận chốt phương án thường nằm ở cuối cuộc thảo luận chủ đề.

Để tối ưu hóa mục tiêu huấn luyện từ nhãn của con người (chứa tối đa 3 tiêu đề tham chiếu do các kiểm định viên viết), hệ thống tự động chọn tiêu đề mang lượng ngữ nghĩa phong phú nhất (chứa nhiều từ đơn nhất):
$$y^* = \arg\max_{c \in C} \text{Count}_{\text{words}}(c)$$

#### 3.2.2. Đánh giá đa tham chiếu bằng chỉ số RougeMax
Tiêu đề cuộc họp mang tính chủ quan cao, vì vậy so khớp nhãn đơn lẻ dễ sinh ra đánh giá sai lệch. Hệ thống áp dụng **RougeMax**: Đo lường độc lập ROUGE giữa văn bản dự đoán và từng ứng viên tiêu đề do con người gán nhãn, sau đó lấy giá trị cực đại:
$$\text{RougeL}_{\text{Max}}(P, C) = \max_{c \in C} \text{ROUGE-L}(P, c)$$

- **Kết quả trên tập Dev Benchmark (`dev_vi.jsonl` - 736 phân đoạn chủ đề)**:
  - **Mean ROUGE-1**: **0.5304**
  - **Mean ROUGE-2**: **0.2837**
  - **Mean ROUGE-L**: **0.4443**
  - Trung vị độ dài tiêu đề dự đoán: **16 tokens**.

---

### 3.3. So sánh chi tiết hai mô hình tạo sinh

| Đặc trưng kỹ thuật | Chunk Summarizer | Topic Segment Titler |
| :--- | :---: | :---: |
| **Mô hình nền (Base Model)** | `VietAI/vit5-base-vietnews-summarization` | `vinai/bartpho-syllable-base` |
| **Kích thước tham số** | 226 triệu (T5 architecture) | 132 triệu (BART architecture) |
| **Cửa sổ ngữ cảnh (Context Window)** | 512 tokens | 1024 tokens |
| **Định dạng dữ liệu đầu vào** | Khối 8 câu thoại thô (`speaker: text`) | Các câu tóm tắt khối ghép nối bằng `" / "` |
| **Giới hạn đầu vào** | Truncation tại 512 tokens | Cắt lát 1500 ký tự cuối cùng từ phải qua |
| **Độ dài đầu ra tối đa** | 128 tokens | 64 tokens |
| **Nhãn tham chiếu kiểm thử** | 1 nhãn (Gemma-generated teacher) | 3 nhãn (Con người dán nhãn) |
| **Phương thức đánh giá** | Standard ROUGE | Multi-Reference RougeMax |
| **Kết quả ROUGE-1 / 2 / L (Dev)** | **0.7265 / 0.4854 / 0.5486** | **0.5304 / 0.2837 / 0.4443** |

---

## ⚡ 4. QUY TRÌNH LUỒNG DỮ LIỆU & SỰ KIỆN TRUYỀN PHÁT (WORKFLOWS & EVENT LIFECYCLE)

Hệ thống được thiết kế tối ưu hóa cho trải nghiệm người dùng cuối theo triết lý hiển thị sớm cấu trúc nội dung. Sơ đồ tuần tự các sự kiện truyền dữ liệu thời gian thực được thể hiện qua các mốc thời gian dưới đây:

### 4.1. Quy trình Async Streaming thời gian thực (SSE/NDJSON)

```
[Bắt đầu gửi] ──► Mốc 0: Gửi và duyệt Utterance đơn lẻ
                     │ Phát sự kiện: "utterance-accepted" (Xác nhận nhận câu thoại)
                     ▼
                 Mốc 1: Gom Transcript thô gửi sang Sliding TextTiling
                     │ 
                     ▼
                 Mốc 2: Tính toán xong ranh giới Sliding TextTiling
                     │ Phát sự kiện: "segment-closed" (Vẽ khung chương trên UI)
                     ▼
                 Mốc 3: Chia Chunk nhỏ, gọi ViT5 tóm tắt từng đoạn
                     │ Phát sự kiện: "chunk-closed" (Lấp đầy tóm tắt phân đoạn con)
                     ▼
                 Mốc 4: Sau khi toàn bộ các Chunk của một Segment đã có tóm tắt
                     │ Gộp các tóm tắt Chunk, gọi BARTpho viết tiêu đề chủ đề
                     │ Phát sự kiện: "title-emitted" (Cập nhật trực tiếp tiêu đề Card)
                     ▼
[Kết thúc]   ──► Mốc 5: Kết thúc toàn bộ tiến trình
                     │ Gom dữ liệu cấu trúc thành HierarchicalRecap
                     │ Phát sự kiện: "meeting-completed" (Đóng kết nối SSE)
```

### 4.2. Các sự kiện chuẩn của Orchestrator (`OrchestratorEvent`)

| Tên sự kiện (`type`) | Mô tả hành vi kích hoạt | Dữ liệu mang theo (`data`) |
| :--- | :--- | :--- |
| `utterance-accepted` | Phát ra cho mọi câu thoại từ câu thứ 2 trở đi để xác nhận việc hệ thống đã ghi nhận câu thoại. | `{"index": int, "speaker": str, "text": str}` |
| `segment-closed` | Phát ra ngay sau khi ranh giới phân mảnh của Sliding TextTiling được xác nhận. Giúp giao diện Front-end vẽ ngay khung Card của Segment. | `{"segment_id": str, "utterances_start": int, "utterances_end": int}` |
| `chunk-closed` | Xuất hiện ngay khi một nhóm khối (tối đa 8 thoại) hoàn tất và được sinh tóm tắt thành công bởi ViT5. | `{"chunk_id": str, "segment_id": str, "utterances_start": int, "utterances_end": int, "rolling_summary": str}` |
| `title-emitted` | Phát ra sau khi tất cả các chunk thuộc Segment đã hoàn tất tóm tắt và mô hình BARTpho viết xong tiêu đề. | `{"segment_id": str, "title": str}` |
| `meeting-completed` | Sự kiện cuối cùng báo hiệu toàn bộ tiến trình tóm tắt phân cấp cuộc họp hoàn tất. | `{"hierarchical_recap": HierarchicalRecap}` |