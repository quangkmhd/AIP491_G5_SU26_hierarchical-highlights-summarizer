# Thiết kế cải thiện Mục 3.5, 3.6 và Chương 5

## Phạm vi

Chỉnh sửa chỉ giới hạn ở Mục 3.5 về Multi-Scale Sliding TextTiling, Mục 3.6 về tóm tắt phân cấp và các nội dung thực nghiệm tương ứng trong Chương 5. Các Mục 3.2, 3.3 và 3.4 được giữ nguyên. Báo cáo tiếp tục tuân theo cấu trúc, cách đặt thuật ngữ Anh–Việt và văn phong của tài liệu mẫu `report_compilation/templates/extracted_paper/extracted_paper.md`.

## Mạch lập luận

Mỗi phương pháp được trình bày theo cùng một mạch: lý do lựa chọn, hạn chế của phương pháp hoặc mô hình nền, nội dung được cải tiến hoặc tùy biến, cấu hình triển khai và bằng chứng thực nghiệm. Phần phương pháp chỉ giải thích thiết kế; số liệu đánh giá và diễn giải kết quả được đặt trong Chương 5 để tránh lặp nội dung.

Mục 3.5 sẽ làm rõ TextTiling được chọn vì không cần dữ liệu gán nhãn, có chi phí suy luận thấp và dễ giải thích, phù hợp với xử lý cục bộ. Hạn chế của TextTiling trên hội thoại ngắn và dữ liệu ngoại tuyến được nối trực tiếp với năm thay đổi của Multi-Scale Sliding TextTiling: tính liên kết theo nhóm lượt lời, điểm sâu đa phạm vi, ngưỡng thích ứng cục bộ, gộp phân đoạn ngắn và xác nhận trễ trong cửa sổ trượt.

Mục 3.6 sẽ giải thích kiến trúc phân cấp được chọn để xử lý giới hạn ngữ cảnh và duy trì thứ tự nội dung. ViT5 được dùng cho tóm tắt khối vì có kiến trúc text-to-text và được tiền huấn luyện cho tiếng Việt; BARTpho được dùng cho tiêu đề vì kiến trúc sinh chuỗi phù hợp với đầu ra ngắn. Các tùy biến cần được nêu rõ gồm chia khối tám lượt lời, giữ nhãn người nói, thêm tiền tố tác vụ, tinh chỉnh trên dữ liệu cuộc họp, giới hạn đầu vào và cấu hình giải mã xác định.

## Bằng chứng thực nghiệm

Chương 5 sẽ liên kết Bảng 9 với so sánh phương pháp phân đoạn, Bảng 11 với đóng góp của từng cải tiến và Bảng 12–14 với quá trình huấn luyện, lựa chọn checkpoint và đánh giá độc lập của ViT5 và BARTpho. Phần thực nghiệm cần mô tả rõ thứ tự chuẩn bị dữ liệu, huấn luyện, theo dõi validation, chọn checkpoint, cố định cấu hình và đánh giá trên 65 cuộc họp giữ lại.

Không bổ sung kết quả giả định. Do chưa có phép chạy đối chứng cho ViT5 và BARTpho trên cùng tập đánh giá, báo cáo chỉ trình bày kết quả tuyệt đối và nêu rõ giới hạn này. Đánh giá streaming cũng không được mở rộng thành tuyên bố về thời gian thực khi chưa có số liệu độ trễ, thông lượng và bộ nhớ.

## Tiêu chí hoàn thành

Nội dung mới phải ngắn gọn, viết thành đoạn văn có câu chuyển tiếp và không lặp lại công thức hoặc cấu hình đã trình bày. Mọi nhận định về hiệu quả cải tiến phải đối chiếu được với bảng kết quả hiện có. Cú pháp Markdown phải hợp lệ và số thứ tự bảng, hình, mục không bị thay đổi ngoài phạm vi cần thiết.
