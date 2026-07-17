# Báo Cáo Huấn Luyện & Đánh Giá Các Mô Hình Tạo Sinh (Dialogue Topic Summarization & Topic Titling)

> **Ngày thực hiện**: 10 tháng 07, 2026  
> **Các thành phần**: 
> 1. **Vietnamese Chunk Summarizer** (Tóm tắt khối 8 lượt thoại - ViT5-base)
> 2. **Vietnamese Topic Segment Titler** (Tạo tiêu đề chủ đề hội thoại - BARTpho-base)  
> **Mục tiêu**: Xây dựng giải pháp tóm tắt cuộn từ dưới lên (Bottom-up Roll-up Summarization) cho các luồng hội thoại tiếng Việt dài mà không gặp rào cản quá tải ngữ cảnh (Context Bloating).

---

## 1. Phương Pháp Luận Tóm Tắt Cuộn Dưới - Lên (Bottom-up Roll-up Summarization)

Trong các cuộc hội thoại dài như họp nhóm, bài giảng hay tư vấn, độ dài luồng chữ thường vượt quá giới hạn thiết kế cửa sổ ngữ cảnh (Context Window) của các mô hình Transformer truyền thống ($512$ hoặc $1024$ tokens). Việc cố gắng nhồi nhét toàn bộ cuộc hội thoại vào một mô hình lớn gây sụt giảm mạnh chất lượng tóm tắt, xuất hiện thông tin giả mạo (hallucination) và tốn tài nguyên GPU.

Hệ thống của chúng tôi áp dụng phương pháp luận **Tóm Tắt Cuộn Dưới-Lên**:
1. **Phân rã thô**: Chia nhỏ các đoạn hội thoại dài thuộc mỗi phân hạt chủ đề thành các khối nhỏ độc lập có kích thước cố định là **8 lượt thoại (8-Utterance Blocks)**.
2. **Tóm tắt khối (Chunk Summarization)**: Sử dụng mô hình **ViT5-base** đã tinh chỉnh để tóm tắt cực nhanh từng khối 8 câu thoại thành một câu tóm tắt cô đọng (dưới dạng câu đơn chuẩn).
3. **Tổng hợp dồn dịch (Topic Titling)**: Chuỗi các câu tóm tắt khối của một chủ đề được xếp chồng theo trình tự thời gian (phân tách bởi dấu `" / "`) và đưa vào mô hình **BARTpho-base** đã tinh chỉnh để tổng hợp ngữ cảnh rộng và sinh ra duy nhất một tiêu đề đại diện mang tính khái quát cao nhất.

```
                      [ Văn bản Hội thoại Gốc (Original Dialogue Stream) ]
                                               │
                                               ▼
                              [ Cơ chế Phân đoạn Chủ đề (DTS) ]
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

### 2.1. Biểu diễn Dữ liệu đầu vào/đầu ra (Input/Target Representation)
Với mỗi khối hội thoại gồm 8 câu thoại $B = \{u_1, u_2, \dots, u_8\}$, trong đó mỗi câu thoại chứa thông tin người nói và văn bản nội dung $u_i = (s_i, t_i)$.
Văn bản đầu vào được định dạng theo cấu trúc chuỗi liên tục và gắn thêm chỉ dẫn tác vụ huấn luyện:
$$x = \text{"Tóm tắt: "} \mathbin{\Vert} \left[ \big(s_1 \mathbin{\Vert} \text{": "} \mathbin{\Vert} t_1\big) \mathbin{\Vert} \text{"\n"} \mathbin{\Vert} \dots \mathbin{\Vert} \big(s_8 \mathbin{\Vert} \text{": "} \mathbin{\Vert} t_8\big) \right]$$
*(Ký hiệu $\Vert$ biểu diễn phép nối chuỗi).*

### 2.2. Dữ liệu Huấn luyện & Đánh giá (Dataset Statistics)
- **Nguồn dữ liệu**: Được chiết xuất từ tập dữ liệu `Alimeeting4MUG_vi` (bản ghi âm hội thoại cuộc họp dịch từ tiếng Trung sang tiếng Việt).
- **Quy mô dữ liệu**:
  - **Tập Train (`train_vi.jsonl`)**: 295 bản ghi (hội thoại), chiết xuất ra **28,079** cặp dữ liệu song song `(8-utterance block, summary)`. 
  - **Phân chia huấn luyện**: Chia ngẫu nhiên theo mức độ cuộc họp (meeting-level group split) theo tỷ lệ **90% train (265 cuộc họp, tương đương 25,051 mẫu)** và **10% validation (30 cuộc họp, tương đương 3,028 mẫu)** với seed cố định là 42.
  - **Tập Dev benchmark (`dev_vi.jsonl`)**: 65 bản ghi hội thoại, chiết xuất ra **6,038** khối 8 câu thoại độc lập.
  - **Tập Test benchmark (`test_vi.jsonl`)**: 65 bản ghi hội thoại, chiết xuất ra **3,863** khối.
- **Phân phối độ dài token (tokenizer SentencePiece của ViT5)**:
  - Trung bình (Mean): 137 tokens.
  - Phân vị 99 (P99): 296 tokens.
  - Tối đa (Max): 2,045 tokens.
  - Tỷ lệ vượt ngưỡng 512 tokens: Chỉ có $3 / 28,079$ mẫu ($0.01\%$). Do đó, cấu hình độ dài đầu vào tối đa `max_input_length = 512` là cực kỳ an toàn.
  - Độ dài mục tiêu (Target summary length): Trung bình khoảng 175 ký tự (~50 tokens), tối đa 382 ký tự. Do đó thiết lập độ dài đầu ra tối đa `max_target_length = 128` là hoàn toàn bao phủ.

### 2.3. Siêu tham số Huấn luyện ViT5 (Hyperparameters)
| Tham số | Giá trị | Giải thích kỹ thuật |
| :--- | :---: | :--- |
| **Mô hình nền** | `VietAI/vit5-base-vietnews-summarization` | Phiên bản 226M tham số, tối ưu sâu sắc cho tóm tắt tiếng Việt. |
| **Tốc độ học (Learning Rate)** | $3 \times 10^{-4}$ | Thích hợp cho kiến trúc ViT5 hội tụ nhanh hơn BART. |
| **Batch Size thực tế** | $32$ | Kết hợp Batch Size trên mỗi GPU là $2$ và số bước tích lũy vi phân (`gradient_accumulation_steps`) là $16$ (Tránh OOM trên GPU 8GB VRAM). |
| **Hàm mất mát (Loss Function)** | Cross-Entropy | Tối ưu hóa xác suất có điều kiện trên từng token sinh ra. |
| **Chiến lược dừng sớm** | Kiên nhẫn 5 bước | Sử dụng `EarlyStoppingCallback` dựa trên điểm ROUGE-L validate. |
| **Cơ chế kiểm thử nhanh** | 200 mẫu | Đánh giá nội bộ mỗi epoch trên 200 mẫu ngẫu nhiên (chỉ tốn ~4 phút thay vì 50 phút cho toàn bộ 2,807 mẫu) để chọn checkpoint tốt nhất. Đánh giá toàn bộ tập val chỉ chạy 1 lần ở cuối phiên huấn luyện. |
| **Precision** | fp16 | Giảm một nửa bộ nhớ VRAM, tối ưu hóa tính toán trên GPU. |

### 2.4. Kết quả Đánh giá Benchmark của Chunk Summarizer (ViT5)
Kết quả đánh giá so sánh chất lượng sinh tóm tắt với duy nhất một tiêu chuẩn tham chiếu (Gemma-generated teacher labels):

| Giai đoạn đánh giá | ROUGE-1 | ROUGE-2 | ROUGE-L | Ghi chú thực nghiệm |
| :--- | :---: | :---: | :---: | :--- |
| **Validate (200 mẫu nhanh)** | 0.7316 | 0.4967 | **0.5559** | Lưu lại checkpoint tốt nhất tại Epoch 6. |
| **Validate (Full 2,807 mẫu)** | 0.7302 | 0.4957 | **0.5574** | Kiểm thử toàn tập val sau khi nạp lại trọng số tốt nhất. |
| **Dev Benchmark (`dev_vi.jsonl`)** | **0.7265** | **0.4854** | **0.5486** | Thực hiện trên **6,038** khối kiểm thử độc lập. |

*Nhận xét*: Điểm số ROUGE-1 đạt rất cao (gần 73%) phản ánh mô hình ViT5 học được cực tốt văn phong và cách lựa chọn từ vựng của giáo viên Gemma, trong khi tốc độ sinh từ chạy cục bộ nhanh gấp hơn 100 lần.

---

## 3. Huấn Luyện Bộ Tạo Tiêu Đề (Topic Segment Titler) với BARTpho

### 3.1. Nén dồn Ngữ cảnh & Giới hạn Biên ký tự (Context Compression)
Khi chuỗi các câu tóm tắt khối $\{S_1, S_2, \dots, S_m\}$ được sinh ra bởi ViT5 cho toàn bộ chủ đề thứ $k$, chúng được ghép nối theo cấu trúc:
$$X_{\text{title}} = \text{"Tạo tiêu đề: "} \mathbin{\Vert} \big(S_1 \mathbin{\Vert} \text{" / "} \mathbin{\Vert} S_2 \mathbin{\Vert} \dots \mathbin{\Vert} S_m\big)$$
Nhằm tránh tràn cửa sổ tự chú ý của kiến trúc BARTpho (vốn tối ưu ở khoảng dài trung bình), văn bản đầu vào được giới hạn độ dài ký tự cố định:
$$L_{\text{char\_max}} = 1500 \text{ ký tự}$$
Nếu chuỗi dài hơn, hệ thống sẽ thực hiện trích xuất lát cắt từ phía bên phải (right-truncation) để giữ lại các thông tin thảo luận cuối cùng. Trong hội thoại cuộc họp, các kết luận chốt phương án thường nằm ở đoạn kết chủ đề, giữ lại ngữ cảnh cuối sẽ tạo ra tiêu đề chất lượng nhất.

### 3.2. Chiến lược lựa chọn mục tiêu huấn luyện tối ưu
Dữ liệu nhãn của con người trong `Alimeeting4MUG_vi` chứa tối đa 3 tiêu đề tham chiếu do các kiểm định viên viết: $C = \{c_1, c_2, c_3\}$.
Để giảm nhiễu huấn luyện cho mạng Seq2Seq, đường ống huấn luyện chọn tiêu đề mang lượng thông tin ngữ nghĩa phong phú nhất làm đích học tập ($y^*$) bằng cách lấy tiêu đề chứa nhiều từ đơn nhất (whitespace tokens):
$$y^* = \arg\max_{c \in C} \text{Count}_{\text{words}}(c)$$

### 3.3. Siêu tham số Huấn luyện BARTpho (Hyperparameters)
| Tham số | Giá trị | Giải thích kỹ thuật |
| :--- | :---: | :--- |
| **Mô hình nền** | `vinai/bartpho-syllable-base` | Mô hình Seq2Seq 132M tham số chuyên biệt cho tiếng Việt mức âm tiết. |
| **Tốc độ học (Learning Rate)** | $5 \times 10^{-5}$ | Thấp hơn ViT5 để bảo vệ tính ổn định của cơ chế tự chú ý trên BART. |
| **Batch Size thực tế** | $64$ | Batch size trên mỗi GPU là $4$, tích lũy vi phân (`gradient_accumulation_steps`) là $16$. |
| **Độ dài đầu vào tối đa** | $1024$ tokens | Chiều dài token tối đa cho đầu vào Seq2Seq. |
| **Độ dài đầu ra tối đa** | $64$ tokens | Giới hạn ngắn gọn vì tiêu đề cần tính cô đọng cao nhất. |
| **Hàm mất mát** | Sequence NLL Loss | Hàm mất mát âm log hợp lý trên chuỗi nhãn đích. |

### 3.4. Phương pháp Đánh giá Đa Tham Chiếu (Multi-Reference RougeMax)
Vì tiêu đề cuộc họp mang tính chủ quan cao, việc so khớp nghiêm ngặt đầu ra dự đoán $P$ của mô hình với chỉ một tiêu đề duy nhất sẽ làm giảm thấp điểm số ROUGE một cách thiếu chính xác.
Hệ thống triển khai hệ đánh giá **RougeMax**: Đo lường độc lập ROUGE giữa văn bản dự đoán và từng ứng viên tiêu đề do con người gán nhãn ($C$), sau đó lấy giá trị cực đại để thu hồi độ chính xác chân thực:
$$\text{Rouge1}_{\text{Max}}(P, C) = \max_{c \in C} \text{ROUGE-1}(P, c)$$
$$\text{RougeL}_{\text{Max}}(P, C) = \max_{c \in C} \text{ROUGE-L}(P, c)$$

### 3.5. Kết quả Đánh giá Benchmark của Topic Titler (BARTpho)
Thực hiện trên tập thử nghiệm độc lập `dev_vi.jsonl` (gồm 65 hội thoại cuộc họp chia thành 736 chủ đề lớn):

| Chỉ số đánh giá (RougeMax) | Giá trị điểm số | Thống kê kích thước tokens |
| :--- | :---: | :--- |
| **Mean ROUGE-1** | **0.5304** | Trung vị số token tiêu đề dự đoán: **16 tokens** |
| **Mean ROUGE-2** | **0.2837** | Trung vị số token tóm tắt đầu vào: **356 tokens** |
| **Mean ROUGE-L** | **0.4443** | Số lượng mẫu kiểm thử: **736 phân đoạn chủ đề** |

---

## 4. So Sánh Hai Mô Hình Tạo Sinh Cốt Lõi

| Đặc trưng kỹ thuật | Chunk Summarizer | Topic Segment Titler |
| :--- | :---: | :---: |
| **Mô hình nền (Base Model)** | `VietAI/vit5-base-vietnews-summarization` | `vinai/bartpho-syllable-base` |
| **Kích thước mô hình** | 226M tham số | 132M tham số |
| **Cửa sổ ngữ cảnh (Context)** | 512 tokens | 1024 tokens |
| **Định dạng dữ liệu đầu vào** | Khối 8 câu thoại thô (`speaker: text`) | Chuỗi các câu tóm tắt khối ghép bằng `" / "` |
| **Định dạng dữ liệu đầu ra** | 1 câu tóm tắt ngắn gọn | 1 tiêu đề đại diện chủ đề |
| **Số lượng tiêu đề tham chiếu** | 1 nhãn (Gemma) | 3 nhãn (Con người dán nhãn) |
| **Phương pháp đánh giá** | Standard ROUGE | Multi-Reference RougeMax |
| **Kết quả ROUGE-1 / 2 / L** | 0.7265 / 0.4854 / 0.5486 | 0.5304 / 0.2837 / 0.4443 |
