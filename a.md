---
TỔNG HỢP 10 ĐÓNG GÓP CẢI THIỆN HỆ THỐNG MEETING RECAP

1. Acoustic-Semantic Error Correction (ASEC) - Hiệu chỉnh lỗi dựa trên âm vị và ngữ nghĩa

- Vấn đề: Transcript từ ASR (Speech-to-Text) thường sai các từ hiếm hoặc từ chuyên môn (ví dụ: "ice cream" thay vì "I scream"), làm sai lệch tóm tắt.
- Giải pháp: Sử dụng mô hình Phoneme-Informed Generative Error Correction. Trước khi tóm tắt, hệ thống sẽ ánh xạ chuỗi văn bản sang chuỗi âm vị (phonemes). Khi gặp từ có độ tin cậy thấp từ ASR, mô hình sẽ tìm kiếm các từ đồng âm (homophones) hoặc từ có âm vị tương đương trong không gian ngữ nghĩa (semantic space) để hiệu chỉnh.
- Công thức: $W^* = \arg\max_{W} P(W|Audio, Phoneme, LLM_Prior)$.
- Đóng góp: Tăng tính bền vững của tóm tắt đối với nhiễu ASR (ASR-noise tolerance).

2. Spectral Dialogue Segmentation (SDS) - Phân đoạn hội thoại dựa trên phổ đồ thị

- Vấn đề: TextTiling hiện tại dùng Cosine Similarity dựa trên từ vựng (lexiĩa (semantic blindness).
TỔNG HỢP 10 ĐÓNG GÓP CẢI THIỆN HỆ THỐNG MEETING RECAP

1. Acoustic-Semantic Error Correction (ASEC) - Hiệu chỉnh lỗi dựa trên âm v

- Vấn đề: Transcript từ ASR (Speech-to-Text) thường sai các từ hiếm hoặc từ chuyên môn (ví dụ: "ice cream" thay vì "I scream"), làm sai lệch tóm tắt.
- Giải pháp: Sử dụng mô hình Phoneme-Informed Generative Error Correction. Trước khi tóm tắt, hệ thống sẽ ánh xạ chuỗi văn bản sang chuỗi âm vị (phonemes). Khi gặp từ có độ tin cậy
thấp từ ASR, mô hình sẽ tìm kiếm các từ đồng âm (homophones) hoặc từ có âm an ngữ nghĩa (semantic space) để hiệu chỉnh.
- Công thức: $W^* = \arg\max_{W} P(W|Audio, Phoneme, LLM_Prior)$.
- Đóng góp: Tăng tính bền vững của tóm tắt đối với nhiễu ASR (ASR-noise tol

2. Spectral Dialogue Segmentation (SDS) - Phân đoạn hội thoại dựa trên phổ

- Vấn đề: TextTiling hiện tại dùng Cosine Similarity dựa trên từ vựng (lexiĩa (semantic blindness).
- Giải pháp: Thay thế TextTiling bằng Spectral Clustering trên đồ thị ngữ nghĩa. Mỗi utterance là một node, trọng số cạnh là độ tương đồng embedding từ Transformer. Sử dụng thuật toán Community Detection (như Louvain) để tìm các cụm chủ đề tự nhiên thay vì cố định cửa sổ 30 utterances.
- Cơ sở: Áp dụng Lý thuyết đồ thị (Graph Theory) để phát hiện cấu trúc phân
- Đóng góp: Phân đoạn chương (chapters) chính xác và linh hoạt hơn theo dòng chảy thực tế của cuộc họp.

3. Key-Utterance Extraction via Video Keyframe Analogy (KUE)

- Vấn đề: Phương thức highlights hiện tại classified từng utterance (O(N)), gây lãng phí tài nguyên cực lớn.
- Giải pháp: Áp dụng kỹ thuật Keyframe Extraction từ Computer Vision. Coi cliên tục. Sử dụng Visual-Temporal Attention để chỉ chọn ra các "KeyUtterances" (những câu mang thông tin đột biến về nội dung - high informational entropy) làm ứng viên cho Highlights, thay vì quét toàn bộ.
- Đánh giá: Giảm số lượng LLM calls từ $N$ xuống còn $K$ ($K \ll N$), tăng

4. Entropy-Based Adaptive Chunking - Chia nhỏ dữ liệu dựa trên lượng tin

- Vấn đề: Chia cố định 8 utterances/chunk gây đứt đoạn ngữ nghĩa (context fragmentation).
- Giải pháp: Sử dụng Information Entropy (Lượng tin). Nếu một đoạn hội thoạ thấp, nghĩa là chủ đề đang thống nhất, có thể gộp chunk lớn. Nếu entropycao, hệ thống sẽ tự động thu nhỏ chunk để bắt kịp các thay đổi nhanh.
- Công thức: Tính $H(X) = -\sum P(x) \log P(x)$ trên cửa sổ trượt để quyết định điểm cắt chunk.
- Đóng góp: Tối ưu hóa ngữ nghĩa cho từng bước tóm tắt nhỏ, tránh mất ý (no-omission).

5. State-Space Dialogue State Tracking (SS-DST)

- Vấn đề: Các chunk được tóm tắt độc lập, dẫn đến mất khả năng giải quyết đại từ (coreference resolution) như "nó", "anh ấy", "vấn đề đó".
- Giải pháp: Áp dụng cấu trúc State Space Models (SSM) tương tự như kiến tr Duy trì một "Vector Trạng thái" (State Vector) đại diện cho ngữ cảnh đã qua và cập nhật nó sau mỗi lần tóm tắt chunk. Vector này được feed vào prompt của chunk tiếp theo.
- Đóng góp: Tạo ra sự liền mạch (coherence) giữa các phần tóm tắt, giúp LLMc đưa ra xuyên suốt nhiều lượt hội thoại.

6. Speculative Hierarchical Summarization - Tóm tắt phân cấp dự đoán

- Vấn đề: Tóm tắt phân cấp (Hierarchical) mất nhiều thời gian do phải chờ kết quả từ các lớp dưới.
- Giải pháp: Sử dụng Speculative Decoding cho việc tóm tắt. Một model nhỏ (ví dụ: Haiku hoặc Llama-8B) tạo ra bản nháp tóm tắt nhanh cho các chunks, model lớn (Sonnet/Opus) chỉ thực hiện việc kiểm chứng và tổng hợp lại ở lớp chương (chapter level).
- Đóng góp: Tối ưu hóa latency (độ trễ) trong khi vẫn giữ được chất lượng cao của model lớn.

7. Centrality-Weighted Highlights (CWH)

- Vấn đề: Highlights hiện tại là một danh sách phẳng (flat list), không có sự ưu tiên.
- Giải pháp: Xây dựng đồ thị liên kết giữa các ý chính. Sử dụng thuật toán  trọng (centrality) của mỗi Highlight. Ý kiến nào được nhắc lại hoặc đượcnhiều người đồng thuận sẽ có rank cao hơn.
- Đóng góp: Tự động sắp xếp mức độ quan trọng của các ghi chú và tác vụ (action items).

8. Acoustic-Prosodic Weighted Attention

- Vấn đề: Chữ viết không thể hiện được cảm xúc hay sự nhấn mạnh của người nói.
- Giải pháp: Trích xuất các tính năng âm học (pitch, energy, duration) từ fhts) cho các utterances. Những câu có cao độ biến thiên mạnh hoặc năng lượng cao (thể hiện sự nhấn mạnh hoặc ra quyết định) sẽ được ưu tiên đưa vào tóm tắt.
- Đóng góp: Tóm tắt "đúng trọng tâm" dựa trên cả tín hiệu phi ngôn ngữ (non

9. Multi-Lens Contrastive Recapping

- Vấn đề: Tóm tắt chung chung thường thiếu các chi tiết cụ thể cho từng bộ
- Giải pháp: Chạy tóm tắt song song qua 3 "ống kính" (Lenses): Logic Lens (tìm quyết định), Task Lens (tìm hành động), và Context Lens (tìm nguyên nhân). Sử dụng kỹ thuật Contrastive Prompting để đảm bảo không có sự chồng lấn và thiếu sót giữa các lens.
- Đóng góp: Đảm bảo độ bao phủ thông tin tối đa (high recall).

10. Error-Tolerant Semantic Reconstruction (ETSR)

- Vấn đề: Khi ASR sai quá nặng, LLM thường bị "hallucinate" (ảo tưởng) ra n
- Giải pháp: Thay vì summary trực tiếp từ text, hệ thống sẽ chuyển transcript sang không gian vector tiềm ẩn (latent space), sau đó sử dụng một model Denoising Autoencoder để khôi
phục lại cấu trúc ngữ nghĩa "sạch" trước khi đưa vào LLM tóm tắt.
- Đóng góp: Tóm tắt đúng ngay cả khi transcript sai nhiều (robustness).
---
ĐỀ CƯƠNG PAPER (RESEARCH PAPER STRUCTURE)

Nếu bạn viết paper, bạn có thể cấu trúc như sau:

1. Abstract: Giới thiệu về thách thức của tóm tắt cuộc họp (nhiễu ASR, độ dài, tính phi tuyến tính) và đề xuất hệ thống cải tiến dựa trên liên ngành.
2. Introduction: Phân tích hạn chế của các phương pháp Hierarchical và Highlights truyền thống (như trong codebase hiện tại).
3. Related Work: Tổng quan về SOTA NLP, Speech Processing và ứng dụng CV tr
4. Methodology:
     - 4.1. Graph-based Semantic Segmentation (thay thế TextTiling).
     - 4.2. Acoustic-Aware Error Correction.
     - 4.3. Information-Theoretic Adaptive Chunking.
5. Experiments:
     - Sử dụng dataset chuẩn (AMI, ICSI, hoặc QMSum).
     - So sánh với Baseline (hệ thống hiện tại).
6. Results & Discussion: Đánh giá qua các chỉ số ROUGE-L, BERTScore, và quan trọng nhất là Human Evaluation về tính hữu dụng của Action Items.
7. Conclusion: Khẳng định đóng góp của các phương pháp liên ngành vào việc cải thiện chất lượng tóm tắt.

Sources & References gợi ý:

- Li et al. (2020) về Hierarchical Transformers.
- Zhang et al. (2023) về LLM-based Dialogue Segmentation.
- Hsu et al. (2021) về HuBERT (Acoustic representations).
- Arxiv Search: "Robust Dialogue Summarization under ASR noise".

giải thích rõ hơn
