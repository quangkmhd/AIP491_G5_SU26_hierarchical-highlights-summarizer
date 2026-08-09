# BẢN THIẾT KẾ & KỊCH BẢN TRÌNH BÀY SLIDE BẢO VỆ ĐỒ ÁN

## Đề tài: VIETNAMESE STREAMING MEETING SUMMARIZATION

### Multi-Scale Topic Segmentation and Hierarchical Summarization

---

## I. CẤU TRÚC VÀ PHÂN BỔ THỜI GIAN

Bộ slide được thiết kế tối ưu cho buổi bảo vệ **16–18 phút**, gồm **32 slide chính** (chỉ 23 slide cần thuyết trình sâu nội dung, 9 slide còn lại là trang bìa và chuyển phần) và **8 slide dự phòng (Backup)** phục vụ phần Hỏi & Đáp (Q&A).

| Phần        | Tên phần                |  Slide  | Thời gian dự kiến | Mục tiêu chính                                                         |
| :----------- | :------------------------ | :------: | :------------------: | :------------------------------------------------------------------------ |
| **01** | Cover & Table of Contents |  1 – 2  |      0.5 phút      | Đặt tên đề tài, thành viên, mục lục 6 phần bài bảo vệ       |
| **02** | Introduction              |  3 – 7  |   2.5 – 3.0 phút   | Động lực, bài toán, khoảng trống nghiên cứu và 5 đóng góp    |
| **03** | Methodology               | 8 – 18 |   5.5 – 6.0 phút   | Kiến trúc, pipeline 5 mô-đun, TextTiling và Tóm tắt phân cấp     |
| **04** | Datasets                  | 19 – 21 |   1.5 – 2.0 phút   | AliMeeting4MUG-Vi, dữ liệu ASR & Benchmark phân đoạn chủ đề       |
| **05** | Experiments & Results     | 22 – 26 |   4.0 – 4.5 phút   | Kết quả thực nghiệm ASR, Phân đoạn, ViT5, BARTpho & Error Analysis |
| **06** | Conclusion & Live Demo    | 27 – 31 |   2.0 – 2.5 phút   | Tổng kết đóng góp, lộ trình phát triển & Kịch bản Live Demo    |
| **07** | Thank You & Q&A           |    32    |      Discussion      | Lời cảm ơn và giữ màn hình tóm tắt kết quả chính              |
| **08** | Backup Slides             | B1 – B8 |         Q&A         | Phục vụ trả lời các câu hỏi kỹ thuật sâu từ Hội đồng        |

---

## II. CHI TIẾT NỘI DUNG 32 SLIDE CHÍNH

---

### Slide 1 — Cover Page

#### Content on Slide

> **VIETNAMESE STREAMING MEETING SUMMARIZATION**
> **Multi-Scale Topic Segmentation and Hierarchical Summarization**
>
> **Sinh viên thực hiện:**
> Student 1: ... | Student 2: ... | Student 3: ... | Student 4: ...
>
> **Giảng viên hướng dẫn:**
> Supervisor: ...
>
> **Mã nhóm / Học kỳ:** AIP491_Gx | Fall 2026
> **Đơn vị:** FPT University — Hanoi, August 2026

#### Visual Layout & Guidelines

* **Tone màu chủ đạo:** Nền tối (Dark Slate Blue / Deep Charcoal), màu nhấn Vàng Neon / Amber.
* **Bố cục:** Logo FPT University đặt góc trên bên trái. Tiêu đề chính in đậm ở trung tâm. Thông tin sinh viên & GVHD chia thành 2 khối cân đối bên dưới.
* **Sơ đồ thu nhỏ:** Đặt luồng tổng quan đơn giản bên dưới tiêu đề: `Meeting Audio Stream -> Structured Meeting Report`.

#### Speaker Script & Purpose

* **Mục đích:** Giới thiệu ngắn gọn tên đề tài, nhóm thực hiện và định vị 3 trụ cột: Tiếng Việt, Xử lý dạng Dòng (Streaming), và Báo cáo cuộc họp có cấu trúc.
* **Lời thoại:** "Kính chào Hội đồng, nhóm chúng tôi xin trình bày đồ án tốt nghiệp với đề tài: Tóm tắt cuộc họp tiếng Việt dạng dòng dựa trên phân đoạn chủ đề đa tỷ lệ và tóm tắt phân cấp."

---

### Slide 2 — Table of Contents

#### Content on Slide

> **TABLE OF CONTENTS (MỤC LỤC BÁO CÁO)**
>
> **01. INTRODUCTION (MỞ ĐẦU)**
>
> * Bối cảnh, Bài toán, Thách thức & Khoảng trống nghiên cứu.
> * Mục tiêu & 5 Đóng góp chính của khóa luận.
>
> **02. RELATED WORK (NGHIÊN CỨU LIÊN QUAN)**
>
> * Tổng quan ASR, Diarization, Summarization & Segmentation.
> * Bảng so sánh đối chiếu phương pháp.
>
> **03. METHODOLOGY (PHƯƠNG PHÁP LUẬN)**
>
> * Quy trình tổng thể 5 mô-đun nối tiếp.
> * Thuật toán Multi-Scale Sliding TextTiling.
> * Tóm tắt phân cấp với ViT5 & BARTpho.
>
> **04. DATASETS (BỘ DỮ LIỆU)
>
> - bộ dữ liệu ASR**
>
> * Bộ dữ liệu AliMeeting4MUG-Vi cho tóm tắt & tạo tiêu đề.
> * Các tập dữ liệu chuyển ngữ & Benchmark phân đoạn chủ đề.
>
> **05. EXPERIMENTS & RESULTS (THỰC NGHIỆM VÀ KẾT QUẢ)**
>
> * Đánh giá định lượng ASR và Phân đoạn chủ đề.
> * Đánh giá Tóm tắt khối (ViT5) & Tạo tiêu đề (BARTpho).
> * Phân tích lỗi & Đánh giá toàn bộ hệ thống.
>
> **06. CONCLUSION & LIVE DEMO (KẾT LUẬN VÀ DEMO)**
>
> * Tổng kết đóng góp chính & Lộ trình phát triển.
> * Minh họa hệ thống chạy thực tế (Live Demo).

#### Visual Layout & Guidelines

* **Bố cục 2 cột dạng Card cân đối:**
  * Cột trái: Phần 01, 02, 03.
  * Cột phải: Phần 04, 05, 06.
* **Yêu cầu:** Trình bày 6 khối rõ ràng tương ứng với đúng 6 chương/nội dung trọng tâm trong báo cáo khóa luận.

#### Speaker Script & Purpose

* **Mục đích:** Cung cấp lộ trình bài trình bày 6 phần chính bám sát từng chương trong khóa luận giúp Hội đồng nắm rõ luồng báo cáo.
* **Lời thoại:** "Bài trình bày hôm nay của nhóm bám sát cấu trúc khóa luận gồm 6 phần chính: Mở đầu & Đóng góp, Nghiên cứu liên quan, Phương pháp luận, Bộ dữ liệu, Thực nghiệm & Kết quả, và cuối cùng là Kết luận cùng phần Live Demo hệ thống."

---

### Slide 3 — Introduction (Section Divider)

#### Content on Slide

> **01**
> **INTRODUCTION**

#### Visual Layout & Guidelines

* **Bố cục:** Màn hình chuyển phần với số **01** kích thước rất lớn trên nền họa tiết lưới tối giản, chữ **INTRODUCTION** căn giữa.
* **Thời gian hiển thị:** 2 — 3 giây.

---

### Slide 4 — Motivation

#### Section Banner & Title

`SECTION 1: INTRODUCTION`
**Motivation & Practical Need**

#### Content on Slide

> **Thực trạng & Thách thức:**
>
> * Cuộc họp chứa nhiều quyết định quan trọng, công việc được giao và kế hoạch triển khai.
> * Băng ghi âm thô rất khó tìm kiếm, chia sẻ và khai thác lại thông tin.
> * Ghi biên bản thủ công tốn thời gian, dễ bỏ sót nội dung và thiếu tính nhất quán.
> * Các hệ thống tóm tắt ngoại tuyến (Offline) chỉ trả kết quả sau khi cuộc họp đã kết thúc hoàn toàn.
>
> **Nhu cầu cấp thiết:**
> Xây dựng giải pháp tạo báo cáo cuộc họp tiếng Việt theo thời gian thực (Incremental Report), cập nhật liên tục trong khi cuộc họp đang diễn ra.

#### Visual Layout & Guidelines

* **Bố cục 2 cột:**
  * **Cột trái:** 4 dòng thực trạng dạng thẻ chữ rõ ràng.
  * **Cột phải:** Sơ đồ so sánh giữa *Khai thác thủ công/Offline* (Độ trễ cao, tốn nguồn lực) và *Xử lý Streaming* (Cập nhật tức thì, có cấu trúc).
  * **Chân slide:** Khối nổi bật chứa nội dung "Nhu cầu cấp thiết" (Need).

#### Speaker Script & Purpose

* **Mục đích:** Trả lời câu hỏi trọng tâm: *Tại sao bài toán này cần được giải quyết?*
* **Lời thoại:** "Các cuộc họp tạo ra lượng lớn thông tin giá trị nhưng âm thanh thô rất khó tra cứu. Tóm tắt thủ công hay hệ thống ngoại tuyến đều chịu độ trễ lớn. Nhóm đặt ra mục tiêu chuyển đổi luồng âm thanh cuộc họp thành báo cáo cấu trúc được cập nhật liên tục."

---

### Slide 5 — Problem Statement and Challenges

#### Section Banner & Title

`SECTION 1: INTRODUCTION`
**Problem Statement & Technical Challenges**

#### Content on Slide

> **Input:** Continuous Vietnamese meeting audio stream
>
> **Processing Pipeline:**
> Audio Preprocessing -> Speaker Diarization -> ASR -> Topic Segmentation -> Hierarchical Summarization
>
> **Output:**
>
> * Topic Titles (Tiêu đề chủ đề)
> * Chunk-level Summaries (Tóm tắt đoạn)
> * Speaker Labels & Timestamps (Nhãn người nói và mốc thời gian)
>
> **Main Technical Challenges:**
>
> * Multi-speaker Audio: Nhiễu môi trường, đè tiếng giữa các speaker.
> * Context Limitation: Cuộc họp kéo dài vượt giới hạn ngữ cảnh của các mô hình ngôn ngữ.
> * Stream Uncertainty: Ranh giới chủ đề không chắc chắn khi chưa có toàn bộ ngữ cảnh tương lai.
> * Low-Resource Vietnamese: Thiếu hụt bộ dữ liệu tóm tắt cuộc họp chuẩn cho tiếng Việt.

#### Visual Layout & Guidelines

* **Nửa trên:** Sơ đồ khối pipeline 3 bước: Input -> Core Pipeline -> Output.
* **Nửa dưới:** 4 khối chữ hình chữ nhật tương ứng với 4 thách thức kỹ thuật cốt lõi.

#### Speaker Script & Purpose

* **Mục đích:** Định nghĩa rõ ràng bài toán hệ thống cần xử lý và các rào cản kỹ thuật chính.
* **Lời thoại:** "Đầu vào của hệ thống là luồng âm thanh liên tục và đầu ra là báo cáo cuộc họp phân cấp. Thách thức lớn nhất không chỉ nằm ở nhận dạng tiếng nói, mà còn ở việc xác định chính xác ranh giới chủ đề khi ngữ cảnh phía sau chưa xuất hiện đầy đủ."

---

### Slide 6 — Related Works and Literature Taxonomy

#### Section Banner & Title

`SECTION 1: INTRODUCTION`
**Related Works & Research Gap**

#### Content on Slide

> **01. Speech & Diarization:** Conformer/Zipformer (Yao 2023), Whisper (Radford 2023), PyAnnote, WeSpeaker. *(Hạn chế: Chủ yếu xử lý file offline, dễ trễ khi streaming tiếng Việt)*.
>
> **02. Dialogue Summarization:** BART (Lewis 2020), ViT5 (Phan 2022), BARTpho (Nguyen 2022), Hierarchical Recap (Asthana 2025). *(Hạn chế: Dễ bị hiện tượng Lost-in-the-Middle trên hội thoại dài)*.
>
> **03. Topic Segmentation:** TextTiling (Hearst 1997), C99 (Choi 2000), TopicTiling (Riedl 2012). *(Hạn chế: Thất bại trên luồng streaming do thiếu ngữ cảnh tương lai)*.
>
> **Comparison Matrix (Bảng so sánh đối chiếu):**
>
> * **Offline Summarization (Zhong 2021):** Offline mode • Single-chunk • Lack of Vietnamese resources.
> * **Commercial Cloud API (Recap/Otter):** Cloud-dependent • High cost • Data privacy risks.
> * **Proposed Pipeline (Đồ án đề xuất):** **Real-time Streaming • Multi-Scale TextTiling • ViT5/BARTpho • Local Deployment**.

#### Visual Layout & Guidelines

* **Bố cục 2 phần:**
  * **Nửa trên:** 3 khối Card phân loại theo 3 nhóm nghiên cứu (ASR, Summarization, Segmentation).
  * **Nửa dưới:** Bảng so sánh 3 cột (Offline vs Cloud vs Proposed Pipeline) bối cảnh hóa trực tiếp khoảng trống nghiên cứu.
* **Chân slide:** Trích dẫn tham khảo chuẩn IEEE: *Hearst (1997), Choi (2000), Raffel (2020), Zhong (2021), Phan et al. (2022), Yao et al. (2023), Asthana et al. (2025).*

#### Speaker Script & Purpose

* **Mục đích:** Tổng quan và phân loại có hệ thống các nghiên cứu trước đây, khẳng định sự vượt trội và tính mới của giải pháp đề xuất.
* **Lời thoại:** "Chúng tôi tổng hợp nghiên cứu liên quan theo 3 trục chính: Âm thanh, Tóm tắt và Phân đoạn. So với các giải pháp Offline hay Cloud thương mại, đồ án lấp đầy khoảng trống nghiên cứu bằng một pipeline Streaming hoàn chỉnh, phân đoạn đa tỷ lệ và triển khai cục bộ bảo mật cho tiếng Việt."

---

### Slide 7 — Contributions

#### Section Banner & Title

`SECTION 1: INTRODUCTION`
**Key Contributions**

#### Content on Slide

> **01. Unified Streaming Architecture**
> Đề xuất kiến trúc 5 mô-đun xử lý dạng dòng cho cuộc họp tiếng Việt.
>
> **02. Multi-Scale Sliding TextTiling**
> Thuật toán phân đoạn chủ đề tăng tiến dựa trên trượt ngữ cảnh đa tỷ lệ và Z-score cục bộ.
>
> **03. Fine-tuned Generation Models**
> Huấn luyện chuyên biệt ViT5 cho tóm tắt đoạn và BARTpho cho sinh tiêu đề chủ đề.
>
> **04. Vietnamese Meeting Resources**
> Xây dựng bộ dữ liệu huấn luyện và đánh giá chuyển ngữ cho các bài toán phân đoạn và tóm tắt.
>
> **05. Quantitative Empirical Evaluation**
> Đánh giá ASR trên bốn tập tiếng Việt và đánh giá ba tác vụ xử lý văn bản: phân đoạn chủ đề, tóm tắt đoạn và sinh tiêu đề.
>
> *(Ghi chú phạm vi: Phân định người nói đã được tích hợp ở mức kiến trúc nhưng chưa có bộ dữ liệu và đánh giá DER trong báo cáo này).*

#### Visual Layout & Guidelines

* **Bố cục:** Khối khung lớn dạng tấm card, sử dụng tiêu đề nổi bật cho từng đóng góp.
* **Lưu ý:** Không đưa đoạn văn dài, chỉ dùng dòng tóm tắt ngắn. Khối ghi chú phạm vi đặt ở góc dưới với kiểu chữ nhỏ hơn.

#### Speaker Script & Purpose

* **Mục đích:** Tuyên bố minh bạch 5 đóng góp của đồ án và làm rõ ranh giới kết quả thực nghiệm.
* **Lời thoại:** "Đóng góp chính của nhóm bao gồm kiến trúc pipeline 5 mô-đun, thuật toán phân đoạn trượt đa tỷ lệ, hai mô hình sinh văn bản ViT5 và BARTpho được tinh chỉnh, cùng đánh giá ASR và ba tác vụ xử lý văn bản."

---

### Slide 8 — Methodology (Section Divider)

#### Content on Slide

> **02**
> **METHODOLOGY**

#### Visual Layout & Guidelines

* **Bố cục:** Màn hình chuyển phần với số **02** kích thước lớn trên nền tối.
* **Thời gian hiển thị:** 2 — 3 giây.

---

### Slide 9 — Overall System Architecture

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**Overall System Architecture**

#### Content on Slide

> **Interface & API Layer:**
> Web Client, giao tiếp qua WebSocket, REST API và Server-Sent Events (SSE).
>
> **Application & AI Service Layer:**
> Streaming Orchestrator quản lý trạng thái phiên họp và điều phối sự kiện theo thứ tự.
>
> **Local Model Runtime Layer:**
> Thực thi mô hình cục bộ với ONNX / sherpa-onnx, PyTorch và Transformers tăng tốc qua CUDA.
>
> **Tổ chức thiết kế đảm bảo khả năng bảo mật dữ liệu và thay thế mô hình độc lập.**

#### Visual Layout & Guidelines

* **Bố cục 2 phần:**
  * **Bên trái:** Mô tả 3 tầng kiến trúc hệ thống.
  * **Bên phải:** Sơ đồ kiến trúc phần mềm tổng thể (Trích xuất từ **Figure 2** trong Báo cáo).

#### Speaker Script & Purpose

* **Mục đích:** Chứng minh đây là một hệ thống phần mềm hoàn chỉnh có phân tầng rõ ràng từ giao diện đến môi trường thực thi mô hình.
* **Lời thoại:** "Hệ thống được thiết kế theo 3 tầng chính: Tầng giao tiếp Web/API, Tầng dịch vụ điều phối phiên họp, và Tầng thực thi mô hình cục bộ nhằm đảm bảo tính riêng tư và khả năng mở rộng."

---

### Slide 10 — Processing Pipeline

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**Five-Module Processing Pipeline**

#### Content on Slide

> **01. Audio Preprocessing:** Chuẩn hóa khung PCM 16kHz và loại bỏ vùng không chứa tiếng nói.
> **02. Speaker Diarization:** Phân chia đoạn thoại và gán nhãn người nói.
> **03. Automatic Speech Recognition (ASR):** Chuyển đổi âm thanh thành văn bản có timestamp.
> **04. Topic Segmentation:** Phát hiện ranh giới chủ đề và chốt đoạn ổn định.
> **05. Hierarchical Summarization:** Sinh tóm tắt cho từng chunk và tạo tiêu đề chủ đề.
>
> **Final Meeting Report Structure:**
> Topic Title -> Chunk Summaries -> Speaker Labels & Timestamps
>
> *(Trạng thái thực nghiệm: ASR và các mô-đun 4–5 đã có đánh giá định lượng; phân định người nói mới được tích hợp ở mức kiến trúc).*

#### Visual Layout & Guidelines

* **Bố cục:** Sơ đồ dòng chảy ngang 5 bước. Dùng mã màu phân biệt:
  * **Màu Xám/Trung tính:** Tiền xử lý âm thanh và phân định người nói.
  * **Màu Vàng Neon/Nổi bật:** ASR, phân đoạn và tóm tắt là các mô-đun đã có kết quả thực nghiệm.

#### Speaker Script & Purpose

* **Mục đích:** Cung cấp cái nhìn toàn cảnh về luồng dữ liệu từ tín hiệu âm thanh đến báo cáo hoàn chỉnh.
* **Lời thoại:** "Luồng xử lý đi từ chuẩn hóa âm thanh, nhận diện người nói, chuyển văn bản, đến phân đoạn chủ đề và tóm tắt phân cấp. Báo cáo đánh giá định lượng ASR và ba mô-đun xử lý văn bản; phân định người nói là phần đang tiếp tục hoàn thiện."

---

### Slide 11 — ASR Data Preparation and Recognition

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**ASR: Data Preparation & Recognition Flow**

#### Content on Slide

> **01. Voice Activity Detection:** Silero VAD loại bỏ vùng không chứa tiếng nói; ngắt đoạn khi im lặng tối thiểu 500 ms.
>
> **02. Pseudo-label Generation:** Whisper Medium và Whisper Large-v3 chép lời độc lập, dùng beam size 2 và mốc thời gian cấp từ. Các đoạn ngắn hơn 2 giây hoặc dài hơn 20 giây được loại bỏ.
>
> **03. Quality Filtering:** Hai bản chép lời được chuẩn hóa thống nhất; chỉ giữ đoạn có $WER(T_{Medium}, T_{Large-v3}) < 5\%$.
>
> **04. Training and Inference Data:** Tạo 90 giờ dữ liệu phòng họp có nhãn giả; tập Custom 10h được gán nhãn lại thủ công. Âm thanh được chuẩn hóa về PCM WAV 16 kHz, mono.
>
> **Output:** Zipformer ASR sinh văn bản kèm thời gian để đưa vào các mô-đun phía sau.

#### Visual Layout & Guidelines

* **Bố cục:** Sơ đồ dòng chảy 4 bước từ âm thanh thô đến văn bản có thời gian. Làm nổi bật ngưỡng WER 5% ở bước lọc để thể hiện cơ chế kiểm soát chất lượng dữ liệu.

#### Speaker Script & Purpose

* **Mục đích:** Làm rõ cách tạo dữ liệu ASR và cách văn bản đầu ra được tạo cho pipeline.
* **Lời thoại:** "Dữ liệu ASR được tạo theo quy trình kiểm soát chất lượng: VAD tách vùng lời nói, hai mô hình Whisper sinh nhãn giả độc lập, sau đó chỉ giữ các đoạn mà hai bản chép lời đồng thuận dưới ngưỡng WER 5%. Tập Custom 10h được gán nhãn thủ công để đánh giá trong điều kiện phòng họp."

---

### Slide 12 — Speaker Diarization in the Pipeline

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**Speaker Diarization: Role in the Processing Flow**

#### Content on Slide

> **Input:** Các đoạn tiếng nói đã qua VAD.
>
> **Speaker Representation:** WeSpeaker trích xuất đặc trưng giọng nói để phục vụ phân định người nói.
>
> **Alignment:** Nhãn người nói được liên kết với mốc thời gian và văn bản ASR của từng lượt lời.
>
> **Downstream Use:** Lượt lời có nhãn người nói được chuyển sang phân đoạn chủ đề và xuất trong biên bản cuối, giúp xác định ai đã phát biểu nội dung nào.
>
> *(Phạm vi: Chưa có dữ liệu nhãn chuẩn và đánh giá DER/JER; phần này mô tả luồng tích hợp, không phải kết quả định lượng.)*

#### Visual Layout & Guidelines

* **Bố cục:** Sơ đồ ngắn gồm `VAD segments → WeSpeaker features → Speaker labels + ASR timestamps → Topic Segmentation / Final Report`. Dùng màu xám cho ghi chú giới hạn ở chân slide.

#### Speaker Script & Purpose

* **Mục đích:** Làm rõ vị trí và giá trị của nhãn người nói trong hệ thống, đồng thời nêu đúng phạm vi thực nghiệm.
* **Lời thoại:** "Phân định người nói nhận các đoạn đã qua VAD, sử dụng WeSpeaker để tạo đặc trưng giọng nói và liên kết nhãn người nói với văn bản ASR. Nhãn này giúp biên bản giữ được ngữ cảnh người phát biểu. Do chưa có tập nhãn chuẩn, nhóm chưa báo cáo DER hoặc JER."

---

### Slide 13 — Why Original TextTiling Is Insufficient

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**Limitations of Original TextTiling in Streaming Dialogue**

#### Content on Slide

> **Đặc điểm của hội thoại cuộc họp:**
>
> * Lượt lời (Utterances) ngắn và thưa thớt từ vựng (Lexically sparse).
> * Sự chuyển dịch chủ đề diễn ra đột ngột hoặc đan xen giữa các nhân vật.
>
> **Hạn chế của TextTiling nguyên bản (Hearst, 1997):**
>
> * Không thể tính toán ngưỡng toàn cục (Global threshold) khi dữ liệu đang chảy theo dòng.
> * Ứng viên ranh giới ở cuối cửa sổ trượt bị thiếu ngữ cảnh tương lai (Right context).
> * Các ranh giới quá gần nhau tạo ra đoạn ngắn, không đủ thông tin để tóm tắt.
>
> **Yêu cầu cải tiến:**
> Đo điểm đa tỷ lệ · Chuẩn hóa Z-score cục bộ · Gộp đoạn ngắn · Cơ chế hoãn chốt ranh giới (Delayed commitment).

#### Visual Layout & Guidelines

* **Bố cục:** Sơ đồ chuyển đổi từ *Hạn chế của phương pháp gốc* -> *Giải pháp cải tiến đề xuất*.
* **Điểm nhấn:** Làm nổi bật sự khác biệt giữa văn bản tài liệu dài (Offline Document) và luồng thoại cuộc họp (Streaming Dialogue).

#### Speaker Script & Purpose

* **Mục đích:** Lý giải nguyên do kỹ thuật bắt buộc nhóm phải cải tiến TextTiling thay vì áp dụng nguyên bản.
* **Lời thoại:** "TextTiling truyền thống giả định tài liệu hoàn chỉnh và đoạn văn dài. Với hội thoại cuộc họp dạng dòng, các câu thoại ngắn và việc thiếu ngữ cảnh tương lai đòi hỏi một cơ chế đánh giá đa tỷ lệ và chuẩn hóa cục bộ."

---

### Slide 14 — Multi-Scale Sliding TextTiling

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**Multi-Scale Sliding TextTiling Algorithm**

#### Content on Slide

> **01. Context Aggregation:** Gom các lượt lời lân cận bên trái và phải của từng khe hở (gap).
> **02. Lexical Cohesion:** Tính độ tương đồng Cosine giữa 2 khối ngữ cảnh kề nhau.
> **03. Multi-Scale Depth:** Đánh giá độ sâu thung lũng độ kết nối ở nhiều bán kính $R$.
> **04. Adaptive Candidate Selection:** Chuẩn hóa điểm Z-score và áp dụng ngưỡng thích ứng cục bộ.
> **05. Boundary Refinement:** Gộp các phân đoạn ngắn bất thường và chốt ranh giới ổn định.
>
> **Hyperparameters:**
> Radii $R = \{3, 5, 10, 15, 20\}$ | Window Size $W = 40$ | Stride $S = 5$ | Threshold factor $\alpha = 1.2$ | Min segment factor $\gamma = 0.20$

#### Visual Layout & Guidelines

* **Bố cục 2 cột:**
  * **Cột trái:** Quy trình 5 bước cải tiến dạng danh sách logic.
  * **Cột phải:** Sơ đồ quy trình chi tiết (Trích từ **Figure 3** trong Báo cáo).
  * **Chân slide:** Dòng thông số siêu tham số được đóng khung gọn gàng.

#### Speaker Script & Purpose

* **Mục đích:** Trình bày 5 bước cốt lõi của thuật toán phân đoạn chủ đề do nhóm đề xuất.
* **Lời thoại:** "Thuật toán giải quyết bài toán qua 5 bước: Gom ngữ cảnh, tính độ kết nối từ vựng, đo độ sâu thung lũng ở nhiều bán kính, lọc ngưỡng Z-score cục bộ và gộp đoạn ngắn trước khi chốt ranh giới."

---

### Slide 15 — Adaptive Boundary Detection

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**Adaptive Boundary Detection Formulations**

#### Content on Slide

> **01. Lexical Cohesion Score:**
>
> $$
> S_i = \frac{\mathbf{L}_i^\top \mathbf{R}_i}{\lVert\mathbf{L}_i\rVert_2 \lVert\mathbf{R}_i\rVert_2 + \varepsilon}
> $$
>
> **02. Multi-Scale Depth Score:**
>
> $$
> D_r(i) = \frac{p_L(i,r) + p_R(i,r) - 2S_i}{2}
> $$
>
> **03. Local Z-Score Normalization & Candidate Condition:**
>
> $$
> \bar{D}(i) > \mu_{\bar{D}} + \alpha \sigma_{\bar{D}}
> $$
>
> **04. Dynamic Minimum Segment Length:**
>
> $$
> m_{\min} = \max(2, \lfloor\gamma M\rfloor)
> $$
>
> **Ý nghĩa:** Ngưỡng quyết định tự động điều chỉnh linh hoạt theo từng cửa sổ trượt ngữ cảnh.

#### Visual Layout & Guidelines

* **Bố cục:** Trình bày các công thức LaTeX rõ ràng, có nhãn tiêu đề cho từng công thức.
* **Minh họa:** Ghép hình ảnh mô phỏng độ sâu thung lũng (Hình 4) và ngưỡng thích ứng (Hình 5).

#### Speaker Script & Purpose

* **Mục đích:** Giải thích toán học cốt lõi của cơ chế tự điều chỉnh ngưỡng trong phân đoạn.
* **Lời thoại:** "Độ kết nối Cosine được đo ở nhiều bán kính để tính điểm độ sâu thung lũng. Ngưỡng chọn ranh giới ứng viên dựa trên Z-score trung bình của chính cửa sổ hiện tại, giúp hệ thống thích ứng với sự thay đổi mật độ từ vựng."

---

### Slide 16 — Streaming Boundary Confirmation

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**Streaming Boundary Confirmation Mechanism**

#### Content on Slide

> **Trạng thái ranh giới:** `Candidate` -> `Pending` -> `Committed`
>
> **Quy tắc chốt ranh giới (Commitment Rule):**
> Một ranh giới ứng viên $g$ chỉ được chốt chính thức (Committed) khi thỏa mãn:
>
> $$
> g \le s_t + W - L
> $$
>
> * $W = 40$: Độ dài cửa sổ trượt (Window size).
> * $S = 5$: Bước trượt (Stride).
> * $L = 20$: Ngữ cảnh quan sát tương lai (Lookahead context).
>
> **Đặc tính:**
>
> * Ranh giới ở vùng `Pending` liên tục được đánh giá lại qua các cửa sổ đè phủ.
> * Ranh giới đã `Committed` là cố định tuyệt đối, kích hoạt ngay tiến trình tóm tắt đoạn.
> * Thao tác `Flush` giải phóng và chốt đoạn cuối cùng khi kết thúc cuộc họp.

#### Visual Layout & Guidelines

* **Bố cục 2 phần:**
  * **Bên trái:** Định nghĩa trạng thái và điều kiện toán học.
  * **Bên phải:** Hình ảnh minh họa trượt cửa sổ và vùng Lookahead (Trích từ **Figure 6**).

#### Speaker Script & Purpose

* **Mục đích:** Làm rõ khái niệm "Streaming" và cơ chế hoãn chốt ranh giới để đảm bảo độ chính xác.
* **Lời thoại:** "Để tránh quyết định vội vàng khi chưa đủ thông tin, hệ thống duy trì vùng nhìn trước Lookahead. Ranh giới chỉ được chốt hoàn toàn khi đã nằm ngoài vùng hoãn, đánh đổi một độ trễ cố định để lấy sự ổn định."

---

### Slide 17 — Hierarchical Summarization

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**Hierarchical Summarization Architecture**

#### Content on Slide

> **Luồng phân cấp (Hierarchical Flow):**
>
> $$
> \text{Topic Segment} \longrightarrow \text{Utterance Chunks} \longrightarrow \text{Chunk Summaries} \longrightarrow \text{Topic Title}
> $$
>
> **Quy tắc chia nhỏ & Tóm tắt:**
>
> * Mỗi phân đoạn chủ đề (Topic Segment) được chia thành các Chunk không đè phủ.
> * Kích thước tối đa: **8 lượt lời (Utterances)** cho mỗi Chunk.
> * **ViT5:** Sinh bản tóm tắt chi tiết cho từng Chunk riêng biệt.
> * **BARTpho:** Tổng hợp chuỗi tóm tắt Chunk để sinh tiêu đề tổng quát cho toàn bộ Topic.
> * Giữ nguyên mốc thời gian và nhãn người nói tương ứng.
>
> **Lợi ích:** Tránh vượt quá giới hạn độ dài đầu vào của LLM và giữ được chi tiết quan trọng.

#### Visual Layout & Guidelines

* **Bố cục:** Sơ đồ phân cấp cây hoặc khối sơ đồ phân tầng (Trích từ **Figure 7**).
* **Màu sắc:** Phân biệt rõ nhiệm vụ của ViT5 (Tóm tắt mức nhỏ) và BARTpho (Tóm tắt mức tổng quát).

#### Speaker Script & Purpose

* **Mục đích:** Trình bày lý do và cơ chế tóm tắt 2 cấp để xử lý các cuộc họp dài.
* **Lời thoại:** "Chiến lược phân cấp giúp giải quyết bài toán giới hạn ngữ cảnh. Phân đoạn chủ đề được chia nhỏ thành các chunk 8 lượt lời cho ViT5 tóm tắt chi tiết, sau đó BARTpho tổng hợp các bản tóm tắt đó thành tiêu đề chủ đề."

---

### Slide 18 — ViT5 and BARTpho Task Design

#### Section Banner & Title

`SECTION 2: METHODOLOGY`
**Model Configurations for Generation Tasks**

#### Content on Slide

> **ViT5 — Chunk Summarization**
>
> * **Nhiệm vụ:** Tóm tắt ngắn gọn các ý chính trong Chunk 8 câu thoại.
> * **Định dạng Prompt:** `Tóm tắt: <speaker>: <utterance> ...`
> * **Cấu hình:** Input 512 / Output 128 tokens | Beam Search = 4 | No 3-gram repetition.
> * **Quy mô:** ~226M thông số (Fine-tuned trên AliMeeting4MUG-Vi).
>
> **BARTpho — Topic Titling**
>
> * **Nhiệm vụ:** Sinh tiêu đề đại diện cho toàn bộ phân đoạn chủ đề.
> * **Định dạng Prompt:** `Tạo tiêu đề: <summary 1> / ... / <summary m>`
> * **Cấu hình:** Input 1,024 / Output 200 tokens | Beam Search = 4 | Lấy 1,500 ký tự cuối.
> * **Quy mô:** ~132M thông số (Fine-tuned trên AliMeeting4MUG-Vi).

#### Visual Layout & Guidelines

* **Bố cục 2 cột song song:** So sánh trực quan về Input format, Output format, Hyperparameters và Model Size giữa ViT5 và BARTpho.
* **Chân slide:** Trích dẫn các nghiên cứu gốc về ViT5 (Phan et al., 2022) và BARTpho (Tran et al., 2022).

#### Speaker Script & Purpose

* **Mục đích:** Cung cấp thông số kỹ thuật chi tiết của hai mô hình sinh ngôn ngữ được sử dụng.
* **Lời thoại:** "Nhóm tinh chỉnh hai mô hình chuyên biệt: ViT5 đóng vai trò rút gọn chi tiết hội thoại, trong khi BARTpho tiếp nhận các bản tóm tắt thành phần để khái quát hóa thành tiêu đề đại diện."

---

### Slide 19 — Experiment (Section Divider)

#### Content on Slide

> **03**
> **EXPERIMENT**

#### Visual Layout & Guidelines

* **Bố cục:** Màn hình chuyển phần với số **03** kích thước lớn trên nền tối.
* **Thời gian hiển thị:** 2 — 3 giây.

---

### Slide 20 — Datasets and Evaluation Scope

#### Section Banner & Title

`SECTION 3: EXPERIMENT`
**Datasets & Experimental Scope**

#### Content on Slide

> **Quy mô dữ liệu thử nghiệm:**
>
> | Task                          | Dataset                                                                         |                            Scale                            |
> | :---------------------------- | :------------------------------------------------------------------------------ | :---------------------------------------------------------: |
> | **ASR**                 | FLEURS, VIVOS, VLSP 2020, Custom 10h                                            | 4 tập kiểm thử tiếng Việt; khoảng 20,7 giờ âm thanh |
> | **Topic Segmentation**  | 6 Dialogue & Meeting Corpora*(AMI, ICSI, QMSum, DialSeg711, Doc2Dial, TIAGE)* |     4,713 dialogues 198,914 utterances  18,001 segments     |
> | **Chunk Summarization** | AliMeeting4MUG-Vi                                                               |                 34,117 chunk-summary pairs                 |
> | **Topic Titling**       | AliMeeting4MUG-Vi                                                               |                     3,999 topic samples                     |
>
> **Phạm vi mô-đun âm thanh:** ASR được đánh giá bằng WER. Phân định người nói dùng WeSpeaker trong kiến trúc, nhưng chưa có tập đánh giá và chỉ số DER để báo cáo.
>
> **Tập đánh giá độc lập (Independent Evaluation Set):**
>
> * **ViT5:** 6,038 chunks trích xuất từ 65 cuộc họp độc lập.
> * **BARTpho:** 736 topics trích xuất từ 65 cuộc họp độc lập.
>
> *(Lưu ý dữ liệu: Các bộ dữ liệu được dịch sang tiếng Việt và chuẩn hóa. Chất lượng dịch thuật chưa được đánh giá độc lập).*

#### Visual Layout & Guidelines

* **Bố cục:** Bảng dữ liệu gọn gàng ở nửa trên, nửa dưới nêu rõ phạm vi ASR, Speaker Diarization và tập test độc lập 65 cuộc họp.
* **Ghi chú:** Dòng lưu ý về giới hạn dữ liệu dịch thuật được in nghiêng ở góc chân trang.

#### Speaker Script & Purpose

* **Mục đích:** Minh bạch quy mô dữ liệu, phạm vi đánh giá từng mô-đun và tập test độc lập.
* **Lời thoại:** "ASR được kiểm thử trên bốn tập tiếng Việt, trong đó có tập phòng họp Custom 10h. Phân đoạn sử dụng sáu bộ dữ liệu hội thoại chuẩn, còn các mô hình sinh văn bản được kiểm thử độc lập trên 65 cuộc họp của AliMeeting."

---

### Slide 21 — ASR Results

#### Section Banner & Title

`SECTION 3: EXPERIMENT`
**ASR: Evaluation Setup & Results**

#### Content on Slide

> **Nhận dạng tiếng nói (ASR):**
>
> * Mô hình đánh giá: **Zipformer SSL 100h** (68M tham số), tinh chỉnh cho miền tiếng Việt.
> * Đối chiếu với Whisper Tiny/Small/Medium/Large-v3 và Zipformer 30M huấn luyện 6.000 giờ.
> * Chỉ số: **Word Error Rate (WER) \downarrow**; so sánh sau khi chuẩn hóa văn bản thống nhất.
> * Tập Custom 10h phản ánh điều kiện phòng họp: nói đè, âm thanh nén và độ vang.
>
> | Model                        | FLEURS WER (%) |  VIVOS WER (%) | VLSP 2020 WER (%) | Custom 10h WER (%) |
> | :--------------------------- | -------------: | -------------: | ----------------: | -----------------: |
> | Whisper Tiny                 |          79,12 |          79,15 |             80,76 |             152,71 |
> | Whisper Small                |          21,15 |          22,22 |             29,47 |              20,77 |
> | Whisper Medium               |          12,23 |          18,98 |             24,07 |              12,17 |
> | Whisper Large-v3             | **7,86** |          16,78 |             32,12 |              19,63 |
> | **Zipformer SSL 100h** |          10,71 |           6,23 |             10,47 |               9,37 |
> | Zipformer 30M 6000h          |           9,23 | **4,64** |    **9,98** |     **6,91** |
>
> *Zipformer SSL 100h cải thiện rõ trên Custom 10h so với các mô hình Whisper, nhưng chưa vượt mô hình Zipformer huấn luyện với 6.000 giờ dữ liệu.*

#### Visual Layout & Guidelines

* **Bố cục:** Bảng WER chiếm phần trung tâm; phía trên nêu thiết lập đánh giá, phía dưới đặt một thông điệp kết quả ngắn.

#### Speaker Script & Purpose

* **Mục đích:** Công bố rõ giao thức và kết quả ASR trên bốn tập kiểm thử tiếng Việt.
* **Lời thoại:** "Nhóm đánh giá Zipformer SSL 100h bằng WER trên bốn tập tiếng Việt. Trên tập phòng họp Custom 10h, mô hình đạt 9,37%, tốt hơn các mô hình Whisper trong so sánh, nhưng vẫn thấp hơn Zipformer được huấn luyện với quy mô 6.000 giờ."

---

### Slide 22 — Speaker Diarization: Current Scope

#### Section Banner & Title

`SECTION 3: EXPERIMENT`
**Speaker Diarization: Integrated, Not Yet Benchmarked**

#### Content on Slide

> **Vai trò trong hệ thống:** Gán nhãn người nói cho từng lượt lời để báo cáo cuối cùng giữ được ngữ cảnh phát biểu và phục vụ truy vết theo thời gian.
>
> **Thiết kế đã tích hợp:**
>
> * **WeSpeaker** trích xuất đặc trưng giọng nói từ các đoạn đã qua VAD.
> * Nhãn người nói được gắn cùng thời gian và văn bản ASR trước khi đưa vào phân đoạn chủ đề.
>
> **Phạm vi báo cáo hiện tại:**
>
> * Chưa có bộ dữ liệu gán nhãn người nói, cấu hình huấn luyện hay đánh giá **DER**.
> * Do đó, slide chỉ xác nhận mức tích hợp của mô-đun, không khẳng định chất lượng phân định người nói.
>
> **Bước tiếp theo:** xây dựng tập đánh giá tiếng Việt, đo DER/JER và đánh giá tác động của lỗi gán người nói lên tóm tắt cuối.

#### Visual Layout & Guidelines

* **Bố cục 3 khối nối tiếp:** Vai trò trong pipeline, trạng thái triển khai và phạm vi chưa đánh giá. Khối cuối dùng màu xám để thể hiện rõ đây là hướng phát triển.

#### Speaker Script & Purpose

* **Mục đích:** Trình bày trung thực trạng thái mô-đun phân định người nói và tránh diễn giải nó như một kết quả thực nghiệm.
* **Lời thoại:** "Phân định người nói đã được đưa vào luồng hệ thống để gắn người phát biểu cho từng lượt lời. Tuy nhiên, do chưa có bộ dữ liệu gán nhãn và đánh giá DER, nhóm chỉ báo cáo mức tích hợp kiến trúc; đây là hướng thực nghiệm ưu tiên tiếp theo."

---

### Slide 23 — Main Topic Segmentation Result

#### Section Banner & Title

`SECTION 3: EXPERIMENT`
**Main Topic Segmentation Results (Macro-Average)**

#### Content on Slide

> **THE PROPOSED METHOD ACHIEVES THE BEST MACRO-AVERAGE PERFORMANCE**
>
> | Method                                          | $P_k \downarrow$ | $WindowDiff \downarrow$ | $Macro-F_1 \uparrow$ |
> | :---------------------------------------------- | :----------------: | :-----------------------: | :--------------------: |
> | NLTK TextTiling                                 |       0.5431       |          0.7037          |         0.5641         |
> | Single-Scale Lexical TextTiling                 |       0.5409       |          0.7625          |         0.5579         |
> | **Multi-Scale Sliding TextTiling (Ours)** |  **0.5259**  |     **0.6531**     |    **0.6089**    |
>
> **Mức độ cải tiến so với NLTK TextTiling:**
>
> * Giảm tỷ lệ lỗi $P_k$: **-0.0172**
> * Giảm tỷ lệ lỗi $WindowDiff$: **-0.0506**
> * Tăng $Macro-F_1$: **+0.0448**
>
> *(Ghi chú: Kết quả là trung bình Macro trên 6 bộ dữ liệu. Phương pháp đề xuất đạt kết quả tốt nhất về trung bình nhưng không phải vượt trội trên mọi tập dữ liệu đơn lẻ).*

#### Visual Layout & Guidelines

* **Bảng kết quả trung tâm:** Tô màu nền nổi bật (Highlight Row) cho hàng phương pháp đề xuất.
* **3 khối chỉ số phóng to:** Đặt 3 khối thể hiện mức độ cải tiến (-0.0172, -0.0506, +0.0448).

#### Speaker Script & Purpose

* **Mục đích:** Công bố kết quả thực nghiệm quan trọng nhất của bài toán phân đoạn chủ đề.
* **Lời thoại:** "Trên điểm trung bình 6 bộ dữ liệu, phương pháp của nhóm đạt kết quả tốt nhất trên cả 3 chỉ số, giúp giảm đáng kể lỗi WindowDiff và nâng Macro-F1 lên mức 0.6089."

---

### Slide 24 — Ablation and Streaming Trade-off

#### Section Banner & Title

`SECTION 3: EXPERIMENT`
**Ablation Study & Streaming Trade-Off Analysis**

#### Content on Slide

> **Ablation Study (Đóng góp thành phần):**
>
> | Variant                                  | $Macro-F_1 \uparrow$ |
> | :--------------------------------------- | :--------------------: |
> | Lexical Baseline                         |         0.5579         |
> | + Sliding Window                         |         0.5544         |
> | + Local Z-score Normalization            |         0.5914         |
> | + Multi-Scale Depth                      |         0.5887         |
> | **+ Short-Segment Merging (Full)** |    **0.6089**    |
>
> **Batch vs. Streaming Mode Trade-Off:**
>
> | Mode                         | $Macro-F_1 \uparrow$ | $WindowDiff \downarrow$ |
> | :--------------------------- | :--------------------: | :-----------------------: |
> | **Batch (Offline)**    |    **0.6089**    |     **0.6531**     |
> | **Streaming (Online)** |         0.5863         |          0.7038          |
>
> * Tốc độ thuật toán: **0.0852 ms / lượt lời** (Chỉ tính thời gian thuật toán phân đoạn).
> * Độ trễ chốt ranh giới trung bình: **21.58 lượt lời**.

#### Visual Layout & Guidelines

* **Bố cục 2 cột:**
  * **Cột trái:** Bảng Ablation chỉ ra tác động của Z-score và gộp đoạn ngắn.
  * **Cột phải:** Bảng so sánh Batch vs Streaming và độ trễ thuật toán.

#### Speaker Script & Purpose

* **Mục đích:** Phân tích sâu thành phần đóng góp và sự đánh đổi khi chuyển sang chế độ Streaming.
* **Lời thoại:** "Phân tích Ablation cho thấy Z-score cục bộ và gộp đoạn ngắn là hai nhân tố đóng góp lớn nhất. Chế độ Streaming chấp nhận giảm nhẹ chất lượng phân đoạn để đổi lấy khả năng xuất kết quả tăng tiến."

---

### Slide 25 — Summarization and Titling Results

#### Section Banner & Title

`SECTION 3: EXPERIMENT`
**Generation Results: ViT5 & BARTpho**

#### Content on Slide

> **VIETNAMESE GENERATION MODELS GENERALIZE WELL TO INDEPENDENT MEETINGS**
>
> **ViT5 Chunk Summarization Card:**
>
> * Đánh giá trên **6,038 Chunks** từ 65 cuộc họp độc lập.
> * **ROUGE-1:** 0.7265
> * **ROUGE-2:** 0.4854
> * **ROUGE-L:** 0.5486
> * Best Checkpoint: Epoch 6 | Parameter size: ~226M.
>
> **BARTpho Topic Titling Card:**
>
> * Đánh giá trên **736 Topics** từ 65 cuộc họp độc lập.
> * **ROUGE-Max-1:** 0.5351
> * **ROUGE-Max-2:** 0.2830
> * **ROUGE-Max-L:** 0.4442
> * Best Checkpoint: Epoch 5 | Parameter size: ~132M.
>
> *(Ghi chú: Điểm số ViT5 và BARTpho dùng giao thức đánh giá khác nhau nên không so sánh trực tiếp với nhau).*

#### Visual Layout & Guidelines

* **Bố cục:** 2 tấm card lớn song song cho ViT5 và BARTpho.
* **Định dạng số:** Phóng to các chỉ số ROUGE chính để Hội đồng dễ quan sát.

#### Speaker Script & Purpose

* **Mục đích:** Trình bày kết quả định lượng của hai mô hình sinh ngôn ngữ trên tập dữ liệu kiểm thử.
* **Lời thoại:** "Hai mô hình thể hiện khả năng tổng quát hóa tốt trên 65 cuộc họp độc lập. ViT5 đạt ROUGE-L 0.5486 ở mức tóm tắt đoạn và BARTpho đạt ROUGE-Max-L 0.4442 ở mức sinh tiêu đề."

---

### Slide 26 — Representative Output and Error Analysis

#### Section Banner & Title

`SECTION 3: EXPERIMENT`
**Output Visual Demonstration & Qualitative Error Analysis**

#### Content on Slide

> **Trường hợp thành công (Successful Cases):**
>
> * **ViT5:** Bảo toàn chính xác kết luận cuộc họp về việc chính sách tài chính chưa đủ giải quyết vấn đề tư tưởng (Đạt $ROUGE-L = 0.9351$).
> * **BARTpho:** Sinh tiêu đề khớp hoàn toàn với mẫu human reference: *"Vấn đề liên quan đến việc mời người dẫn chương trình và khách mời"*.
>
> **Trường hợp thất bại & Hạn chế (Failure Cases):**
>
> * **ViT5 — Hallucination:** Xuất hiện thông tin bịa đặt về "thanh toán tiền mặt" trong đoạn thảo luận về thiết bị tập thể dục.
> * **BARTpho — Off-topic Title:** Sinh tiêu đề lệch sang "ngân sách khen thưởng" thay vì nội dung duy trì trật tự sinh viên.
>
> **Nhận xét rút ra:**
> Chỉ số ROUGE chưa phản ánh hết độ chính xác thực tế (Factual Consistency). Cần bổ sung đánh giá từ con người (Human Evaluation).

#### Visual Layout & Guidelines

* **Bố cục 2 cột:**
  * **Cột trái:** Khung màu xanh nhạt / xám cho trường hợp thành công.
  * **Cột phải:** Khung màu cảnh báo nhẹ cho trường hợp ảo giác (Hallucination) và lệch chủ đề.

#### Speaker Script & Purpose

* **Mục đích:** Thể hiện tính trung thực khoa học thông qua việc phân tích cả case thành công và trường hợp lỗi của mô hình.
* **Lời thoại:** "Bên cạnh các trường hợp tóm tắt chính xác, mô hình vẫn gặp hiện tượng bịa đặt thông tin hoặc sinh tiêu đề chưa bám sát ngữ cảnh. Điều này chỉ ra giới hạn của chỉ số ROUGE và nhu cầu đánh giá tính trung thực thực tế."

---

### Slide 27 — Conclusion (Section Divider)

#### Content on Slide

> **04**
> **CONCLUSION & FUTURE WORKS**

#### Visual Layout & Guidelines

* **Bố cục:** Màn hình chuyển phần với số **04** trên nền tối.
* **Thời gian hiển thị:** 2 — 3 giây.

---

### Slide 28 — Conclusion

#### Section Banner & Title

`SECTION 4: CONCLUSION`
**Conclusion & Key Achievements**

#### Content on Slide

> **Tóm tắt đóng góp chính:**
>
> * Thiết kế thành công kiến trúc dạng dòng 5 mô-đun phân tầng cho cuộc họp tiếng Việt.
> * Cải tiến thuật toán Multi-Scale Sliding TextTiling giúp phân đoạn chủ đề tăng tiến.
> * Tinh chỉnh thành công ViT5 cho tóm tắt đoạn và BARTpho cho sinh tiêu đề chủ đề.
> * Hoàn thành đánh giá định lượng cho ASR và ba bài toán xử lý văn bản.
>
> **Các chỉ số cốt lõi đạt được:**
>
> * **ASR (Custom 10h):** $WER = \mathbf{9,37\%}$ với Zipformer SSL 100h
> * **Topic Segmentation:** $Macro-F_1 = \mathbf{0.6089}$
> * **Chunk Summarization:** $ROUGE-L = \mathbf{0.5486}$
> * **Topic Titling:** $ROUGE-Max-L = \mathbf{0.4442}$
>
> **Kết luận:** Đồ án chứng minh tính khả thi về mặt kỹ thuật của bài toán tóm tắt cuộc họp dạng dòng cho tiếng Việt.

#### Visual Layout & Guidelines

* **Nửa trên:** 4 dòng tóm tắt đóng góp chính.
* **Nửa dưới:** 4 khối số lớn thể hiện WER trên Custom 10h cùng ba kết quả xử lý văn bản.

#### Speaker Script & Purpose

* **Mục đích:** Chốt lại những giá trị và chỉ số chính mà đồ án đã giải quyết được.
* **Lời thoại:** "Tóm lại, đồ án đã chứng minh tính khả thi của hệ thống tóm tắt cuộc họp dạng dòng tiếng Việt với kết quả ASR trên dữ liệu phòng họp và các kết quả định lượng cho phân đoạn, tóm tắt đoạn và sinh tiêu đề."

---

### Slide 29 — Future Works

#### Section Banner & Title

`SECTION 4: CONCLUSION`
**Limitations & Future Works**

#### Content on Slide

> **Hướng phát triển tiếp theo:**
>
> * **01. Speaker Benchmarking:** Xây dựng dữ liệu gán nhãn và đánh giá DER/JER cho mô-đun phân định người nói.
> * **02. End-to-End Latency:** Đo lường chi tiết độ trễ toàn hệ thống theo giây (bao gồm độ trễ mạng và sinh từ).
> * **03. Model Baselines:** So sánh ViT5/BARTpho với các mô hình ngôn ngữ lớn (LLM) mạnh hơn.
> * **04. Factuality & Quality:** Đánh giá chất lượng dịch thuật và tính xác thực của câu văn tóm tắt.
> * **05. Human Evaluation:** Tiến hành đánh giá từ người dùng thực tế trên các cuộc họp tiếng Việt thực địa.
> * **06. System Optimization:** Tối ưu hóa hiệu năng để triển khai mượt mà trên các thiết bị phần cứng hạn chế.

#### Visual Layout & Guidelines

* **Bố cục:** Thiết kế dạng 6 ô vuông / khối danh sách được đánh số rõ ràng từ 01 đến 06.
* **Yêu cầu:** Không dùng icon, viết câu súc tích.

#### Speaker Script & Purpose

* **Mục đích:** Thể hiện rõ nhóm nắm chắc các hạn chế hiện tại và có lộ trình phát triển rõ ràng.
* **Lời thoại:** "Trong thời gian tới, nhóm sẽ hoàn thiện thực nghiệm cho mô-đun âm thanh, đo độ trễ end-to-end, đánh giá tính xác thực thông tin và nâng cao hiệu năng triển khai ứng dụng."

---

### Slide 30 — Demo (Section Divider)

#### Content on Slide

> **05**
> **LIVE DEMO**

#### Visual Layout & Guidelines

* **Bố cục:** Màn hình chuyển phần với số **05** trên nền tối.
* **Thời gian hiển thị:** 2 — 3 giây.

---

### Slide 31 — Demo Scenario

#### Section Banner & Title

`SECTION 5: DEMO`
**Live Demonstration Flow**

#### Content on Slide

> **Quy trình 6 bước thực hiện Demo:**
>
> * **Step 1. Start Meeting:** Khởi tạo phiên họp (Thu âm trực tiếp hoặc tải file audio).
> * **Step 2. Audio Streaming:** Gửi các khung âm thanh PCM 16kHz liên tục lên Server qua WebSocket.
> * **Step 3. Transcript Update:** Hiển thị lượt lời nhận dạng kèm mốc thời gian và nhãn người nói.
> * **Step 4. Boundary Confirmation:** Chốt ranh giới chủ đề khi đủ ngữ cảnh Lookahead (`segment-closed`).
> * **Step 5. Report Generation:** Kích hoạt mô hình sinh tóm tắt đoạn và tiêu đề chủ đề.
> * **Step 6. Export Report:** Xuất báo cáo cuộc họp hoàn chỉnh dưới dạng văn bản cấu trúc.

#### Visual Layout & Guidelines

* **Bố cục:** Quy trình trôi ngang 6 bước có mũi tên kết nối đơn giản.
* **Bên phải:** Ảnh chụp màn hình giao diện ứng dụng Web thực tế.

#### Speaker Script & Purpose

* **Mục đích:** Hướng dẫn Hội đồng các bước sẽ diễn ra trong phần Demo sản phẩm (60 — 90 giây).
* **Lời thoại:** "Phần demo sau đây sẽ minh họa luồng hoạt động từ nhận âm thanh, cập nhật transcript, phát hiện ranh giới chủ đề đến xuất báo cáo tự động theo thời gian thực."

---

### Slide 32 — Thank You and Q&A

#### Content on Slide

> **THANK YOU FOR YOUR ATTENTION!**
> **Questions & Discussion**
>
> **Summary of Key Results:**
>
> * ASR on Custom 10h ($WER$): **9,37%**
> * Topic Segmentation ($Macro-F_1$): **0.6089**
> * Chunk Summarization ($ROUGE-L$): **0.5486**
> * Topic Titling ($ROUGE-Max-L$): **0.4442**
>
> **Capston Project 2026 | FPT University — Hanoi**

#### Visual Layout & Guidelines

* **Bố cục:** Chữ **THANK YOU** thiết kế lớn nổi bật ở giữa.
* **Phần trung tâm:** Giữ nguyên 3 kết quả chính để Hội đồng tiện quan sát và đặt câu hỏi trong suốt phần Q&A.

#### Speaker Script & Purpose

* **Mục đích:** Lời cảm ơn kết thúc phần thuyết trình và giữ lại thông tin quan trọng nhất.
* **Lời thoại:** "Nhóm xin chân thành cảm ơn thầy cô trong Hội đồng đã chú ý theo dõi. Nhóm sẵn sàng nhận câu hỏi và góp ý từ Hội đồng."

---

## III. SLIDE DỰ PHÒNG (BACKUP SLIDES)

*Các slide dự phòng nằm sau Slide 32, chỉ sử dụng khi Hội đồng truy vấn chi tiết.*

---

### Slide B1 — Selected References

#### Content on Slide

> **Core References:**
>
> * Hearst, M. A. (1997). *TextTiling: Segmenting text into multi-paragraph subtopic passages*. Computational Linguistics.
> * Phan, H., et al. (2022). *ViT5: Pre-trained Text-to-Text Transformer for Vietnamese Language Generation*. AACL-IJCNLP.
> * Tran, V., et al. (2022). *BARTpho: Pre-trained Sequence-to-Sequence Models for Vietnamese*. Interspeech.
> * Zhang, H., et al. (2023). *MUG: A Large-Scale Benchmark for Multi-Granularity Summarization*. EMNLP.
> * Zhong, M., et al. (2021). *QMSum: A New Benchmark for Query-based Meeting Summarization*. NAACL.
> * Xing, L., & Carenini, G. (2021). *Improving Dialogue Topic Segmentation via Multi-Task Learning*. EMNLP.
> * Asthana, A., et al. (2025). *Meeting Recap: A Real-time Streaming Summarization System*. arXiv.

---

### Slide B2 — Detailed Segmentation Results per Dataset

#### Content on Slide

> **Bảng chi tiết kết quả phân đoạn chủ đề trên từng dataset:**
>
> | Dataset              | NLTK$P_k$ | Single$P_k$ | **Ours $P_k \downarrow$** | NLTK$WD$ | Single$WD$ | **Ours $WD \downarrow$** | NLTK$F_1$ | Single$F_1$ | **Ours $F_1 \uparrow$** |
> | :------------------- | :---------: | :-----------: | :-------------------------------: | :--------: | :----------: | :------------------------------: | :---------: | :-----------: | :-----------------------------: |
> | **DialSeg711** |   0.4428   |    0.4285    |         **0.3812**         |   0.5401   |    0.5210    |         **0.4610**         |   0.6012   |    0.6120    |        **0.6580**        |
> | **Doc2Dial**   |   0.4812   |    0.4790    |         **0.4510**         |   0.6210   |    0.6800    |         **0.5912**         |   0.5810   |    0.5790    |        **0.6210**        |
> | **AMI**        |   0.5890   |    0.5910    |         **0.5620**         |   0.7810   |    0.8210    |         **0.7210**         |   0.5410   |    0.5380    |        **0.5890**        |
> | **QMSum**      |   0.5910   |    0.5880    |         **0.5710**         |   0.7910   |    0.8410    |         **0.7510**         |   0.5390   |    0.5310    |        **0.5780**        |
> | **ICSI**       |   0.6120   |    0.6100    |         **0.5910**         |   0.8120   |    0.8610    |         **0.7810**         |   0.5210   |    0.5180    |        **0.5610**        |
> | **TIAGE**      |   0.5427   |    0.5486    |         **0.5992**         |   0.5772   |    0.8417    |         **0.6101**         |   0.5990   |    0.5693    |        **0.5866**        |

---

### Slide B3 — Algorithm 1 Pseudocode

#### Content on Slide

> **Multi-Scale Sliding TextTiling Pseudocode Structure:**
>
> * **Update Phase:** Tiếp nhận câu thoại mới $u_t$, đẩy vào bộ đệm cửa sổ trượt $W$.
> * **Cohesion & Depth Phase:** Tính điểm Cosine trên bán kính $R = \{3,5,10,15,20\}$ và chuẩn hóa Z-score.
> * **Candidate Filtering:** Kiểm tra ngưỡng $\bar{D}(i) > \mu_{\bar{D}} + \alpha \sigma_{\bar{D}}$ và gộp đoạn ngắn $m_{\min}$.
> * **Commitment Phase:** Chốt ranh giới ứng viên thỏa mãn $g \le s_t + W - L$.
> * **Flush Phase:** Chốt đoạn cuối cùng khi gặp sự kiện kết thúc luồng.

---

### Slide B4 — Metric Definitions

#### Content on Slide

> **Định nghĩa chi tiết các chỉ số:**
>
> * **$P_k$:** Tỷ lệ xác suất 2 câu cách nhau $k$ câu bị phân loại sai ranh giới (Càng nhỏ càng tốt).
> * **$WindowDiff (WD)$:** Cải tiến của $P_k$, đếm sự chênh lệch số lượng ranh giới trong cửa sổ $k$.
> * **$Macro-F_1$:** Trung bình cộng $F_1$ của nhãn ranh giới (boundary) và nhãn không phải ranh giới (non-boundary). *(Lưu ý: Không phải điểm $F_1$ riêng của lớp ranh giới)*.
> * **$ROUGE-Max$:** Điểm ROUGE lớn nhất khi so sánh kết quả sinh với danh sách nhiều tiêu đề mẫu chuẩn.

---

### Slide B5 — Training Configurations

#### Content on Slide

> **Chi tiết thông số huấn luyện:**
>
> **ViT5 Chunk Summarization:**
>
> * Learning rate: $3 \times 10^{-4}$ | Effective Batch size: 32 | Max Epochs: 10
> * Best Epoch: **Epoch 6** | Input max length: 512 | Output max length: 128
>
> **BARTpho Topic Titling:**
>
> * Learning rate: $3 \times 10^{-5}$ | Effective Batch size: 64 | Max Epochs: 20
> * Best Epoch: **Epoch 5** | Input max length: 1,024 | Output max length: 200

---

### Slide B6 — Training Curves & Overfitting Analysis

#### Content on Slide

> **Phân tích đường cong huấn luyện (Training & Validation Loss):**
>
> * **ViT5:** Loss giảm ổn định, điểm ROUGE trên tập validation đạt đỉnh tại Epoch 6 trước khi có dấu hiệu đi ngang.
> * **BARTpho:** Validation loss giảm đều và đạt tối ưu tại Epoch 5.
> * Kết luận: Lựa chọn Checkpoint dựa trên Validation Loss và ROUGE giúp tránh hiện tượng Overfitting.

---

### Slide B7 — Streaming Events & Output JSON Schema

#### Content on Slide

> **Danh sách 5 sự kiện dạng dòng (Streaming Events):**
>
> * `utterance-accepted`: Nhận lượt lời mới từ ASR.
> * `segment-closed`: Chốt ranh giới chủ đề mới.
> * `chunk-closed`: Chốt khối 8 câu thoại.
> * `title-emitted`: Phát tiêu đề chủ đề vừa tạo.
> * `meeting-completed`: Hoàn tất và đóng phiên họp.
>
> **Định dạng Output JSON:**
> `{ meeting_id, topic_id, title, summaries: [{ chunk_id, text, speakers, timestamps }] }`

---

### Slide B8 — Speech Front-End Status

#### Content on Slide

> **Kiến trúc tiền xử lý âm thanh (Speech Front-End Design):**
>
> * **Silero VAD:** Phát hiện khoảng lặng và lọc đoạn không chứa tiếng nói.
> * **Zipformer ASR:** Chuyển đổi âm thanh thành văn bản dạng dòng với độ trễ thấp.
> * **WeSpeaker:** Trích xuất đặc trưng giọng nói phục vụ phân định người nói (Diarization).
> * **Sherpa-onnx:** Môi trường thực thi mô hình tối ưu trên CPU/GPU cục bộ.
>
> *(Trạng thái: ASR đã có đánh giá WER; phân định người nói đã tích hợp trong kiến trúc nhưng chưa có đánh giá DER/JER).*

---

## IV. QUY TẮC NGUYÊN TẮC THIẾT KẾ VÀ TRÌNH BÀY

1. **Tuyệt đối không dùng Icon/Emoji:** Tất cả các slide và tài liệu thiết kế không sử dụng bất kỳ biểu tượng icon hoặc emoji nào. Dùng chữ viết, khối định dạng, màu sắc và ký hiệu toán học tiêu chuẩn.
2. **Thanh phân đoạn đồng bộ:** Tất cả các slide đều chứa thanh phân đoạn nhỏ ở góc trên để Hội đồng biết rõ slide thuộc phần nào trong 5 phần chính.
3. **Một thông điệp chính cho mỗi slide:** Mỗi slide chỉ truyền tải 1 kết luận quan trọng nhất, hiển thị nổi bật ở phần tiêu đề hoặc khối kết luận.
4. **Giới hạn số lượng bullet:** Không quá 5 dòng chữ chính trên mỗi slide; ưu tiên trình bày dạng khung, thẻ, bảng hoặc sơ đồ.
5. **Độ tương phản và kích thước chữ:** Chữ tiêu đề tối thiểu 28pt, chữ nội dung 18-20pt, số liệu thống kê phóng lớn 36-48pt.
6. **Màu sắc thiết kế:** Dùng màu tối (Slate / Charcoal) làm nền, màu Vàng Neon / Amber làm màu nhấn chính, màu Xám cho các thông tin phụ/phạm vi.
