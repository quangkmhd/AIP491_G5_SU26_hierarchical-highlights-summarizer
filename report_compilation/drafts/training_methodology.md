# Phương Pháp Luận & Kiến Trúc Huấn Luyện (Training Summarization & Titling)

Bộ tài liệu này chi tiết hóa phương pháp luận (**Methodology**), sơ đồ kiến trúc (**Architecture**), các công thức toán học (**Formulas**) và kỹ thuật tối ưu hóa trong quá trình huấn luyện hai thành phần tạo sinh cốt lõi của hệ thống DTS-TSL:
1. **Vietnamese Chunk Summarizer**: Bộ tóm tắt phân đoạn hội thoại ngắn 8 câu (sử dụng nền tảng `ViT5-base`).
2. **Vietnamese Topic Segment Titler**: Bộ tạo tiêu đề chủ đề cấp cao từ các câu tóm tắt thành phần (sử dụng nền tảng `BARTpho-syllable-base`).

---

## 1. Bản Chất Phương Pháp Luận (Methodological Approach)

Trong các cuộc hội thoại dài (như cuộc họp, bài giảng, hay hội thoại chat chăm sóc khách hàng), việc sinh tóm tắt hoặc sinh tiêu đề trích đoạn trực tiếp từ toàn bộ ngữ cảnh gặp phải ba rào cản kỹ thuật lớn:
- **Quá tải ngữ cảnh (Context Bloating)**: Chiều dài chuỗi đầu vào vượt quá giới hạn thiết kế của cơ chế tự chú ý (Self-Attention) trong các kiến trúc Transformer truyền thống (thường giới hạn ở $512$ hoặc $1024$ tokens).
- **Trôi lệch tập trung (Focus Drift)**: Các mô hình Generative lớn khi xử lý văn bản hội thoại rườm rà dễ sinh thông tin sai lệch (hallucination) hoặc bỏ sót các chi tiết mịn ở giữa cuộc trao đổi.
- **Tốn kém tài nguyên**: Gọi các LLM siêu tham số qua API hoặc chạy GPU trên máy local với ngữ cảnh cực lớn có độ trễ cao và chi phí lớn.

Để giải quyết triệt để rào cản này, hệ thống áp dụng phương pháp luận **Tóm Tắt Cuộn Dưới-Lên (Bottom-Up Roll-up Summarization)**:
1. **Phân rã thô**: Chia nhỏ các đoạn hội thoại dài thuộc mỗi phân hạt chủ đề thành các khối nhỏ độc lập có kích thước cố định cố định là $8$ lượt thoại (8-Utterance Blocks).
2. **Tóm tắt song song (Chunk Summarization)**: Sử dụng mô hình `ViT5-base` đã tinh chỉnh để tóm tắt cực nhanh và sắc nét từng khối 8 câu thoại thành một câu tóm tắt cô đọng (dưới dạng câu đơn ngữ pháp chuẩn).
3. **Tổng hợp dồn dịch (Topic Titling)**: Chuỗi các câu tóm tắt khối của một chủ đề được xếp chồng theo trình tự thời gian và đưa vào mô hình `BARTpho-syllable-base` đã tinh chỉnh để tổng hợp ngữ cảnh rộng và sinh ra duy nhất một tiêu đề đại diện mang tính khái quát cao nhất.

### Sơ đồ kiến trúc luồng dữ liệu huấn luyện & suy luận:

```
                      [ Văn bản Hội thoại Gốc (Original Dialogue Stream) ]
                                               │
                                               ▼
                              [ Cơ chế Phân đoạn Chủ đề (DTS) ]
                         (Có thể dùng Heuristic/Sliding TextTiling...)
                                               │
                                               ▼
                               [ Tách các Phân đoạn Chủ đề ]
                                               │
                                               ▼
                         [ Cắt khúc 8-Utterance Blocks trong Chủ đề ]
                        - Block 1: U_1 đến U_8  ──► Định dạng "speaker: text"
                        - Block 2: U_9 đến U_16 ──► Định dạng "speaker: text"
                                               │
                                               ▼
                      ┌──────────────────────────────────────────────────┐
                      ▼                                                  ▼
             [ Huấn luyện / Suy luận ]                             [ Ghép nối ]
             [  ViT5 Chunk Summarizer ]                         Xếp chồng câu:
             - Prompt: "Tóm tắt: " + Block                 S_1 / S_2 / ... / S_m
             - Target: Câu tóm tắt chuẩn                                 │
             - Loss: Cross-Entropy Token                                 ▼
                      │                                        ┌───────────────────┐
                      ▼                                        ▼                   ▼
            [ Sinh ra chuỗi tóm tắt ]                   [ Huấn luyện / Suy luận ]
             (S_1, S_2, ..., S_m) ───────────────────►  [  BARTpho Topic Titler ]
                                                       - Prompt: "Tạo tiêu đề: " + S
                                                       - Target: Tiêu đề dài nhất y*
                                                       - Loss: Sequence NLL
                                                                 │
                                                                 ▼
                                                        [ Tiêu Đề Chủ Đề ]
                                                          (Topic Title)
```

---

## 2. Huấn Luyện Bộ Tóm Tắt Khối (Chunk Summarizer) với ViT5

### 2.1 Biểu diễn Toán học của Nhiệm vụ (Input/Target Representation)
Cho một khối hội thoại gồm 8 câu thoại $B = \{u_1, u_2, \dots, u_8\}$, trong đó mỗi câu thoại chứa thông tin người nói và văn bản nội dung $u_i = (s_i, t_i)$.
Văn bản đầu vào được định dạng theo cấu trúc chuỗi liên tục và gắn thêm chỉ dẫn tác vụ huấn luyện (instruction prompt anchor):

$$x = \text{"Tóm tắt: "} \mathbin{\Vert} \left[ \big(s_1 \mathbin{\Vert} \text{": "} \mathbin{\Vert} t_1\big) \mathbin{\Vert} \text{"\n"} \mathbin{\Vert} \dots \mathbin{\Vert} \big(s_8 \mathbin{\Vert} \text{": "} \mathbin{\Vert} t_8\big) \right]$$

Trong đó ký hiệu $\mathbin{\Vert}$ biểu diễn phép nối chuỗi (string concatenation). 

Mục tiêu của mô hình sinh chuỗi Seq2Seq là ước lượng phân phối xác suất có điều kiện của chuỗi tóm tắt phân đoạn đích $Y = (y_1, y_2, \dots, y_L)$:

$$P(Y \mid x) = \prod_{j=1}^{L} P(y_j \mid y_{<j}, x)$$

### 2.2 Hàm Mục tiêu Huấn luyện (Loss Function)
Trong quá trình Fine-tuning mô hình `VietAI/vit5-base-vietnews-summarization`, chúng tôi tối ưu cực tiểu hóa hàm mất mát Cross-Entropy (Negative Log-Likelihood) trên tập dữ liệu gồm $N$ mẫu huấn luyện:

$$\mathcal{L}_{\text{summarize}}(\theta) = -\frac{1}{N} \sum_{i=1}^{N} \sum_{j=1}^{L_i} \log P_{\theta}(y_{i, j} \mid y_{i, <j}, x_i)$$

Trong đó $\theta$ biểu diễn toàn bộ trọng số mạng nơ-ron của mô hình ViT5.

### 2.3 Giải quyết Lỗi Tokenizer đặc thù trong Transformers
Một trong những bổ sung kỹ thuật quan trọng nhất trong codebase của chúng tôi để cứu vãn hệ thống khỏi lỗi phân luồng của thư viện Hugging Face `transformers==5.5.0` (trong việc tương tác với Unigram SentencePiece của ViT5) là giải pháp **Chế tác Tokenizer thủ công**.

*   **Hiện tượng lỗi**: Lớp `T5Tokenizer.__init__` chuyển một đối tượng `dict` trực tiếp tới lớp biên dịch Rust `tokenizers.Unigram`, sinh ra lỗi nghiêm trọng loại dữ liệu `TypeError: argument 'vocab': 'dict' object cannot be converted to 'Sequence'`.
*   **Giải pháp phương pháp luận**: Đọc trực tiếp bộ từ vựng nhị phân gốc từ tệp `spiece.model` của mô hình nền, giải mã thành danh sách tuple gồm `(token_string, score_float)` – định dạng chính xác mà bộ giải nén Unigram mong đợi.
*   **Mã hóa Kích thước Embedding Toán học**:
    Kích thước bảng nhúng của ViT5 được cấu hình cố định là:
    
    $$V_{\text{embed}} = 36096$$
    
    Tuy nhiên, từ vựng cơ sở từ tệp SentencePiece là $36000$ tokens. Để đảm bảo tính đồng bộ không gian toán học và tránh lỗi sụt lệch kích dạng (out-of-bound errors), chúng tôi bắt buộc phải khóa tham số định danh bổ sung:
    
    $$N_{\text{extra\_ids}} = 96 \implies V = 36000 + 96 = 36096$$
    
    Sử dụng bất kỳ giá trị nào khác (ví dụ mặc định của T5 là $100$ bổ sung $\implies 36100$) sẽ khiến chiều rộng tokenizer lệch sóng với chiều rộng ma trận nhúng trọng số của GPU, gây sập mô hình khi nạp.

### 2.4 Siêu tham số Huấn luyện ViT5 (Hyperparameters)
| Siêu tham số (Hyperparameter) | Giá trị (Value) | Giải thích kỹ thuật |
|---|---|---|
| **Base Model** | `VietAI/vit5-base-vietnews-summarization` | 226M tham số, cấu hình T5, đã được tiền huấn luyện sâu sắc về tóm tắt tiếng Việt. |
| **Learning Rate** | $3 \times 10^{-4}$ | Tốc độ hội tụ cao đặc trưng giúp các mô hình dòng T5 tối ưu hóa nhanh hơn đối với dữ liệu trích thảo luận. |
| **Batch Size hiệu dụng** | $32$ | Kết hợp Batch Size mỗi GPU là $2$ và số bước tích lũy vi phân (Gradient Accumulation Steps) là $16$. |
| **Max Input Length** | $512$ tokens | Bảo đảm không có sự mất mát thông tin ngữ cảnh đầu vào (chỉ có dưới 0.01% số khối 8 câu trong dữ liệu vượt quá ngưỡng này). |
| **Max Target Length** | $128$ tokens | Chặn trên an toàn cho các câu tóm tắt cô đọng mà không làm loãng trọng số câu. |
| **Early Stopping** | Kiên nhẫn 3 bước kiểm thử | Tự động hạ màn huấn luyện khi điểm sinh học tự nhiên `Rouge-L` trên tập Validate ngừng tăng trưởng để tránh Overfitting. |

---

## 3. Huấn Luyện Bộ Tạo Tiêu Đề (Topic Segment Titler) với BARTpho

### 3.1 Nén dồn Ngữ cảnh & Giới hạn Biên ký tự (Context Compression)
Khi các câu tóm tắt cục bộ $\{S_1, S_2, \dots, S_m\}$ đã được tạo sinh cho toàn bộ vùng chủ đề thứ $k$, chúng được kết hợp lại để làm đầu vào cho mô hình tạo tiêu đề:

$$X_{\text{title}} = \text{"Tạo tiêu đề: "} \mathbin{\Vert} \big(S_1 \mathbin{\Vert} \text{" / "} \mathbin{\Vert} S_2 \mathbin{\Vert} \dots \mathbin{\Vert} a_m\big)$$

Nhằm bảo vệ bộ đệm tự chú ý của kiến trúc BARTpho (vốn vận hành tối ưu ở độ dài trung bình), chúng tôi giới hạn chiều dài ký tự đầu vào ở ngưỡng cố định:

$$L_{\text{char\_max}} = 1500 \text{ characters}$$

Nếu chuỗi vượt quá giới hạn, hệ thống sẽ thực hiện trích xuất lát cắt từ phía bên phải (right-truncation) để giữ lại thông tin thảo luận cuối cùng:

$$X_{\text{title\_truncated}} = X_{\text{title}}[-1500:]$$

Cách xử lý này dựa trên luận điểm thực tế rằng: trong hội thoại, phần tổng kết hoặc kết luận thường nằm ở các câu thoại cuối của một chủ đề lớn, việc ưu tiên giữ lại các khối tóm tắt cuối sẽ gia tăng chất lượng tiêu đề sinh ra.

### 3.2 Chiến lược Lựa chọn Tiêu đề Đích Tối ưu (Dynamic Target Selection)
Hồ sơ dữ liệu huấn luyện (như `Alimeeting4MUG_vi`) được gán nhãn thủ công bới nhiều kiểm định viên, mang lại tập hợp nhiều ứng viên tiêu đề khả thi cho cùng một phân vùng thảo luận: $C = \{c_1, c_2, \dots, c_p\}$.

Thay vì chọn ngẫu nhiên gây nhiễu cho mạng nơ-ron sinh chữ, chúng tôi tối ưu hóa quá trình học bằng cách chọn **tiêu đề dài nhất và mang lượng thông tin ngữ nghĩa phong phú nhất** dựa vào số lượng từ đơn phân tách bởi khoảng trắng (whitespace tokens):

$$y^* = \arg\max_{c \in C} \text{Count}_{\text{words}}(c)$$

Tiêu đề $y^*$ đại diện cho mục tiêu học tập (training target) có độ bao phủ ngữ nghĩa cao nhất.

### 3.3 Hàm Đánh giá Đa Tham Chiếu (Multi-Reference RougeMax Evaluation)
Vì tiêu đề mang tính chủ quan cao, việc so khớp nghiêm ngặt đầu ra dự đoán $P$ của mô hình với chỉ một tiêu đề đích duy nhất sẽ làm méo mó kết quả đánh giá thực tế (làm giảm thấp điểm số ROUGE một cách oan uổng). 
Phương pháp luận của chúng tôi triển khai hệ mét **RougeMax**: Đo lường ROUGE độc lập giữa văn bản dự đoán và từng ứng viên do con người gắn nhãn, sau đó lấy giá trị cực đại để thu hồi độ chính xác chân thực:

$$\text{Rouge1}_{\text{Max}}(P, C) = \max_{c \in C} \text{ROUGE-1}(P, c)$$

$$\text{Rouge2}_{\text{Max}}(P, C) = \max_{c \in C} \text{ROUGE-2}(P, c)$$

$$\text{RougeL}_{\text{Max}}(P, C) = \max_{c \in C} \text{ROUGE-L}(P, c)$$

Công thức này loại bỏ sự thiên kiến cá nhân của người dán nhãn đơn lẻ, cho phép mô hình tạo tiêu đề đa dạng phong cách mà vẫn đạt điểm đánh giá khách khoa học.

### 3.4 Siêu tham số Huấn luyện BARTpho
| Siêu tham số (Hyperparameter) | Giá trị (Value) | Giải thích kỹ thuật |
|---|---|---|
| **Base Model** | `vinai/bartpho-syllable-base` | 226M tham số, kiến trúc BART tối ưu hóa sâu sắc cho cấu tạo âm tiết tiếng Việt. |
| **Learning Rate** | $5 \times 10^{-5}$ | Thấp hơn so với ViT5, giúp bảo vệ tính ổn định của cơ chế tự chú ý trên kiến trúc BARTpho. |
| **Batch Size hiệu dụng** | $64$ | Kết hợp Batch Size mỗi GPU là $4$ và số bước tích lũy vi phân (Gradient Accumulation Steps) là $16$. |
| **Max Input Length** | $1024$ tokens | Chiều dài token tối đa phục vụ tối ưu hóa học máy Seq2Seq. |
| **Max Target Length** | $64$ tokens | Tiêu đề là ngắn gọn, sắc sảo; việc thu hẹp chiều dài đầu ra giúp mô hình không sinh rườm rà. |

---

## 4. Phân đoạn Chủ đề (Segmentation) & Khía cạnh Huấn luyện

Khác với các bộ sinh văn bản trên, các thuật toán phân đoạn chủ đề (Dialogue Topic Segmentation - DTS) vận hành theo các cơ chế khác nhau:

- **Unsupervised Segmenters (`sliding_texttiling`)**:
  *   **Không cần huấn luyện**: Các phương pháp này là heuristic thuần túy, hoạt động dựa trên toán học tương đồng Cosine của tần suất từ (Bag-of-Words - BoW) và tính toán khoảng sâu dốc để tìm biên (Local Minima Depth Score Analysis). Do đó, chúng không yêu cầu quá trình huấn luyện máy học, giúp hệ thống triển khai tức thì trên bất kỳ máy chủ cấu hình thấp nào mà không tốn chi phí học nhãn.
- **Deep Learning Segmenters (`vibert_texttiling`, `bamibert_1dod`)**:
  *   **Sử dụng mô hình có sẵn**: Mô hình phân đoạn vector hóa `vibert` dựa trên các mô hình nhúng câu Transformer (như SBERT tiếng Việt) được tinh chỉnh để tối ưu khoảng cách ngữ nghĩa giữa các lượt thoại liên tiếp.
  *   **1DOD boundary classification (`bamibert_1dod`)**: Ứng dụng mô hình nơ-ron phát hiện biên giống phát hiện vật thể một chiều để gán nhãn nhị phân xem vị trí thoại $i$ có phải là điểm ranh giới chủ đề hay không.

Do đó, trọng tâm huấn luyện trong hệ thống này tập trung cao độ vào hai trục mô hình Seq2Seq tạo sinh (`ViT5` và `BARTpho`) để sinh tóm tắt và sinh tiêu đề chất lượng cao.

---

## 5. Bản Đồ Mã Nguồn Liên Quan Trực Tiếp (Direct Source Map)

*   `/src/train/chunk_summarizer/`:
    - `data_utils.py`: Chứa mã nguồn tải dữ liệu huấn luyện, định dạng khối 8 câu thoại và phương thức vượt lỗi Tokenizer của ViT5.
    - `finetune_chunk_summarizer.py`: Tập lệnh chạy huấn luyện cực thích nghi (Fine-tune) cho ViT5.
    - `evaluate_chunk_summarizer.py`: Bộ kiểm thử và so sánh chất lượng sinh tóm tắt của mô hình sau huấn luyện trên tập kiểm thử cô lập.
*   `/src/train/topic_titler/`:
    - `data_utils.py`: Bộ sưu tập nén dồn tóm tắt, lựa chọn tiêu đề huấn luyện dài tối đa và bộ phân chia dữ liệu.
    - `finetune_topic_titler.py`: Tập lệnh huấn luyện mô hình BARTpho tạo tiêu đề.
    - `evaluate_topic_titler.py`: Bộ kiểm thử nâng cao tích hợp hệ điểm **RougeMax**.
