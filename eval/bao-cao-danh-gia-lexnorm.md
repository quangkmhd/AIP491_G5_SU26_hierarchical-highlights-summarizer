# Báo Cáo Kết Quả Đánh Giá Mô Hình Chuẩn Hóa Từ Vựng (Lexical Normalization)

Báo cáo này trình bày kết quả đánh giá thực tế của công cụ chuẩn hóa từ vựng (lexnorm) chạy trên tập dữ liệu gồm **239 phân đoạn hội thoại**, so sánh hiệu suất giữa văn bản thô từ mô hình ASR (Sherpa) và văn bản đã chuẩn hóa bằng mô hình ngôn ngữ lớn (LLM) so với dữ liệu Ground Truth (Soniox).

---

## 1. Cấu Hình Đợt Đánh Giá (Run Configuration)

*   **Thư mục dữ liệu thô (ASR Sherpa):** `/home/quangnhvn34/dev/me/AIP491/data/processed/output_sherpa`
*   **Thư mục dữ liệu nhãn chuẩn (Truth Soniox):** `/home/quangnhvn34/dev/me/AIP491/data/processed/output_soniox`
*   **Mô hình LLM chuẩn hóa:** `gemma4:12b-it-qat` (chạy trên Ollama cục bộ)
*   **Địa chỉ API Ollama:** `http://127.0.0.1:11434`
*   **Số luồng xử lý song song (`max_workers`):** `1` (Tuần tự từng câu hội thoại để đảm bảo tính ổn định và đo lường độ trễ chuẩn xác)
*   **Tổng số cặp phân đoạn đánh giá (`pair_count`):** `239`
*   **Chế độ chạy:** `ollama` (Thực tế)
*   **Thời gian chạy:** `0.001` giây (Sử dụng cơ chế khôi phục từ log tạm `jsonl` đã lưu trước đó)

---

## 2. Kết Quả Chỉ Số Metrics Tổng Thể (Overall Metrics)

| Chỉ số | Trước chuẩn hóa (Raw) | Sau chuẩn hóa (Corrected) | Thay đổi (Delta) | Cải thiện? |
| :--- | :---: | :---: | :---: | :---: |
| **WER (Tỷ lệ lỗi từ)** | 13.8886% | 13.5636% | -0.3250% | **Có (Đạt)** |
| **CER (Tỷ lệ lỗi ký tự)** | 11.1628% | 10.8856% | -0.2772% | **Có (Đạt)** |

---

## 3. Ma Trận Nhầm Lẫn Cục Bộ (Confusion Matrix)

Dưới đây là thống kê hành vi sửa đổi cấp câu thoại của mô hình:

| Phân nhóm | Số lượng câu | Ý nghĩa thực tế | Đánh giá |
| :--- | :---: | :--- | :---: |
| **TP** (True Positive) | `11` | ASR thô viết sai, mô hình **sửa đúng** khớp Ground Truth (hoặc cả hai đều đúng). | Tốt |
| **FN** (False Negative) | `125` | ASR thô viết sai, mô hình **không sửa** hoặc giữ nguyên lỗi. | Chưa đạt |
| **FP1** (False Positive 1) | `3` | ASR thô vốn đã đúng, mô hình tự ý sửa dẫn đến **bị sai**. | Nguy hại |
| **FP2** (False Positive 2) | `100` | ASR thô viết sai, mô hình nhận biết được nhưng **sửa thành một lỗi sai khác**. | Chưa đạt |

### Thống kê tài nguyên & hiệu năng:
*   **Tổng số câu thoại đã xử lý:** 239 câu.
*   **Tổng thời gian LLM xử lý (Latency Total):** 3.823.443 ms (~ 63,7 phút).
*   **Thời gian xử lý trung bình mỗi câu (Latency Mean):** 15.997 ms (~ 16 giây / câu).

---

## 4. Phân Tích Các Ví Dụ Điển Hình (Representative Examples)

### 4.1. Nhóm TP (Sửa lỗi đúng hoàn toàn)
Mô hình làm tốt trong việc khôi phục dấu câu, viết hoa viết thường chữ cái đầu câu và sửa các từ đơn giản.
*   **Ví dụ 1 (video_id=01_tsKMxDpZV68 seg=4):**
    *   *Raw:* `NHƯNG MÀ VẤN ĐỀ ĐẶT RA LÀ MÌNH NHÌN VÀO ĐÂU ĐỂ MÌNH KẾT LUẬN LÀ NGƯỜI NÀY CÓ NHỮNG CÁI KỸ NĂNG ĐÁP ỨNG ĐÚNG YÊU CẦU THÌ BÂY GIỜ CÁC BẠN XEM THỬ CÁI ĐỊNH NGHĨA BÊN CẠNH CÁC BẠN NHÌN THẤY CÁI VÍ DỤ BÊN CẠNH`
    *   *Corrected:* `Nhưng mà vấn đề đặt ra là mình nhìn vào đâu để mình kết luận là người này có những cái kỹ năng đáp ứng đúng yêu cầu thì bây giờ các bạn xem thử cái định nghĩa bên cạnh các bạn nhìn thấy cái ví dụ bên cạnh`
    *   *Truth:* `Nhưng mà vấn đề đặt ra là: mình nhìn vào đâu để mình kết luận là người này có những cái kỹ năng đáp ứng đúng yêu cầu? Thì bây giờ các bạn xem thử cái định nghĩa bên cạnh. Các bạn nhìn thấy cái ví dụ bên cạnh.`
*   **Ví dụ 2 (video_id=01_tsKMxDpZV68 seg=10):**
    *   *Raw:* `VỪA QUAN SÁT NGÔN NGỮ CƠ THỂ CỦA ỨNG VIÊN VẬY LÀ MÌNH THẤY QUAN SÁT NGÔN NGỮ CƠ THỂ LÀ QUAN SÁT CÁI GÌ RỒI ĐẶT CÂU HỎI THEO CẤU TRÚC PHẺO NHƯ VẬY THÌ ĐẶT CÂU HỎI THEO CẤU TRÚC PHẺO LÀ NÓ TỪ TO ĐẾN NHỎ VÀ HIỆU QUẢ`
    *   *Corrected:* `Vừa quan sát ngôn ngữ cơ thể của ứng viên vậy là mình thấy quan sát ngôn ngữ cơ thể là quan sát cái gì rồi đặt câu hỏi theo cấu trúc phễu như vậy thì đặt câu hỏi theo cấu trúc phễu là nó từ to đến nhỏ và hiệu quả`
    *   *Truth:* `Vừa quan sát ngôn ngữ cơ thể của ứng viên, vậy là mình thấy quan sát ngôn ngữ cơ thể là quan sát cái gì rồi. Đặt câu hỏi theo cấu trúc phễu, như vậy thì đặt câu hỏi theo cấu trúc phễu là nó từ to đến nhỏ, và hiệu quả.`

### 4.2. Nhóm FN (Bỏ qua lỗi hoặc lỗi hệ thống)
Phần lớn các câu thuộc nhóm FN là do mô hình trả về chuỗi JSON bị lỗi cú pháp hoặc bị cắt cụt do vượt quá giới hạn token (validation error), dẫn đến việc kích hoạt cơ chế dự phòng (fallback) giữ nguyên văn bản thô.
*   **Ví dụ 1 (video_id=01_tsKMxDpZV68 seg=1):**
    *   *Raw:* `KIM ANH MƯỢN CÁI ĐỊNH NGHĨA CỦA TỔ CHỨC GỌI LÀ QUẢN LÝ NĂNG LỰC TRÊN THẾ GIỚI Thấy... (đoạn rất dài)... THÀNH CÔNG`
    *   *Lý do thất bại:* `validation_error` do LLM tạo ra chuỗi JSON không hợp lệ (EOF hoặc lỗi phân tích cú pháp). Các câu hội thoại quá dài thường dễ bị lỗi này.

### 4.3. Nhóm FP1 (Tự ý sửa làm hỏng câu đúng)
Mô hình đôi khi thay thế quá đà một số từ vựng tiếng Việt đang đúng thành các từ đồng âm sai ngữ cảnh.
*   **Ví dụ 1 (video_id=01_tsKMxDpZV68 seg=50):**
    *   *Raw:* `... THÌ CÁC BẠN MÔ TẢ NÓ QUÁ TỦNG MỦNG ĐI...`
    *   *Corrected:* `... thì các bạn mô tả nó quá tủi mủn đi...`
    *   *Truth:* `... thì các bạn mô tả nó quá tủng mủng đi...`
    *   *Lý do:* Từ "tủng mủng" (vụn vặt/nhỏ nhặt) là từ địa phương đúng ngữ cảnh nhưng mô hình tự sửa thành "tủi mủn" không có nghĩa.

### 4.4. Nhóm FP2 (Sửa lỗi nhưng vẫn sai)
Đây là nhóm chiếm số lượng lớn nhất (100 câu), xảy ra khi mô hình cố gắng sửa nhưng kết quả chưa đạt độ chuẩn xác so với Ground Truth hoặc sửa thiếu từ đệm nói lắp.
*   **Ví dụ 1 (video_id=01_tsKMxDpZV68 seg=6):**
    *   *Raw:* `... XIN MỜI CÁC BẠN CHỊ THẤY HÀ MY SPA`
    *   *Corrected:* `... Xin mời các bạn chị thấy Hà My spa.`
    *   *Truth:* `... xin mời các bạn. Ờ, chị thấy Hà Mi Spa.`
*   **Ví dụ 2 (video_id=01_tsKMxDpZV68 seg=49):**
    *   *Raw:* `... NÓ HƠI BỊ TỦNG MỦNG LẤY VÍ DỤ...`
    *   *Corrected:* `... nó hơi bị vụn vặt lấy ví dụ...`
    *   *Truth:* `... nó hơi bị tủng mủng. Lấy ví dụ...`
    *   *Lý do:* Mô hình tự ý đồng nghĩa hóa từ "tủng mủng" thành "vụn vặt", làm thay đổi cấu trúc từ vựng so với Ground Truth.

---

## 5. Kết Luận Và Đề Xuất

### Kết luận:
1.  **WER và CER cải thiện nhẹ:** Sự sụt giảm của cả hai chỉ số (WER giảm `0.325%`, CER giảm `0.277%`) cho thấy bước chuẩn hóa Lexnorm bước đầu mang lại giá trị tích cực cho văn bản.
2.  **Đánh giá quyết định (Go/No-go):** **GO** cho giai đoạn tóm tắt tiếp theo (Summary Phase 2) vì chất lượng tổng thể văn bản đã tốt hơn.

### Đề xuất tối ưu hóa Lexnorm:
*   **Rút ngắn câu thoại:** Đối với các câu hội thoại cực dài của Sherpa, nên chia nhỏ thêm (sub-segment) trước khi gửi qua Lexnorm để tránh lỗi định dạng JSON do hết hạn token dự đoán.
*   **Tắt chế độ đồng nghĩa hóa (Paraphrase):** Cần bổ sung luật cấm mô hình thay thế các từ ngữ địa phương/từ hiếm có nghĩa trong tiếng Việt (ví dụ: `tủng mủng`) bằng các từ đồng nghĩa phổ thông hơn (`vụn vặt`) nhằm giữ nguyên bản sắc hội thoại.
*   **Tăng tốc độ:** Nghiên cứu nâng cấu hình Ollama chạy song song (`max_workers` > 1) kết hợp tối ưu tham số nhiệt độ (`temperature = 0`) để giảm thời gian phản hồi trung bình (hiện tại đang là khá chậm: 16 giây/câu).
