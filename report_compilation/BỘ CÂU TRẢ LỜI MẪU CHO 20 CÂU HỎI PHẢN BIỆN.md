**Câu 1: Tại sao chọn Bag-of-Words (BoW) thay vì Dense Sentence Embeddings (Sentence-BERT)?**
- thời gian thực + tối ưu tài nguyên: 
- thuật toán đang chạy với của sổ là 40, bước là 5 => cần nhiều gpu để chạy, thời gian chậm, khó streaming, chi phí cao
- Bow có chi phí tính toán thấp trên cpu . 
- Nhóm đã kết hợp cơ chế z-core cục bộ và quét đa phạm vi để tăng độ chính sác.
Câu 2: ở thuật toán 1 tại sao lại chọn tham số **(α=1.2,γ=0.20)**
- Là tham số cố định để đánh giá khả năng tổng quát
- tham số đã được qua thử nhiệm nhiều lần theo vòng lặp để tìm được tham số hiện tại phù hợp và bao quát với 6 bộ data đánh giá
- nếu mà cuộc họp rất ngắn và chuyển chủ đề rất nhanh thì có thể sảy ra mất ranh giới chủ đề.
**Câu 3: Nguyên nhân kết quả kém trên bộ dữ liệu AMI và ICSI?**
- AMI: là họp thiết kế sản phầm là cuộc họp tự nhiên kéo dài, **ICSI** là họp học thuật
- Mật độ dùng trung các từ chuyên ngành rất cao vì vậy nó gặp khó khăn khi độ suy giảm từ vứng giữa 2 ranh giới không đủ sâu
- 