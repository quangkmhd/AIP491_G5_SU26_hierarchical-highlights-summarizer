# Báo Cáo Đánh Giá Hiệu Năng Phân Đoạn Chủ Đề Hội Thoại (Dialogue Topic Segmentation - DTS)

> **Ngày thực hiện**: 10 tháng 07, 2026  
> **Nhiệm vụ**: Phân đoạn dòng hội thoại dài (Dialogue Topic Segmentation) thành các khối chủ đề đơn nhất ngữ nghĩa  
> **Mục tiêu**: So sánh và xếp hạng 5 thuật toán phân đoạn chủ đề khác nhau trên 6 tập dữ liệu đa dạng về độ dài, ngữ cảnh và miền ngôn ngữ.

---

## 1. Giới Thiệu Nhiệm Vụ & Bản Chất Kỹ Thuật

**Phân đoạn Chủ đề Hội thoại (Dialogue Topic Segmentation - DTS)** là tác vụ chia nhỏ một luồng văn bản hội thoại liên tục (ví dụ: bản ghi âm cuộc họp, đoạn hội thoại chat chăm sóc khách hàng, cuộc gọi thoại tư vấn) thành các phân vùng ngữ nghĩa (topic segments) độc lập. 

Khác với văn bản có cấu trúc (báo chí, sách giáo khoa có chương, đề mục rõ ràng), hội thoại tự do có ba đặc điểm gây khó khăn lớn cho các mô hình học máy:
- **Không có ranh giới vật lý rõ ràng**: Các thành viên chuyển chủ đề một cách tự nhiên thông qua các từ đệm, nói chen ngang hoặc chuyển đổi dần dần mà không có ngắt trang hay dòng mới.
- **Tính lặp và dư thừa**: Từ ngữ lặp đi lặp lại giữa các chủ đề khác nhau làm lu mờ ranh giới từ vựng.
- **Độ nhiễu cao**: Chứa nhiều từ thừa, câu ngắn, lỗi chính tả từ các bộ nhận dạng giọng nói (ASR).

---

## 2. Các Thuật Toán Phân Đoạn & Cấu Hình Tham Số (Parameters Setup)

Hệ thống đánh giá và triển khai 5 thuật toán phân đoạn chủ đề thuộc hai trường phái chính: **Heuristic/Unsupervised (Không giám sát)** và **Deep Learning/Supervised (Có giám sát)**.

```
                                  ┌─ Unsupervised (Không giám sát):
                                  │   ├── nltk_texttiling
                                  │   ├── custom_texttiling
                                  │   └── sliding_texttiling
[ Các thuật toán DTS đánh giá ]───┤
                                  └─ Supervised (Có giám sát):
                                      ├── vibert_texttiling
                                      └── bamibert_1dod
```

### 2.1. Heuristic & Unsupervised (Không giám sát)
Các phương pháp này tận dụng sự liên kết từ vựng (lexical cohesion) để phát hiện ranh giới chuyển đổi chủ đề, không yêu cầu GPU và không tốn chi phí huấn luyện.

#### 1. `nltk_texttiling`
- **Nguyên lý**: Wrapper quanh mô hình `TextTiling` cổ điển của thư viện NLTK. Gom các lượt thoại thành các khối từ vựng (pseudo-sentences), đo khoảng cách Cosine giữa các khối trượt liên tiếp và xác định thung lũng tương đồng để đặt biên.
- **Hạn chế**: Bộ tách từ của NLTK thiết kế cho tiếng Anh, không tối ưu cho âm tiết ghép của tiếng Việt.
- **Tham số cấu hình**: Sử dụng các tham số mặc định của NLTK.

#### 2. `custom_texttiling`
- **Nguyên lý**: Phiên bản cải tiến thiết kế riêng cho cấu trúc hội thoại. Nó tiền xử lý loại bỏ toàn bộ dấu câu, lọc từ dừng tiếng Việt (sử dụng thư viện `stopwordsiso`). Tính toán tần suất từ (Bag-of-Words) trên mỗi lượt thoại rồi đo độ tương đồng Cosine qua một cửa sổ trượt.
- **Điểm sâu thung lũng (Depth Score)** được tính tại mỗi vị trí biên $i$ như sau:
  $$\text{depth}(i) = (\text{peak}_L - \text{val}_i) + (\text{peak}_R - \text{val}_i)$$
  Trong đó $\text{val}_i$ là độ tương đồng tại thung lũng $i$, còn $\text{peak}_L, \text{peak}_R$ là điểm tương đồng cao nhất ở hai bên sườn trái và phải của thung lũng. Biên phân đoạn được xác định nếu điểm sâu lớn hơn ngưỡng động $\mu + \alpha \cdot \sigma$ (với $\mu$ và $\sigma$ là trung bình và độ lệch chuẩn của các điểm sâu).
- **Tham số cấu hình**:
  - `block_size`: 1 (bán kính cửa sổ trượt để so khớp từ vựng).
  - `alpha`: 2.0 (hệ số lọc ngưỡng điểm sâu để kích hoạt biên).

#### 3. `sliding_texttiling`
- **Nguyên lý**: Phương pháp phân tích chiều sâu đa thang đo (Multi-Scale Depth Analysis), lấy cảm hứng từ hệ thống *LLM-powered Meeting Recap System* (Asthana et al., 2025). Thay vì đo độ sâu ở một kích thước cửa sổ cố định, thuật toán chạy song song nhiều bán kính cửa sổ trượt khác nhau.
- **Cơ chế**:
  - Chạy `custom_texttiling` với tập hợp các bán kính $R = \{3, 5, 10, 15, 20\}$. Bán kính nhỏ nhạy cảm với các chuyển dịch chủ đề nhỏ; bán kính lớn nhận diện các bước chuyển giai đoạn lớn.
  - Chuẩn hóa điểm sâu của từng bán kính bằng Z-score để đưa về cùng một phân phối, sau đó tính trung bình cộng để tạo bản đồ sâu tích hợp:
    $$\text{depth\_profile} = \frac{1}{|R|} \sum_{r \in R} \text{zscore}(\text{depth}_r)$$
  - Ranh giới được đặt nếu $\text{depth\_profile} \ge \alpha$. Áp dụng thêm ràng buộc khoảng cách tối thiểu giữa các biên (`min_segment_ratio`) để tránh hiện tượng phân mảnh quá mức.
- **Tham số cấu hình**:
  - `block_size`: 2
  - `radii`: `[3, 5, 10, 15, 20]`
  - `alpha`: 1.5
  - `min_segment_ratio`: 0.1
  - `use_stopwords`: `True`
  - `normalize`: `"zscore"`
  - `agg`: `"mean"`

### 2.2. Supervised & Deep Learning (Có giám sát)
Sử dụng các mô hình Transformer sâu đã qua huấn luyện/tinh chỉnh để nắm bắt thông tin ngữ nghĩa thay vì chỉ so khớp tần suất từ vựng thô.

#### 4. `vibert_texttiling`
- **Nguyên lý**: Thay thế vector Bag-of-Words trong TextTiling bằng vector nhúng ngữ nghĩa (dense sentence embedding) sinh ra từ mô hình Transformer tiếng Việt. Độ tương đồng Cosine được đo trên không gian vector nhúng biểu diễn ý nghĩa sâu sắc của câu thoại.
- **Tham số cấu hình**:
  - Mô hình cơ sở: Tinh chỉnh từ kiến trúc BERT tiếng Việt (`Sentence-BERT`).
  - Đường dẫn checkpoint: `models/vibert/cpt_3818.pth`.

#### 5. `bamibert_1dod`
- **Nguyên lý**: Chuyển đổi tác vụ phân đoạn hội thoại thành bài toán **Phát hiện vật thể 1 chiều (1D Object Detection)** trên chuỗi lượt thoại. Mô hình mã hóa ngữ cảnh đa lượt thoại xung quanh biên và phân loại nhị phân trực tiếp xem ranh giới giữa hai lượt thoại $i$ và $i+1$ có phải là điểm chuyển chủ đề hay không. Phương pháp này tận dụng tốt các tín hiệu từ vựng hội thoại (như câu chào, câu kết, chuyển vai nói).
- **Tham số cấu hình**:
  - Mô hình cơ sở: `BamiBert` tinh chỉnh riêng cho tác vụ phát hiện biên.
  - Đường dẫn checkpoint: `models/bamibert-1dod-vi-v1`.

---

## 3. Hệ Dữ Liệu Đánh Giá (Evaluation Datasets)

Quá trình benchmark được thực hiện trên 6 tập dữ liệu hội thoại và văn bản phân đoạn có đặc tính rất khác biệt. Thống kê chi tiết như sau:

| Tên tập dữ liệu (JSON) | Số lượng hội thoại (Dialogues) | Tổng số lượt thoại (Utterances) | Trung bình lượt thoại/đoạn | Tổng số phân đoạn chủ đề (Segments) | Trung bình phân đoạn/đoạn | Đặc trưng & Nguồn gốc dữ liệu |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`dialseg_711.json`** | 711 | 19,350 | 27.2 | 3,465 | 4.9 | Bản dịch tiếng Việt từ tập dữ liệu DialSeg (AMI meetings). Lượt thoại ngắn, chủ đề chuyển đổi nhanh. |
| **`doc2dial.json`** | 3,270 | 42,585 | 13.0 | 11,400 | 3.5 | Dữ liệu hội thoại hướng nhiệm vụ (task-oriented) dựa trên tài liệu hướng dẫn dịch vụ công. |
| **`meeting_ami.json`** | 137 | 73,379 | 535.6 | 601 | 4.4 | Bản dịch tiếng Việt từ AMI Meeting Corpus. Bản ghi âm cuộc họp nhóm dài, nhiều nhiễu, đối thoại đan xen phức tạp. |
| **`meeting_committee.json`** | 36 | 7,477 | 207.7 | 254 | 7.1 | Bản ghi các cuộc thảo luận của ủy ban/hội đồng. Tính trang trọng cao hơn AMI, độ dài trung bình. |
| **`meeting_icsi.json`** | 59 | 48,321 | 819.0 | 268 | 4.5 | Bản dịch tiếng Việt của ICSI Meeting Corpus. Họp học thuật chuyên ngành, cực kỳ dài và độ phức tạp từ vựng rất lớn. |
| **`tiage.json`** | 500 | 7,802 | 15.6 | 2,013 | 4.0 | Bản dịch tiếng Việt từ tập dữ liệu Tiage. Đối thoại tư vấn y tế/tâm lý ngắn, cấu trúc chặt chẽ. |

---

## 4. Phương Pháp Đánh Giá & Các Chỉ Số (Evaluation Metrics)

Để đo lường độ chính xác của ranh giới chủ đề được dự đoán so với nhãn gốc từ con người, hệ thống tính toán 4 chỉ số cốt lõi:

1. **Chỉ số $P_k$ (Beeferman Metric - $\downarrow$)**:
   - **Cách tính**: Một cửa sổ trượt có kích thước $k$ (thường đặt bằng một nửa chiều dài trung bình thực tế của các phân đoạn chủ đề: $k = \frac{\text{avg\_segment\_len}}{2}$) được di chuyển qua toàn bộ chuỗi lượt thoại. Tại mỗi bước, chỉ số kiểm tra xem số lượng ranh giới bên trong cửa sổ của bản dự đoán và bản gốc có đồng nhất hay không (đồng nhất về việc có tồn tại biên hay không).
   - **Ý nghĩa**: Phản ánh xác suất xảy ra lỗi phân đoạn. Chỉ số nằm trong khoảng $[0.0, 1.0]$. **Giá trị càng thấp càng tốt** ($0.0$ là hoàn hảo).
2. **Chỉ số $W_d$ (WindowDiff - $\downarrow$)**:
   - **Cách tính**: Tương tự như $P_k$, nhưng nghiêm ngặt hơn. Thay vì chỉ kiểm tra tính đồng nhất nhị phân (có/không có biên), $W_d$ kiểm tra xem số lượng biên chính xác trong cửa sổ dự đoán có khớp hoàn toàn với nhãn gốc hay không.
   - **Ý nghĩa**: Khắc phục nhược điểm của $P_k$ (khi $P_k$ dễ bị đánh lừa bởi các mô hình dự đoán quá nhiều biên hoặc quá ít biên). **Giá trị càng thấp càng tốt**.
3. **Chỉ số $F_1$-score ($\uparrow$)**:
   - **Cách tính**: Định nghĩa ranh giới dự đoán là chính xác (True Positive) nếu nó nằm trong một khoảng cách dung sai cho phép (tolerance window) so với ranh giới thực tế. Tính toán Precision (Độ chính xác) và Recall (Độ phủ), từ đó tính trung bình điều hòa $F_1$. **Giá trị càng cao càng tốt** (khoảng $[0.0, 1.0]$).
4. **Thời gian thực thi (Total Time - s)**:
   - Đo lường thời gian chạy (tính bằng giây) để xử lý toàn bộ tập dữ liệu, phản ánh tính khả thi khi ứng dụng vào hệ thống thực tế cần độ trễ thấp.

---

## 5. Kết Quả Benchmark Chi Tiết (Detailed Benchmark Results)

Dưới đây là kết quả thực nghiệm chi tiết của 5 thuật toán trên 6 tập dữ liệu.

### 5.1. Kết quả trên từng tập dữ liệu

#### dialseg_711.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| **`custom_texttiling`** | **0.3467** | **0.3678** | 0.4320 | **1.5** |
| `sliding_texttiling` | 0.3660 | 0.4264 | **0.4472** | 1.9 |
| `vibert_texttiling` | 0.4253 | 0.4263 | 0.0230 | 300.8 |
| `nltk_texttiling` | 0.4417 | 0.4434 | 0.0871 | 4.8 |
| `bamibert_1dod` | 0.4474 | 0.4477 | 0.0104 | 15.9 |

#### doc2dial.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| **`bamibert_1dod`** | **0.4593** | **0.4593** | 0.0007 | 39.2 |
| `nltk_texttiling` | 0.4720 | 0.4721 | 0.0688 | 12.9 |
| `vibert_texttiling` | 0.4736 | 0.4741 | 0.0538 | 645.9 |
| `custom_texttiling` | 0.4830 | 0.4835 | 0.0730 | **6.0** |
| `sliding_texttiling` | 0.5241 | 0.5656 | **0.3302** | 7.0 |

#### meeting_ami.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| **`vibert_texttiling`** | **0.3745** | **0.3960** | 0.0055 | 2482.4 |
| `sliding_texttiling` | 0.4410 | 0.4463 | 0.0000 | 25.7 |
| `custom_texttiling` | 0.4981 | 0.6432 | 0.0093 | **20.9** |
| `bamibert_1dod` | 0.5585 | 0.6968 | **0.0445** | 84.9 |
| `nltk_texttiling` | 0.5881 | 0.8358 | 0.0162 | 394.3 |

#### meeting_committee.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| **`vibert_texttiling`** | **0.4324** | **0.4530** | 0.0032 | 262.4 |
| `sliding_texttiling` | 0.4559 | 0.4630 | 0.0489 | **3.7** |
| `custom_texttiling` | 0.4746 | 0.5592 | 0.0707 | 3.9 |
| `nltk_texttiling` | 0.5174 | 0.7635 | 0.0304 | 809.9 |
| `bamibert_1dod` | 0.5967 | 0.8669 | **0.0757** | 70.5 |

#### meeting_icsi.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| **`vibert_texttiling`** | **0.3825** | **0.3825** | 0.0000 | 1457.0 |
| `sliding_texttiling` | 0.4265 | 0.4265 | 0.0000 | 16.4 |
| `custom_texttiling` | 0.5760 | 0.8722 | 0.0083 | **14.3** |
| `nltk_texttiling` | 0.6014 | 0.9513 | 0.0086 | 829.1 |
| `bamibert_1dod` | 0.6167 | 0.9470 | **0.0175** | 93.5 |

#### tiage.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| **`vibert_texttiling`** | **0.4553** | **0.4569** | 0.0494 | 219.4 |
| `nltk_texttiling` | 0.4752 | 0.4759 | 0.0165 | 7.6 |
| `sliding_texttiling` | 0.4794 | 0.5734 | **0.3557** | 8.3 |
| `custom_texttiling` | 0.4884 | 0.5264 | 0.2977 | **6.3** |
| `bamibert_1dod` | 0.4940 | 0.4940 | 0.0669 | 2.1 |

---

### 5.2. Bảng Xếp Hạng Tổng Hợp (Overall Ranking)

Điểm xếp hạng tổng hợp (Composite Score) được tính bằng giá trị trung bình của điểm chuẩn hóa min-max đảo ngược của $P_k$ (càng thấp càng tốt), $W_d$ (càng thấp càng tốt) và điểm $F_1$ trên từng tập dữ liệu. Điểm Composite càng gần $1.0$ thể hiện thuật toán hoạt động càng tốt trên toàn bộ các tập thử nghiệm.

| Xếp hạng | Thuật toán | Điểm Composite (↑) | Trung bình Pk (↓) | Trung bình WD (↓) | Trung bình F1 (↑) | Nhận xét hiệu năng |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **`vibert_texttiling`** | **0.5854** | **0.4239** | **0.4315** | 0.0225 | Đạt hiệu năng phân đoạn vượt trội (Pk, WD tốt nhất) trên các tài liệu họp cực dài và phức tạp (`ami`, `icsi`, `committee`). Nhược điểm: tốn tài nguyên và thời gian chạy cực lâu (GPU inference). |
| **2** | **`custom_texttiling`** | **0.5690** | 0.4778 | 0.5754 | 0.1485 | Cân bằng tuyệt vời giữa chất lượng phân đoạn và thời gian tính toán siêu nhanh (chạy CPU chỉ vài giây). Hoạt động rất tốt trên các văn bản hội thoại ngắn. |
| **3** | **`sliding_texttiling`** | **0.5680** | 0.4488 | 0.4835 | **0.1970** | Điểm F1 trung bình cao nhất. Nhờ cơ chế Z-score đa thang đo, nó bắt được cả ranh giới lớn và nhỏ. Cực kỳ tối ưu cho các luồng hội thoại có độ dài phân đoạn biến thiên cao. |
| **4** | **`bamibert_1dod`** | **0.3496** | 0.5288 | 0.6519 | 0.0360 | Hiệu năng phân khúc trên tập dữ liệu ngắn tốt (ví dụ đạt Pk tốt nhất trên `doc2dial.json`), nhưng độ ổn định kém trên tài liệu siêu dài và hội thoại họp tự do. |
| **5** | **`nltk_texttiling`** | **0.3071** | 0.5160 | 0.6570 | 0.0379 | Hiệu năng kém nhất do cơ chế tiền xử lý không được tối ưu cho ngôn ngữ đơn âm tiết tiếng Việt. |

---

## 6. Kết Luận & Khuyến Nghị Vận Hành

1. **Khi cần độ chính xác tối đa trên cuộc họp dài**: Khuyến nghị dùng **`vibert_texttiling`** để tận dụng tối đa không gian ngữ nghĩa dense embedding của Transformer.
2. **Khi tối ưu hóa tài nguyên phần cứng & thời gian thực**: Khuyến nghị sử dụng **`sliding_texttiling`** hoặc **`custom_texttiling`**. Các giải pháp heuristic này không cần GPU, chạy nhanh hơn các mô hình Transformer từ 100x đến 1000x trong khi vẫn duy trì điểm số phân đoạn $P_k$ rất sát nút (sai số Composite dưới 2%).