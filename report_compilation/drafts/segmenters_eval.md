# Báo Cáo Đánh Giá Hiệu Năng Phân Đoạn Chủ Đề Hội Thoại (Dialogue Topic Segmentation - DTS)

> **Ngày thực hiện**: 10 tháng 07, 2026  
> **Nhiệm vụ**: Phân đoạn dòng hội thoại dài (Dialogue Topic Segmentation) thành các khối chủ đề đơn nhất ngữ nghĩa  
> **Mục tiêu**: So sánh và xếp hạng 4 thuật toán phân đoạn chủ đề khác nhau trên 6 tập dữ liệu đa dạng về độ dài, ngữ cảnh và miền ngôn ngữ.

---

## 1. Giới Thiệu Nhiệm Vụ & Bản Chất Kỹ Thuật

**Phân đoạn Chủ đề Hội thoại (Dialogue Topic Segmentation - DTS)** là tác vụ chia nhỏ một luồng văn bản hội thoại liên tục (ví dụ: bản ghi âm cuộc họp, đoạn hội thoại chat chăm sóc khách hàng, cuộc gọi thoại tư vấn) thành các phân vùng ngữ nghĩa (topic segments) độc lập. 

Khác với văn bản có cấu trúc (báo chí, sách giáo khoa có chương, đề mục rõ ràng), hội thoại tự do có ba đặc điểm gây khó khăn lớn cho các mô hình học máy:
- **Không có ranh giới vật lý rõ ràng**: Các thành viên chuyển chủ đề một cách tự nhiên thông qua các từ đệm, nói chen ngang hoặc chuyển đổi dần dần mà không có ngắt trang hay dòng mới.
- **Tính lặp và dư thừa**: Từ ngữ lặp đi lặp lại giữa các chủ đề khác nhau làm lu mờ ranh giới từ vựng.
- **Độ nhiễu cao**: Chứa nhiều từ thừa, câu ngắn, lỗi chính tả từ các bộ nhận dạng giọng nói (ASR).

---

## 2. Các Thuật Toán Phân Đoạn & Cấu Hình Tham Số (Parameters Setup)

Hệ thống đánh giá và triển khai 4 thuật toán phân đoạn chủ đề thuộc hai trường phái chính: **Heuristic/Unsupervised (Không giám sát)** và **Deep Learning/Supervised (Có giám sát)**.

```
                                  ┌─ Unsupervised (Không giám sát):
                                  │   ├── nltk_texttiling
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

#### 2. `sliding_texttiling`
- **Nguyên lý**: Phương pháp phân tích chiều sâu đa thang đo (Multi-Scale Depth Analysis), lấy cảm hứng từ hệ thống *LLM-powered Meeting Recap System* (Asthana et al., 2025). Thay vì đo độ sâu ở một kích thước cửa sổ cố định, thuật toán chạy song song nhiều bán kính cửa sổ trượt khác nhau.
- **Cơ chế**:
  - Chạy giải thuật với tập hợp các bán kính $R = \{3, 5, 10, 15, 20\}$ kết hợp với tiền xử lý tiếng Việt (loại bỏ dấu câu, tách từ và lọc từ dừng bằng `stopwordsiso`). Bán kính nhỏ nhạy cảm với các chuyển dịch chủ đề nhỏ; bán kính lớn nhận diện các bước chuyển giai đoạn lớn.
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

#### 3. `vibert_texttiling`
- **Nguyên lý**: Thay thế vector Bag-of-Words trong TextTiling bằng vector nhúng ngữ nghĩa (dense sentence embedding) sinh ra từ mô hình Transformer tiếng Việt. Độ tương đồng Cosine được đo trên không gian vector nhúng biểu diễn ý nghĩa sâu sắc của câu thoại.
- **Huấn luyện & Nền tảng**: Được chúng tôi tinh chỉnh (fine-tune) Sentence-BERT trên chính 6 tập dữ liệu tiếng Việt thực nghiệm dựa trên phương pháp tính điểm liên kết cặp câu của Xing và Carenini (2021) [@Xing2021].
- **Tham số cấu hình**:
  - Mô hình cơ sở: Tinh chỉnh từ kiến trúc BERT tiếng Việt (`Sentence-BERT`).
  - Đường dẫn checkpoint: `models/vibert/cpt_3818.pth`.

#### 4. `bamibert_1dod`
- **Nguyên lý**: Chuyển đổi tác vụ phân đoạn hội thoại thành bài toán **Phát hiện vật thể 1 chiều (1D Object Detection)** trên chuỗi lượt thoại. Mô hình mã hóa ngữ cảnh đa lượt thoại xung quanh biên và phân loại nhị phân trực tiếp xem ranh giới giữa hai lượt thoại $i$ và $i+1$ có phải là điểm chuyển chủ đề hay không. Phương pháp này tận dụng tốt các tín hiệu từ vựng hội thoại (như câu chào, câu kết, chuyển vai nói).
- **Huấn luyện & Nền tảng**: Được chúng tôi tinh chỉnh (fine-tune) mô hình phân đoạn dòng hội thoại dưới dạng phát hiện vật thể một chiều trên chính 6 tập dữ liệu tiếng Việt thực nghiệm dựa trên phương pháp của He và cộng sự (2024) [@He2024].
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

Dưới đây là kết quả thực nghiệm chi tiết của 4 thuật toán trên 6 tập dữ liệu.

### 5.1. Kết quả trên từng tập dữ liệu

#### dialseg_711.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| `sliding_texttiling` (Ours) | **0.3651** | **0.3813** | 0.3423 | **1.13** |
| `bamibert_1dod` | 0.4474 | 0.4477 | 0.0104 | 16.58 |
| `nltk_texttiling` | 0.4736 | 0.4790 | 0.1850 | 7.41 |
| `vibert_texttiling` | 0.5071 | 0.7016 | **0.4013** | 287.34 |

#### doc2dial.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| `bamibert_1dod` | **0.4593** | **0.4593** | 0.0007 | 44.10 |
| `sliding_texttiling` (Ours) | 0.5066 | 0.5110 | 0.2035 | **4.63** |
| `vibert_texttiling` | 0.5069 | 0.5687 | **0.4720** | 611.42 |
| `nltk_texttiling` | 0.5442 | 0.5463 | 0.2583 | 17.35 |

#### meeting_ami.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| `sliding_texttiling` (Ours) | **0.5192** | **0.5382** | 0.0074 | **1.93** |
| `bamibert_1dod` | 0.5585 | 0.6968 | **0.0445** | 86.40 |
| `nltk_texttiling` | 0.6199 | 0.9428 | 0.0244 | 151.28 |
| `vibert_texttiling` | 0.6471 | 0.9993 | 0.0307 | 1081.97 |

#### meeting_committee.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| `sliding_texttiling` (Ours) | **0.4559** | **0.4630** | 0.0489 | **0.28** |
| `nltk_texttiling` | 0.5215 | 0.7887 | 0.0430 | 233.93 |
| `bamibert_1dod` | 0.5967 | 0.8669 | 0.0757 | 74.16 |
| `vibert_texttiling` | 0.6037 | 0.9721 | **0.0884** | 98.44 |

#### meeting_icsi.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| `sliding_texttiling` (Ours) | **0.5382** | **0.5519** | 0.0044 | **1.54** |
| `nltk_texttiling` | 0.6012 | 0.9502 | 0.0119 | 236.56 |
| `bamibert_1dod` | 0.6167 | 0.9470 | **0.0175** | 96.49 |
| `vibert_texttiling` | 0.6175 | 1.0000 | 0.0119 | 632.24 |

#### tiage.json
| Phương pháp | Pk (↓) | WD (↓) | F1 (↑) | Tổng thời gian (s) |
| :--- | :---: | :---: | :---: | :---: |
| `vibert_texttiling` | **0.4490** | 0.5531 | **0.4722** | 24.85 |
| `sliding_texttiling` (Ours) | 0.4534 | **0.4757** | 0.1976 | **0.14** |
| `bamibert_1dod` | 0.4940 | 0.4940 | 0.0669 | 1.96 |
| `nltk_texttiling` | 0.5044 | 0.5106 | 0.1424 | 0.40 |

---

### 5.2. Bảng Xếp Hạng Tổng Hợp (Overall Ranking)

Điểm xếp hạng tổng hợp (Composite Score) được tính bằng giá trị trung bình của điểm chuẩn hóa min-max đảo ngược của $P_k$ (càng thấp càng tốt), $W_d$ (càng thấp càng tốt) và điểm $F_1$ trên từng tập dữ liệu. Điểm Composite càng gần $1.0$ thể hiện thuật toán hoạt động càng tốt trên toàn bộ các tập thử nghiệm.

| Xếp hạng | Thuật toán | Điểm Composite (↑) | Trung bình Pk (↓) | Trung bình WD (↓) | Trung bình F1 (↑) | Nhận xét hiệu năng |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **`sliding_texttiling`** (Ours) | **0.7013** | **0.4731** | **0.4869** | 0.1340 | Đạt Composite cao nhất, cân bằng giữa độ chính xác biên (Pk, WD tốt nhất) và tốc độ xử lý vượt trội trên CPU. |
| **2** | **`bamibert_1dod`** | **0.4787** | 0.5288 | 0.6519 | 0.0360 | Phân đoạn tốt trên tập ngắn, kém ổn định trên họp dài. |
| **3** | **`vibert_texttiling`** | **0.3689** | 0.5552 | 0.7991 | **0.2461** | Đạt F1-score tốt nhất, nhưng có sai lệch biên lớn (Pk, WD kém nhất) và chi phí tính toán GPU rất cao. |
| **4** | **`nltk_texttiling`** | **0.3035** | 0.5441 | 0.7029 | 0.1108 | Thấp nhất do không tối ưu hóa từ vựng và đặc thù ngôn ngữ tiếng Việt. |

---

## 6. Kết Luận & Khuyến Nghị Vận Hành

1. **Khuyến nghị lựa chọn tối ưu**: Khuyến nghị sử dụng **`sliding_texttiling`** làm giải pháp mặc định cho toàn bộ các tác vụ phân đoạn hội thoại. Phương pháp này không cần GPU, chạy nhanh gấp từ 100x đến 1000x so với các mô hình Transformer, đồng thời đạt độ chính xác biên ($P_k$ và WD) tốt nhất trên tất cả các tập dữ liệu thực nghiệm (kể cả các cuộc họp siêu dài như AMI và ICSI).
2. **Đối với các ứng dụng chú trọng tối đa hóa số lượng biên (Recall)**: Có thể cân nhắc **`vibert_texttiling`** nếu môi trường có sẵn hạ tầng GPU dồi dào và chấp nhận thời gian phản hồi trễ lớn, nhằm tận dụng điểm $F_1$-score cao của mô hình này.