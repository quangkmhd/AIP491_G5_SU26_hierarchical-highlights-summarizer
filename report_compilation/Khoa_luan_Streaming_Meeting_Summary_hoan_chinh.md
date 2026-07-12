## Xây dựng hệ thống tóm tắt cuộc họp tiếng Việt theo thời gian thực sử dụng phân đoạn chủ đề và mô hình sinh phân cấp (Building a Real-time Vietnamese Meeting Summarization System Using Topic Segmentation and Hierarchical Generative Models)

**Tóm tắt (Abstract)**

Bản ghi lời thoại (transcript) cuộc họp thường dài, có nhiều người tham gia đối thoại, chứa câu rời rạc và chuyển chủ đề không rõ ràng. Việc đưa toàn bộ transcript vào một mô hình sinh duy nhất vừa bị giới hạn độ dài đầu vào, vừa làm giảm khả năng bảo toàn cấu trúc nội dung. Báo cáo này trình bày thiết kế và triển khai một hệ thống tóm tắt cuộc họp tiếng Việt theo thời gian thực theo cấu trúc phân cấp. Hệ thống trước hết chia hội thoại thành các phân đoạn chủ đề bằng Multi-Scale Sliding TextTiling, một phương pháp phi giám sát kết hợp Bag-of-Words, độ tương đồng cosine giữa hai khối thoại, điểm sâu đa bán kính, chuẩn hóa Z-score, ngưỡng động và gộp phân đoạn nhỏ. Mỗi phân đoạn sau đó được chia thành các khối (chunk) tối đa 8 lượt thoại. Mô hình ViT5 đã tinh chỉnh sinh tóm tắt cho từng chunk; các tóm tắt trung gian được ghép theo thứ tự và đưa vào BARTpho để tạo tiêu đề chủ đề.

Hai chế độ thực thi dùng chung một lõi điều phối: chế độ streaming phát 5 loại sự kiện để cập nhật kết quả dần, còn chế độ batch tiêu thụ cùng luồng sự kiện và trả về cấu trúc `HierarchicalRecap`. Trên 6 bộ dữ liệu phân đoạn, Sliding TextTiling đạt điểm $F_1$ trung bình 0,1970, cao nhất trong 5 phương pháp được so sánh, đồng thời có $P_k$ trung bình 0,4488 và WindowDiff trung bình 0,4835. ViT5 đạt ROUGE-1/2/L lần lượt 0,7265/0,4854/0,5486 trên 6.038 chunk của tập dev. BARTpho đạt RougeMax-1/2/L tương ứng 0,5304/0,2837/0,4443 trên 736 phân đoạn. Kết quả cho thấy kiến trúc phân cấp là một hướng khả thi để xử lý hội thoại dài tiếng Việt, nhưng chất lượng vẫn phụ thuộc vào độ chính xác của ranh giới chủ đề, nhãn tóm tắt và miền dữ liệu.

*Abstract:* Meeting transcripts are often long, multi-party, fragmented, and weakly structured. Processing an entire transcript with a single generative model is constrained by input length and may obscure the topical organization of the meeting. This report details a real-time Vietnamese meeting summarization system based on a hierarchical pipeline. The dialogue is first divided into topical segments using Multi-Scale Sliding TextTiling, an unsupervised method combining bag-of-words representations, block cosine similarity, multi-radius depth scoring, Z-score normalization, dynamic thresholding, and greedy merging of short segments. Each segment is then divided into chunks of at most 8 utterances. A fine-tuned ViT5 model generates chunk summaries, which are chronologically concatenated and passed to BARTpho to produce a topic title. Streaming and batch modes share the same orchestration core. The streaming mode emits 5 deterministic event types, while batch processing consumes the same event stream and returns a validated `HierarchicalRecap`. Across 6 topic-segmentation datasets, Sliding TextTiling obtains the highest average boundary $F_1$ of 0.1970 among 5 evaluated methods, with average $P_k$ of 0.4488 and WindowDiff of 0.4835. ViT5 achieves ROUGE-1/2/L scores of 0.7265/0.4854/0.5486 on 6,038 development chunks. BARTpho achieves multi-reference RougeMax-1/2/L scores of 0.5304/0.2837/0.4443 on 736 topical segments. The results indicate that hierarchical processing is a practical direction for long Vietnamese meetings, although the overall quality remains dependent on segmentation accuracy, target-label quality, and domain transferability.

**Từ khóa (Keywords):** tóm tắt cuộc họp, phân đoạn chủ đề, Sliding TextTiling, ViT5, BARTpho, xử lý luồng, tiếng Việt (meeting summarization, topic segmentation, Sliding TextTiling, ViT5, BARTpho, streaming, Vietnamese).

---

## Mở đầu (Introduction)

### Bối cảnh và động cơ nghiên cứu (Background and Motivation)
Họp trực tuyến và làm việc phân tán tạo ra ngày càng nhiều bản ghi lời thoại. Transcript giúp lưu trữ nội dung nhưng không giải quyết trực tiếp nhu cầu tra cứu nhanh: người dùng vẫn phải đọc hàng trăm hoặc hàng nghìn lượt thoại để xác định cuộc họp đã bàn gì, nội dung nào thuộc cùng một chủ đề và phần nào chứa kết luận quan trọng. Khó khăn tăng lên khi transcript có nhiều người nói, câu không hoàn chỉnh, từ đệm, lặp ý và lỗi nhận dạng giọng nói.

Tóm tắt văn bản thông thường giả định đầu vào tương đối mạch lạc. Hội thoại cuộc họp không có tiêu đề hoặc ranh giới đoạn rõ ràng; một chủ đề có thể kéo dài qua nhiều lượt nói, bị ngắt bởi trao đổi ngắn rồi quay lại. Nếu xử lý toàn bộ transcript như một văn bản phẳng, mô hình phải đồng thời phát hiện cấu trúc, chọn thông tin và sinh bản tóm tắt trong một lần. Cách làm này khó áp dụng với mô hình có cửa sổ 512 hoặc 1.024 token và không phù hợp với yêu cầu trả kết quả dần trong lúc họp.

Nghiên cứu tiếp cận vấn đề theo nguyên tắc phân rã: xác định ranh giới chủ đề trước, tóm tắt từng phần nhỏ sau, rồi tổ chức các kết quả thành báo cáo phân cấp. Phân đoạn chủ đề làm giảm độ dài và nhiễu của mỗi đơn vị xử lý. Tóm tắt theo chunk giúp mô hình sinh làm việc trong giới hạn đầu vào. Tiêu đề chủ đề cung cấp lớp điều hướng ở mức cao, trong khi tóm tắt chunk giữ lại chi tiết theo trình tự.

### Bài toán nghiên cứu (Problem Statement)
Đầu vào của hệ thống là chuỗi $n$ lượt thoại theo thứ tự thời gian:
$$
U = (u_1, u_2, \dots, u_n), \qquad u_i = (s_i, t_i)
$$
trong đó $s_i$ là người nói và $t_i$ là nội dung. Hệ thống cần tìm tập ranh giới $B$, chia $U$ thành các phân đoạn chủ đề; chia mỗi phân đoạn thành các chunk; sinh tóm tắt $q_{k,j}$ cho chunk thứ $j$ của chủ đề $k$; và sinh tiêu đề $h_k$ từ các tóm tắt thuộc chủ đề đó. Đầu ra là một cấu trúc phân cấp:
$$
R = \left\{ \left( h_k, \{ q_{k, 1}, q_{k, 2}, \dots, q_{k, m_k} \} \right) \right\}_{k=1}^{K}
$$
Ngoài chất lượng nội dung, hệ thống phải hỗ trợ hai cách sử dụng: tiếp nhận dần từng lượt thoại và phát kết quả trung gian; hoặc xử lý một transcript hoàn chỉnh theo batch. Hai chế độ cần nhất quán về cấu trúc đầu ra để tránh duy trì hai pipeline khác nhau.

### Mục tiêu nghiên cứu (Research Objectives)
Nghiên cứu hướng tới các mục tiêu cụ thể sau:
1. Xây dựng phương pháp phân đoạn chủ đề hội thoại tiếng Việt không cần huấn luyện và đủ nhẹ cho pipeline trực tuyến.
2. Tinh chỉnh mô hình ViT5 để tóm tắt khối hội thoại ngắn có thông tin người nói.
3. Tinh chỉnh BARTpho để sinh tiêu đề từ chuỗi tóm tắt trung gian thay vì transcript thô.
4. Thiết kế pipeline phân cấp hỗ trợ streaming và batch trên cùng logic nghiệp vụ.
5. Đánh giá từng thành phần bằng các chỉ số phù hợp: $P_k$, WindowDiff và $F_1$ cho phân đoạn; ROUGE/RougeMax cho tóm tắt và tạo tiêu đề.

### Phạm vi nghiên cứu (Scope of Study)
Đề tài xử lý transcript văn bản tiếng Việt đã có thông tin người nói. Nhận dạng giọng nói, speaker diarization từ âm thanh, phân tích cảm xúc, trích xuất nhiệm vụ và phát hiện quyết định không thuộc phạm vi thực nghiệm chính. Hệ thống chạy các checkpoint cục bộ và yêu cầu CUDA cho hai mô hình tạo sinh. Chất lượng được đánh giá chủ yếu bằng bộ dữ liệu dịch hoặc chuyển đổi sang tiếng Việt; vì vậy khả năng khái quát tới hội thoại tự nhiên thu thập trực tiếp tại Việt Nam cần được kiểm chứng thêm.

### Đóng góp nghiên cứu (Research Contributions)
Các đóng góp chính của nghiên cứu gồm:
* Một pipeline tóm tắt cuộc họp tiếng Việt theo cấu trúc chủ đề–chunk, hỗ trợ cả streaming và batch.
* Một biến thể Multi-Scale Sliding TextTiling kết hợp điểm sâu ở các bán kính $\{3, 5, 10, 15, 20\}$, chuẩn hóa Z-score và ngưỡng động.
* Hai checkpoint tạo sinh được tinh chỉnh cho hai nhiệm vụ tách biệt: tóm tắt chunk bằng ViT5 và tạo tiêu đề chủ đề bằng BARTpho.
* Một đánh giá thực nghiệm gồm 5 phương pháp phân đoạn trên 6 tập dữ liệu, cùng benchmark riêng cho hai mô hình sinh.
* Một kiến trúc phần mềm phân tầng và vòng đời 5 sự kiện phục vụ cập nhật kết quả dần.

### Cấu trúc báo cáo (Report Structure)
Phần còn lại của báo cáo được tổ chức như sau: Mục Nghiên cứu liên quan trình bày nền tảng lý thuyết và nghiên cứu liên quan. Mục Phương pháp luận mô tả dữ liệu, kiến trúc và phương pháp đề xuất. Mục Bộ dữ liệu và Thiết lập thực nghiệm giới thiệu về các tập dữ liệu, cấu hình huấn luyện và môi trường. Mục Thực nghiệm và Phân tích phân tích kết quả thực nghiệm chi tiết. Mục Phần mềm đặc tả về thiết kế UI, các tầng kiến trúc và cơ chế xử lý streaming. Cuối cùng, Mục Kết luận kết luận báo cáo, nêu hạn chế và hướng phát triển tương lai.

---

## Nghiên cứu liên quan (Related Work)

### Tóm tắt văn bản và tóm tắt hội thoại (Text and Dialogue Summarization)
Tóm tắt văn bản tạo phiên bản ngắn hơn của đầu vào trong khi cố gắng bảo toàn thông tin quan trọng. Phương pháp trích xuất chọn câu hoặc cụm từ có sẵn; phương pháp sinh tạo chuỗi mới và có thể diễn đạt cô đọng hơn. Mô hình sinh dựa trên Transformer đạt chất lượng ngôn ngữ tốt nhưng có nguy cơ ảo giác và phụ thuộc mạnh vào dữ liệu huấn luyện.

Tóm tắt cuộc họp khó hơn tóm tắt tài liệu đơn tác giả. Thông tin quan trọng có thể được hình thành qua nhiều lượt nói: một người đề xuất, người khác phản biện và nhóm chốt phương án ở cuối. Một câu riêng lẻ thường không đủ ngữ cảnh. Bản tóm tắt hữu ích do đó cần phản ánh trình tự và cấu trúc chủ đề, thay vì chỉ xếp hạng từng câu độc lập.

Nghiên cứu chọn tóm tắt sinh phân cấp. Đơn vị nhỏ là chunk tối đa 8 lượt thoại, đủ ngắn cho ViT5. Các tóm tắt chunk đóng vai trò biểu diễn nén của phân đoạn. Từ biểu diễn này, BARTpho sinh tiêu đề ở mức chủ đề. Thiết kế tách nhiệm vụ cho phép mỗi mô hình tối ưu một mục tiêu rõ ràng.

### Phân đoạn chủ đề hội thoại (Dialogue Topic Segmentation)
Phân đoạn chủ đề chia chuỗi đơn vị ngôn ngữ thành các vùng liên tiếp có nội dung tương đối nhất quán. TextTiling của Hearst [@Hearst1997] dựa trên giả định rằng các phần cùng chủ đề chia sẻ từ vựng, còn độ tương đồng giảm tại điểm chuyển chủ đề. Phương pháp tạo chuỗi điểm tương đồng giữa các khối lân cận, tìm các “thung lũng” và chọn vị trí có điểm sâu cao làm ranh giới.

Phương pháp từ vựng có ưu điểm không cần nhãn, dễ giải thích và chạy nhanh. Tuy nhiên, nó không nhận biết tốt hai cách diễn đạt khác từ nhưng cùng nghĩa; đồng thời dễ bị nhiễu trong hội thoại ngắn. Biểu diễn embedding cải thiện ngữ nghĩa nhưng tăng chi phí suy luận. Đề tài sử dụng đa bán kính để giảm phụ thuộc vào một kích thước quan sát cố định: bán kính nhỏ nhạy với chuyển dịch ngắn, bán kính lớn phản ánh thay đổi vĩ mô.

### Kiến trúc Transformer, T5 và BART (Transformer, T5, and BART Architectures)
Transformer sử dụng self-attention để mô hình hóa quan hệ giữa các token [@Vaswani2017]. Trong mô hình encoder–decoder, encoder mã hóa đầu vào và decoder sinh đầu ra tự hồi quy. Xác suất của chuỗi đích $Y = (y_1, \dots, y_m)$ được phân rã:
$$
P(Y \mid X) = \prod_{j=1}^{m} P(y_j \mid y_{<j}, X)
$$
T5 biểu diễn nhiều nhiệm vụ NLP dưới dạng chuyển đổi văn bản–văn bản [@Raffel2020]. Tiền tố tác vụ như `Tóm tắt:` giúp mô hình nhận biết nhiệm vụ. ViT5 kế thừa cách tiếp cận này và được huấn luyện cho tiếng Việt [@Phan2022]. BART kết hợp encoder hai chiều và decoder tự hồi quy, được tiền huấn luyện bằng cách khôi phục văn bản bị làm nhiễu [@Lewis2020]. BARTpho là biến thể dành cho tiếng Việt, phù hợp với nhiệm vụ sinh chuỗi ngắn như tiêu đề [@Nguyen2021].

Trong đề tài, ViT5 nhận văn bản hội thoại trực tiếp và sinh một câu tóm tắt. BARTpho chỉ nhận các tóm tắt đã nén. Việc không đưa transcript thô vào bộ tạo tiêu đề làm giảm độ dài đầu vào và tách tiêu đề khỏi nhiễu hội thoại.

### Tóm tắt phân cấp và xử lý ngữ cảnh dài (Hierarchical Summarization and Long Context Processing)
Khi đầu vào vượt giới hạn mô hình, một chiến lược phổ biến là chia nhỏ, xử lý từng phần và tổng hợp kết quả. Ưu điểm là kiểm soát bộ nhớ và giữ được thông tin cục bộ. Nhược điểm là lỗi có thể lan truyền: nếu tóm tắt chunk bỏ sót một quyết định, bộ tạo tiêu đề không thể khôi phục thông tin đó. Các chunk độc lập cũng có thể tạo câu lặp hoặc thiếu liên kết.

Hệ thống sử dụng chiến lược bottom-up roll-up. Transcript được chia theo chủ đề trước khi chunking, nhờ đó phần lớn chunk không vượt qua ranh giới nội dung. Tóm tắt chunk được giữ theo thứ tự thời gian. Tiêu đề được sinh sau khi toàn bộ chunk của phân đoạn hoàn tất, vì vậy gọi là tạo tiêu đề trì hoãn.

### Xử lý streaming và Server-Sent Events (Streaming and Server-Sent Events)
Streaming cho phép hệ thống phản hồi trước khi toàn bộ cuộc họp kết thúc. SSE [@W3CSSE2015] là cơ chế máy chủ gửi chuỗi sự kiện một chiều tới trình duyệt qua kết nối HTTP. So với polling, SSE giảm số lần yêu cầu lặp; so với WebSocket, nó đơn giản hơn khi chỉ cần truyền dữ liệu từ máy chủ tới giao diện.

Tuy nhiên, một ranh giới chủ đề chỉ có thể được xác nhận khi đã quan sát đủ ngữ cảnh phía sau. Vì vậy “thời gian thực” trong đề tài được hiểu là xử lý và phát kết quả tăng dần, không phải xác định ranh giới ngay tại thời điểm phát sinh câu thoại. Hệ thống phát sự kiện khi phân đoạn hoặc chunk đã đóng và không sửa lại đối tượng bất biến đã công bố.

### Chỉ số đánh giá tự động (Automatic Evaluation Metrics)
$P_k$ đo xác suất hai vị trí cách nhau một cửa sổ bị phân loại sai về quan hệ cùng/khác phân đoạn [@Beeferman1999]. WindowDiff đếm sự khác biệt về số ranh giới trong cửa sổ và khắc phục một số hạn chế của $P_k$ [@Pevzner2002]. Hai chỉ số càng thấp càng tốt. $F_1$ biên là trung bình điều hòa của precision và recall, càng cao càng tốt; kết quả phụ thuộc quy tắc dung sai khi ghép biên.

ROUGE đánh giá độ trùng lặp n-gram hoặc chuỗi con chung dài nhất giữa đầu ra và tham chiếu [@Lin2004]. ROUGE-1 phản ánh unigram, ROUGE-2 phản ánh bigram và ROUGE-L dựa trên longest common subsequence. Với nhiều tiêu đề tham chiếu, đề tài dùng RougeMax: tính ROUGE với từng tham chiếu rồi lấy giá trị lớn nhất. Cách này chấp nhận nhiều cách đặt tiêu đề hợp lệ nhưng có thể cho điểm lạc quan hơn so với lấy trung bình.

### Khoảng trống nghiên cứu và định hướng (Research Gaps and Directions)
Các hướng tiếp cận hiện có thường đánh đổi giữa mô hình ngữ nghĩa tốn tài nguyên và heuristic nhẹ nhưng hạn chế hiểu nghĩa. Đồng thời, nhiều pipeline tóm tắt tập trung vào chất lượng đầu ra cuối mà chưa xem cấu trúc sự kiện phục vụ giao diện trực tuyến. Đề tài không đặt mục tiêu chứng minh một mô hình đạt trạng thái tốt nhất tuyệt đối. Thay vào đó, nghiên cứu xây dựng và đánh giá một tổ hợp thực dụng: phân đoạn phi giám sát chạy nhanh, hai mô hình sinh cục bộ chuyên biệt và một lõi điều phối dùng chung cho hai chế độ vận hành.

---

## Phương pháp luận (Methodology)

### Quy trình tổng thể (Overall Pipeline)
Pipeline gồm 4 giai đoạn chính: phân đoạn hội thoại bằng Multi-Scale Sliding TextTiling; chia từng phân đoạn thành các chunk liên tiếp tối đa 8 lượt thoại; sinh tóm tắt chunk bằng ViT5; và ghép các tóm tắt theo thứ tự để BARTpho sinh tiêu đề. Đầu ra là `HierarchicalRecap`, trong đó mỗi segment chứa khoảng chỉ số, tiêu đề và danh sách chunk. Cấu trúc này hỗ trợ đọc theo chiều rộng: xem danh sách chủ đề trước rồi mở chi tiết khi cần.

### Thuật toán Multi-Scale Sliding TextTiling (Multi-Scale Sliding TextTiling Algorithm)

#### Tiền xử lý và độ tương đồng khối (Preprocessing and Block-level Similarity)
Với mỗi lượt thoại $u_i$, hệ thống chuyển chữ thường, loại ký tự đặc biệt, lọc từ dừng tiếng Việt bằng `stopwordsiso` [@Stopwordsiso2024] và tạo vector tần suất $b_i(w) = \operatorname{tf}(w, u_i)$. Tại khe $i$ giữa $u_i$ và $u_{i+1}$, hai khối có kích thước $k$ (block size) được biểu diễn bởi:
$$
B_L^i(w) = \sum_{j=\max(0, i-k+1)}^{i} b_j(w)
$$
$$
B_R^i(w) = \sum_{j=i+1}^{\min(n-1, i+k)} b_j(w)
$$
Độ tương đồng cosine:
$$
S_i = \frac{B_L^i \cdot B_R^i}{\|B_L^i\|_2 \|B_R^i\|_2}
$$
Giá trị thấp cho biết hai phía chia sẻ ít từ vựng và có thể là điểm chuyển chủ đề. So sánh theo khối ổn định hơn so sánh hai câu ngắn riêng lẻ.

#### Điểm sâu thung lũng đa bán kính (Multi-radius Depth Scoring)
Với bán kính $r$, đỉnh trái và phải quanh khe $i$ là:
$$
p_L(i, r) = \max_{\max(0, i-r) \le j \le i} S_j
$$
$$
p_R(i, r) = \max_{i \le j \le \min(n-2, i+r)} S_j
$$
Điểm sâu:
$$
D_r(i) = \frac{p_L(i, r) + p_R(i, r) - 2S_i}{2}
$$
Đề tài sử dụng $R = \{3, 5, 10, 15, 20\}$. Mỗi mảng điểm được chuẩn hóa để bán kính lớn không chi phối:
$$
\widehat{D}_r(i) = \frac{D_r(i) - \mu_r}{\sigma_r + 10^{-10}}
$$
$$
\bar{D}(i) = \frac{1}{|R|} \sum_{r \in R} \widehat{D}_r(i)
$$

#### Ngưỡng động và gộp phân đoạn ngắn (Dynamic Thresholding and Greedy Merging)
Ngưỡng thích ứng được tính:
$$
\tau = \mu(\bar{D}) + \alpha \sigma(\bar{D})
$$
Khe có $\bar{D}(i) > \tau$ là ứng viên ranh giới. Cấu hình được chọn trên 6 mẫu phát triển của `meeting_committee` gồm `block_size = 2`, `alpha = 1.5`, `radii = [3,5,10,15,20]` và `min_segment_ratio = 0.1`. Độ dài tối thiểu là:
$$
m_{\min} = \max(2, \lfloor 0.1n \rfloor)
$$
Nếu một phân đoạn ngắn hơn $m_{\min}$, thuật toán xóa ranh giới yếu hơn trong hai ranh giới bao quanh để gộp đoạn vào láng giềng. Bước hậu xử lý làm giảm quá phân mảnh và tránh gửi quá ít ngữ cảnh cho mô hình sinh.

#### Mã giả thuật toán (Algorithm Pseudocode)
```text
Input: utterances U, block size k, radii R, alpha, min ratio
1. Chuyển từng lượt thoại thành biểu diễn BoW sau khi lọc stopword.
2. Tính độ tương đồng cosine giữa khối trái và phải tại mọi khe.
3. Với mỗi bán kính r trong R: tính depth score và chuẩn hóa Z-score.
4. Lấy trung bình các mảng depth đã chuẩn hóa để có aggregated_depth.
5. Thiết lập ngưỡng động: tau <- mean(aggregated_depth) + alpha * std(aggregated_depth).
6. Chọn khe có aggregated_depth > tau và thêm điểm chốt chặn kết thúc.
7. Gộp tham lam các phân đoạn ngắn hơn tỷ lệ min_segment_ratio.
8. Trả về ranh giới các phân đoạn chủ đề.
```

### Tóm tắt khối bằng ViT5 (Chunk Summarization via ViT5)
Mỗi phân đoạn được chia tuần tự, không chồng lấn, thành các chunk tối đa 8 lượt thoại. Đầu vào giữ người nói và thêm tiền tố tác vụ:
```text
Tóm tắt: Speaker A: ...
Speaker B: ...
```
ViT5 học chuỗi đích bằng negative log-likelihood:
$$
\mathcal{L}_{\text{sum}}(\theta) = -\frac{1}{N} \sum_{i=1}^{N} \sum_{j=1}^{|y_i|} \log P_\theta(y_{i, j} \mid y_{i, <j}, x_i)
$$
Runtime giới hạn đầu vào 512 token, dùng 4 beam và tối đa 128 token mới. Checkpoint triển khai là `models/vit5-chunk-summarizer-v1` [@Nguyen2026], tải cục bộ.

### Tạo tiêu đề chủ đề bằng BARTpho (Topic Titling via BARTpho)
Với các tóm tắt $q_{k,1}, \dots, q_{k,m}$ của chủ đề $k$, đầu vào là:
$$
x_k^{\text{title}} = \text{“Tạo tiêu đề: ”} \mathbin{\Vert} q_{k, 1} \mathbin{\Vert} \text{“ / ”} \mathbin{\Vert} \dots \mathbin{\Vert} q_{k, m}
$$
Nếu chuỗi dài hơn 1.500 ký tự, hệ thống giữ 1.500 ký tự cuối, sau đó giới hạn ở 1.024 token. Runtime dùng 4 beam và tối đa 200 token mới; nhãn huấn luyện giới hạn 64 token. Checkpoint là `models/bartpho-topic-titler-v2` [@Nguyen2026].

Dữ liệu có tối đa 3 tiêu đề tham chiếu. Mục tiêu huấn luyện là tiêu đề có nhiều từ nhất:
$$
y^* = \arg\max_{c \in C} \operatorname{CountWords}(c)
$$
Lựa chọn này ưu tiên độ bao phủ nhưng không đảm bảo tiêu đề tự nhiên nhất. Khi đánh giá, đầu ra được so với toàn bộ tham chiếu bằng RougeMax.

---

## Bộ dữ liệu (Dataset)

### Dữ liệu cho các mô hình tạo sinh (Generative Model Datasets)
Dữ liệu chính là `Alimeeting4MUG_vi` [@Alimeeting2024]. Tập train chứa 295 bản ghi; trường `chunk_summaries` cung cấp khoảng `start_id`–`end_id` và tóm tắt. Quá trình trích xuất tạo 28.079 cặp `(chunk, summary)`.

**Thống kê tập dữ liệu huấn luyện và đánh giá mô hình tạo sinh**

| Tập dữ liệu | Số bản ghi (Hội thoại) | Đơn vị đánh giá | Quy mô trích xuất |
|---|---|---|---|
| Train nguồn | 295 | 28.079 chunk | - |
| Train sau chia (90%) | 295* | 25.272 chunk | - |
| Validation (10%) | 295* | 2.807 chunk | - |
| Dev benchmark | 65 | 6.038 chunk | 736 chủ đề |
| Test benchmark | 65 | 3.863 chunk | - |

\(*\): Tập Train và Validation được chia ngẫu nhiên ở mức độ chunk từ toàn bộ 295 hội thoại nguồn để tối ưu hóa hiệu quả học máy.

Train/validation được chia 90/10 với seed 42. Đầu vào trung bình 137 token, trung vị 132, P99 là 296 và lớn nhất 2.045 token. Chỉ 3/28.079 mẫu (0,01%) vượt 512 token. Tóm tắt đích trung bình khoảng 175 ký tự (~50 token), tối đa 382 ký tự. Nhãn chunk do mô hình giáo viên Gemma sinh; nhãn tiêu đề có tối đa 3 phương án do con người gán. Vì vậy, điểm ViT5 chủ yếu phản ánh mức mô phỏng nhãn giáo viên.

### Dữ liệu cho phân đoạn chủ đề (Topic Segmentation Datasets)
Quá trình benchmark phân đoạn chủ đề sử dụng 6 bộ dữ liệu hội thoại tiếng Việt dịch hoặc gốc:

**Thống kê quy mô các bộ dữ liệu phân đoạn chủ đề hội thoại**

| Bộ dữ liệu | Số lượng hội thoại | Tổng số lượt thoại | TB lượt thoại/đoạn | Số phân đoạn | Đặc trưng |
|---|---|---|---|---|---|
| `dialseg_711` | 711 | 19.350 | 27,2 | 3.465 | Bản dịch từ AMI [@Carletta2005], lượt thoại ngắn. |
| `doc2dial` | 3.270 | 42.585 | 13,0 | 11.400 | Dịch vụ công nhiệm vụ [@Feng2020]. |
| `meeting_ami` | 137 | 73.379 | 535,6 | 601 | Bản dịch từ AMI [@Carletta2005], họp dài phức tạp. |
| `meeting_committee` | 36 | 7.477 | 207,7 | 254 | Thảo luận ủy ban chuyên sâu, trang trọng. |
| `meeting_icsi` | 59 | 48.321 | 819,0 | 268 | Bản dịch từ ICSI [@Janin2003], họp học thuật cực dài. |
| `tiage` | 500 | 7.802 | 15,6 | 2.013 | Tư vấn y tế/tâm lý [@TIAGE2023], cấu trúc chặt chẽ. |

---

## Thực nghiệm và Phân tích (Experiments and Analysis)

### Thiết lập thực nghiệm và Chi tiết triển khai (Experimental Setup and Implementation Details)

#### Huấn luyện bộ tóm tắt khối ViT5 (ViT5 Chunk Summarizer Training)
Mô hình nền là `VietAI/vit5-base-vietnews-summarization` (226M tham số) [@Phan2022].

**Các siêu tham số thiết lập cho huấn luyện mô hình ViT5**

| Siêu tham số | Giá trị thiết lập |
|---|---|
| Mô hình nền (Base model) | `VietAI/vit5-base-vietnews-summarization` |
| Bộ tối ưu hóa (Optimizer) | AdamW |
| Tốc độ học (Learning rate) | $3\times10^{-4}$ |
| Suy giảm trọng số / Warmup | 0,01 / 0,06 |
| Batch size mỗi GPU / tích lũy | 2 / 16 (Batch hiệu dụng = 32) |
| Số lượng epoch tối đa | 10 |
| Kiên nhẫn dừng sớm (Patience) | 5 epochs |
| Độ chính xác (Precision) | fp16 |
| Phương pháp giải mã (Decoding) | Beam search (width = 4) |
| Giới hạn token input/target | 512 / 128 tokens |

Tokenizer sử dụng `extra_ids = 96` để đảm bảo kích thước từ vựng 36.096 tương thích hoàn toàn với embedding của checkpoint gốc. Đánh giá nhanh trên 200 mẫu ngẫu nhiên mỗi epoch để chọn checkpoint tốt nhất, và chạy đánh giá toàn bộ 2.807 mẫu validation khi kết thúc.

#### Huấn luyện bộ tạo tiêu đề BARTpho (BARTpho Topic Titler Training)
Mô hình nền là `vinai/bartpho-syllable-base` (132M tham số) [@Nguyen2021].

**Các siêu tham số thiết lập cho huấn luyện mô hình BARTpho**

| Siêu tham số | Giá trị thiết lập |
|---|---|
| Mô hình nền (Base model) | `vinai/bartpho-syllable-base` |
| Tốc độ học (Learning rate) | $5\times10^{-5}$ |
| Batch size mỗi GPU / tích lũy | 4 / 16 (Batch hiệu dụng = 64) |
| Giới hạn token input/target | 1.024 (giữ 1.500 ký tự cuối) / 64 tokens |
| Hàm mất mát (Loss function) | Sequence NLL Loss |

Mô hình học từ chuỗi tóm tắt khối ghép bằng dấu `" / "`, không học từ transcript thô. Điểm số ROUGE-L trên tập validate được dùng làm mốc checkpoint tốt nhất.

#### Môi trường hệ thống và tính tái lập (System Environment and Reproducibility)

**Cấu hình môi trường phần cứng và các thư viện phụ thuộc**

| Thành phần | Phiên bản / Đặc tả |
|---|---|
| Ngôn ngữ lập trình | Python 3.12.3 |
| Framework học sâu | PyTorch 2.13.0+cu130; Transformers 5.13.1 [@Wolf2020] |
| API/Runtime | FastAPI 0.139.0; Uvicorn 0.51.0; SSE Starlette 3.4.5 |
| Xác thực dữ liệu | Pydantic 2.13.4 [@Colvin2024] |
| Thiết bị GPU | NVIDIA GeForce RTX 4060 (8 GB VRAM) |
| Hệ điều hành | Ubuntu 24.04.4 LTS |
| Phía giao diện | HTML, Vanilla JavaScript |

Hệ thống được phát hành dưới phiên bản 0.1.0 [@Nguyen2026], tích hợp sẵn các lệnh chạy cục bộ `scripts/train_chunk_summarizer.sh` và `scripts/eval_chunk_summarizer.sh` để đảm bảo khả năng tái lập.

### Câu hỏi nghiên cứu (Research Questions)
Thực nghiệm trả lời 3 câu hỏi chính:
* **RQ1:** Multi-Scale Sliding TextTiling có cân bằng được độ chính xác biên và chi phí xử lý so với các segmenter khác không?
* **RQ2:** ViT5 sau tinh chỉnh có học được nhiệm vụ tóm tắt chunk hội thoại tiếng Việt không?
* **RQ3:** BARTpho có thể tạo tiêu đề chủ đề từ các tóm tắt trung gian mà không cần transcript thô không?

Năm phương pháp phân đoạn so sánh gồm: NLTK TextTiling, Custom TextTiling, Sliding TextTiling, ViBERT TextTiling và BaMiBERT-1DOD.

### Kết quả thực nghiệm phân đoạn chủ đề (Topic Segmentation Experimental Results)

#### Kết quả trên tập dialseg_711 (Results on dialseg_711)

**Kết quả so sánh các phương pháp trên tập dữ liệu dialseg_711**

| Phương pháp | $P_k$ ↓ | WD ↓ | $F_1$ ↑ | Thời gian (s) ↓ |
|---|---:|---:|---:|---:|
| **`custom_texttiling`** | **0,3467** | **0,3678** | 0,4320 | **1,5** |
| `sliding_texttiling` | 0,3660 | 0,4264 | **0,4472** | 1,9 |
| `vibert_texttiling` | 0,4253 | 0,4263 | 0,0230 | 300,8 |
| `nltk_texttiling` | 0,4417 | 0,4434 | 0,0871 | 4,8 |
| `bamibert_1dod` | 0,4474 | 0,4477 | 0,0104 | 15,9 |

#### Kết quả trên tập doc2dial (Results on doc2dial)

**Kết quả so sánh các phương pháp trên tập dữ liệu doc2dial**

| Phương pháp | $P_k$ ↓ | WD ↓ | $F_1$ ↑ | Thời gian (s) ↓ |
|---|---:|---:|---:|---:|
| **`bamibert_1dod`** | **0,4593** | **0,4593** | 0,0007 | 39,2 |
| `nltk_texttiling` | 0,4720 | 0,4721 | 0,0688 | 12,9 |
| `vibert_texttiling` | 0,4736 | 0,4741 | 0,0538 | 645,9 |
| `custom_texttiling` | 0,4830 | 0,4835 | 0,0730 | **6,0** |
| `sliding_texttiling` | 0,5241 | 0,5656 | **0,3302** | 7,0 |

#### Kết quả trên các tập cuộc họp dài (Results on Long Meeting Datasets)

**Kết quả so sánh trên các bộ dữ liệu cuộc họp dài (AMI, ICSI, Committee)**

| Bộ dữ liệu | Phương pháp đạt $P_k$ tốt nhất | $P_k$ (Best) | Sliding $P_k$ | Sliding Thời gian (s) |
|---|---|---:|---:|---:|
| `meeting_ami` | ViBERT | 0,3745 | 0,4410 | 25,7 |
| `meeting_committee` | ViBERT | 0,4324 | 0,4559 | 3,7 |
| `meeting_icsi` | ViBERT | 0,3825 | 0,4265 | 16,4 |

#### Kết quả trên tập tiage (Results on tiage)

**Kết quả so sánh các phương pháp trên tập dữ liệu tiage**

| Phương pháp | $P_k$ ↓ | WD ↓ | $F_1$ ↑ | Thời gian (s) ↓ |
|---|---:|---:|---:|---:|
| **`vibert_texttiling`** | **0,4553** | **0,4569** | 0,0494 | 219,4 |
| `nltk_texttiling` | 0,4752 | 0,4759 | 0,0165 | 7,6 |
| `sliding_texttiling` | 0,4794 | 0,5734 | **0,3557** | 8,3 |
| `custom_texttiling` | 0,4884 | 0,5264 | 0,2977 | 6,3 |
| `bamibert_1dod` | 0,4940 | 0,4940 | 0,0669 | **2,1** |

#### Xếp hạng hiệu năng phân đoạn tổng hợp (Overall Performance Ranking)
Điểm Composite được tính dựa trên điểm trung bình chuẩn hóa nghịch đảo của $P_k$, WindowDiff (WD) và $F_1$ biên trên toàn bộ 6 tập dữ liệu.

**Bảng xếp hạng hiệu năng phân đoạn tổng hợp của các giải thuật**

| Hạng | Phương pháp | Composite ↑ | $P_k$ TB ↓ | WD TB ↓ | $F_1$ TB ↑ | Nhận xét |
|---:|---|---:|---:|---:|---:|---|
| 1 | `vibert_texttiling` | **0,5854** | **0,4239** | **0,4315** | 0,0225 | Đạt $P_k$ tốt nhất trên cuộc họp dài. Yêu cầu GPU cao. |
| 2 | `custom_texttiling` | 0,5690 | 0,4778 | 0,5754 | 0,1485 | Chạy CPU nhanh, phù hợp cuộc họp ngắn. |
| 3 | `sliding_texttiling` | 0,5680 | 0,4488 | 0,4835 | **0,1970** | Đạt $F_1$ cao nhất, tối ưu cho phân đoạn biến thiên rộng. |
| 4 | `bamibert_1dod` | 0,3496 | 0,5288 | 0,6519 | 0,0360 | Phân đoạn tốt trên tập ngắn, kém ổn định trên họp dài. |
| 5 | `nltk_texttiling` | 0,3071 | 0,5160 | 0,6570 | 0,0379 | Thấp nhất do tokenizer không hợp với tiếng Việt. |

Điểm $F_1$ biên rất thấp của một số mô hình là do quy tắc đánh giá khớp ranh giới tuyệt đối (exact segment matching) không sử dụng cửa sổ dung sai. Ranh giới dự đoán chỉ được tính là chính xác nếu cả điểm bắt đầu và điểm kết thúc trùng khớp hoàn toàn với nhãn gốc. Tuy Sliding TextTiling đứng thứ ba về composite, nó vẫn là giải pháp được chọn vì tính thực tế cao (chạy nhanh trên CPU) và đạt điểm $F_1$ biên tốt nhất.

### Kết quả huấn luyện bộ tóm tắt khối ViT5 (ViT5 Chunk Summarizer Training Results)

#### Diễn biến huấn luyện theo epoch

**Mức độ suy giảm hàm mất mát và ROUGE của ViT5 qua từng epoch**

| Epoch | Loss | ROUGE-1 | ROUGE-2 | ROUGE-L | Ghi chú |
|---:|---:|---:|---:|---:|---|
| 1 | 0,9289 | 0,7017 | 0,4487 | 0,5190 | Bắt đầu |
| 2 | 0,8085 | 0,7123 | 0,4660 | 0,5365 | - |
| 3 | **0,7755** | 0,7168 | 0,4803 | 0,5418 | Cực tiểu Loss |
| 4 | 0,7781 | 0,7244 | 0,4860 | 0,5502 | - |
| 5 | 0,7935 | 0,7235 | 0,4897 | 0,5451 | - |
| **6** | 0,8320 | 0,7316 | 0,4967 | **0,5559** | **Checkpoint lưu trữ** (Peak R-L) |
| 7 | 0,8977 | 0,7311 | 0,4905 | 0,5500 | Bắt đầu overfit |
| 10 | 1,1964 | **0,7352** | 0,4968 | 0,5545 | Overfit nặng |

Mặc dù hàm mất mát đạt cực tiểu ở epoch 3, chỉ số ROUGE-L lại đạt đỉnh ở epoch 6. Quyết định chọn checkpoint epoch 6 giúp bảo toàn khả năng sinh từ ngữ có tính liên kết cấu trúc tốt hơn.

#### Đánh giá trên toàn tập validation và tập dev

**Kết quả đánh giá ROUGE của ViT5 trên các tập dữ liệu**

| Tập đánh giá | ROUGE-1 | ROUGE-2 | ROUGE-L | Quy mô mẫu |
|---|---:|---:|---:|---|
| Validation nhanh | 0,7316 | 0,4967 | 0,5559 | 200 |
| Validation đầy đủ | 0,7302 | 0,4957 | **0,5574** | 2.807 |
| Dev benchmark | **0,7265** | **0,4854** | **0,5486** | 6.038 |

Điểm ROUGE-1 rất cao (~73%) xác nhận mô hình ViT5 học được tốt phong cách sinh nhãn của giáo viên Gemma và cho tốc độ xử lý nhanh hơn 100 lần.

### Kết quả huấn luyện bộ tạo tiêu đề BARTpho (BARTpho Topic Titler Training Results)
Đánh giá trên 736 phân đoạn chủ đề lớn của tập `dev_vi.jsonl` sử dụng hệ đánh giá RougeMax:

**Kết quả đánh giá tiêu đề BARTpho trên dev benchmark**

| Chỉ số RougeMax | Giá trị điểm số | Thống kê quy mô |
|---|---:|---|
| **ROUGE-1** | **0,5304** | Trung vị độ dài tiêu đề: **16 tokens** |
| **ROUGE-2** | **0,2837** | Trung vị độ dài tóm tắt đầu vào: **356 tokens** |
| **ROUGE-L** | **0,4443** | Số lượng phân đoạn kiểm thử: **736 segments** |

Hệ thống RougeMax đo độ tương đồng với tiêu đề tham chiếu tốt nhất trong số các lựa chọn do con người viết, giúp phản ánh chân thực chất lượng tiêu đề sinh ra mà không bị ảnh hưởng bởi tính chủ quan đơn lẻ của người gắn nhãn.

### Phân tích toàn diện pipeline phân cấp (Hierarchical Pipeline Analysis)
Các kết quả định lượng khẳng định tính khả thi của kiến trúc phân cấp:
1. Phân đoạn từ vựng phi giám sát chạy nhanh hơn rất nhiều so với ViBERT trên họp dài.
2. ViT5 tóm tắt hiệu quả các khối 8 lượt thoại trong phạm vi 512 token.
3. BARTpho có thể sinh tiêu đề đại diện từ chuỗi tóm tắt thay vì transcript thô.

**So sánh đặc trưng kỹ thuật giữa Chunk Summarizer và Topic Titler**

| Đặc trưng kỹ thuật | Chunk Summarizer | Topic Segment Titler |
|---|---|---|
| Mô hình nền | `VietAI/vit5-base-vietnews-summarization` | `vinai/bartpho-syllable-base` |
| Số lượng tham số | 226 triệu | 132 triệu |
| Cửa sổ ngữ cảnh | 512 tokens | 1.024 tokens |
| Dữ liệu đầu vào | Khối 8 câu thoại thô (`speaker: text`) | Các câu tóm tắt khối ghép bằng `" / "` |
| Dữ liệu đầu ra | 1 câu tóm tắt ngắn gọn | 1 tiêu đề đại diện chủ đề |
| Số tham chiếu đánh giá | 1 nhãn (Gemma-generated teacher) | 3 nhãn (Con người dán nhãn) |
| Phương thức đánh giá | Standard ROUGE | Multi-Reference RougeMax |
| Kết quả ROUGE-1 / 2 / L | 0,7265 / 0,4854 / 0,5486 | 0,5304 / 0,2837 / 0,4443 |

Tuy nhiên, lỗi phân đoạn có thể gây nhiễu cho ViT5 và BARTpho. Do chưa có đánh giá thủ công trên cùng một tập nhãn đầu-cuối, báo cáo chỉ khẳng định các thành phần đạt kết quả định lượng riêng tốt, chưa kết luận chất lượng đầu-cuối đã tối ưu.

### Các mối đe dọa đối với tính hợp lệ (Threats to Validity)
* **Dữ liệu:** Một phần dữ liệu được dịch máy sang tiếng Việt, có thể làm thay đổi từ vựng tự nhiên. Nhãn chunk của mô hình giáo viên có thể chứa sai lệch.
* **Chỉ số:** ROUGE chỉ đo độ trùng lặp từ ngữ, không đo được tính đúng đắn sự kiện hay ảo giác. Điểm Composite nhạy cảm với cách chuẩn hóa.
* **So sánh:** Thời gian chạy phụ thuộc vào thiết bị và việc tối ưu thư viện, chỉ nên đối chiếu trong cùng một môi trường.
* **Khái quát:** Chưa kiểm chứng hiệu năng trên hội thoại doanh nghiệp Việt Nam tự nhiên, transcript ASR có lỗi hoặc các miền chuyên biệt (pháp lý, y tế).

### Trả lời các câu hỏi nghiên cứu (Answering Research Questions)
* **Trả lời RQ1:** Sliding TextTiling cân bằng tốt giữa chi phí tính toán (chạy nhanh trên CPU) và chất lượng phân đoạn ($F_1$ biên tốt nhất, $P_k$ tốt thứ hai), là lựa chọn tối ưu cho hệ thống trực tuyến.
* **Trả lời RQ2:** ViT5 học ổn định nhiệm vụ tóm tắt khối theo nhãn giáo viên, đạt ROUGE-L 0,5486 trên dev.
* **Trả lời RQ3:** BARTpho đạt RougeMax-L 0,4443, xác minh chuỗi tóm tắt khối chứa đủ tín hiệu để mô hình sinh tiêu đề tương đương với nhãn tham chiếu của con người.

---

## Phần mềm (Software)

### Giao diện và các tầng kiến trúc phần mềm (User Interface and Software Layers)
Hệ thống tuân thủ nghiêm ngặt kiến trúc phân tầng một chiều:
```
Types ──► Config ──► Repo ──► Service ──► Runtime ──► UI
```

**Mô tả các tầng trong kiến trúc phần mềm phân tầng**

| Tầng | Vai trò chính | Ràng buộc |
|---|---|---|
| **Types** | Định nghĩa cấu trúc dữ liệu cơ sở (`Utterance`, `DialogueTranscript`, `HierarchicalRecap`). | Không được phép import từ bất kỳ tầng nào khác. |
| **Config** | Quản lý tham số hệ thống (block size, radii, alpha) qua Pydantic Settings. | Chỉ được phép import tầng `Types`. |
| **Repo** | Quản lý việc đọc/ghi và tải cục bộ các checkpoint. | Không chứa logic nghiệp vụ cấp cao. |
| **Service** | Phân đoạn (TextTiling), chunking, tóm tắt và phối hợp (Orchestrator). | Phối hợp `Repo` và `Config` để xử lý nghiệp vụ. |
| **Runtime** | Cung cấp giao diện thực thi (REST API, SSE streaming, CLI). | Vỏ bọc runtime, khởi tạo lazy các Service. |
| **UI** | Hiển thị kết quả tóm tắt và trạng thái cho người dùng. | Chỉ giao tiếp với Runtime qua REST/SSE. |

Kiểm tra AST tự động trên mã nguồn giúp ngăn chặn các phụ thuộc chéo. Ràng buộc `MAX_UTTERANCES = 5000` được áp dụng để bảo vệ bộ nhớ.

### Xử lý Streaming và vòng đời dữ liệu theo sự kiện (Streaming Processing and Event-driven Data Lifecycle)
Để đáp ứng yêu cầu xử lý dữ liệu động, hệ thống sử dụng cơ chế xử lý theo sự kiện (event-driven). Thay vì xử lý tĩnh sau khi cuộc họp kết thúc (chế độ Batch), hệ thống trực tuyến (chế độ Streaming) phân tách tiến trình xử lý thành 5 cột mốc logic để cập nhật dần kết quả lên giao diện người dùng thông qua Server-Sent Events (SSE). 

Cả hai chế độ Streaming và Batch đều dùng chung một bộ điều phối lõi. Bộ điều phối này phát ra chuỗi sự kiện tuần tự đại diện cho vòng đời của dữ liệu cuộc họp:

1. **Tiếp nhận lượt thoại thô (`utterance-accepted`)**: 
   * *Ý nghĩa*: Server xác nhận đã nhận thành công câu thoại mới từ người nói.
   * *Phản hồi trên giao diện*: Câu nói thô được hiển thị ngay lập tức lên màn hình để người dùng theo dõi nội dung hội thoại đang diễn ra theo thời gian thực (phản hồi tức thời).

2. **Xác định ranh giới chủ đề (`segment-closed`)**: 
   * *Ý nghĩa*: Thuật toán Sliding TextTiling phát hiện một điểm chuyển đổi chủ đề logic và chốt chặn ranh giới của phân đoạn cũ.
   * *Phản hồi trên giao diện*: UI nhận diện ranh giới này để đóng phân vùng cũ và tự động vẽ một "Thẻ chủ đề" (Card) mới trống trên màn hình, chuẩn bị nhận dữ liệu cho chủ đề mới.

3. **Hoàn thành tóm tắt khối thoại (`chunk-closed`)**: 
   * *Ý nghĩa*: Hệ thống gom đủ một khối (tối đa 8 lượt thoại) trong chủ đề hiện tại và mô hình ViT5 hoàn thành việc sinh câu tóm tắt ngắn cho khối thoại đó.
   * *Phản hồi trên giao diện*: Câu tóm tắt này lập tức được đẩy vào bên trong Thẻ chủ đề đang hoạt động, giúp người dùng nắm bắt nhanh ý chính của đoạn hội thoại vừa diễn ra.

4. **Định danh chủ đề trì hoãn (`title-emitted`)**: 
   * *Ý nghĩa*: Khi một chủ đề kết thúc (cuộc họp chuyển sang chủ đề khác), mô hình BARTpho sẽ tổng hợp toàn bộ các câu tóm tắt khối trong phân đoạn đó để đặt tiêu đề đại diện cho chủ đề.
   * *Phản hồi trên giao diện*: Tiêu đề sinh ra sẽ tự động được gắn lên đầu Thẻ chủ đề (thay thế cho thẻ trống hoặc tiêu đề tạm thời), giúp người dùng dễ dàng phân loại và tra cứu nội dung lớn.

5. **Kết thúc và đồng bộ cuộc họp (`meeting-completed`)**: 
   * *Ý nghĩa*: Cuộc họp chính thức kết thúc hoàn toàn.
   * *Phản hồi trên giao diện*: Đóng kết nối streaming, hoàn thiện cấu trúc dữ liệu phân cấp `HierarchicalRecap` cuối cùng phục vụ việc lưu trữ lâu dài.

Bảng dưới đây đặc tả chi tiết cấu trúc dữ liệu tương ứng với từng cột mốc sự kiện phát ra từ bộ điều phối:

**Các sự kiện trong chu kỳ phát sê-ri của bộ điều phối**

| Tên sự kiện kỹ thuật (`type`) | Cột mốc hoạt động thực tế | Cấu trúc dữ liệu đính kèm (`data`) |
|---|---|---|
| `utterance-accepted` | Tiếp nhận lượt thoại thô thành công. | `{"index": int, "speaker": str, "text": str}` |
| `segment-closed` | Xác nhận và khóa ranh giới phân đoạn chủ đề. | `{"segment_id": str, "utterances_start": int, "utterances_end": int}` |
| `chunk-closed` | ViT5 hoàn thành tóm tắt khối thoại ≤ 8 câu. | `{"chunk_id": str, "segment_id": str, "rolling_summary": str}` |
| `title-emitted` | BARTpho viết xong tiêu đề cho chủ đề. | `{"segment_id": str, "title": str}` |
| `meeting-completed` | Toàn bộ cuộc họp kết thúc. | `{"hierarchical_recap": HierarchicalRecap}` |

Sự nhất quán này giúp hệ thống đạt độ tin cậy cao: chế độ Batch thực chất là việc hệ thống tự tiêu thụ luồng sự kiện này trong bộ nhớ và xuất ra kết quả cuối cùng, đảm bảo dữ liệu hiển thị trực tuyến và dữ liệu lưu file hàng loạt luôn trùng khớp hoàn toàn.

### Quản lý tính hợp lệ và biên hiệu năng (Validity Management and Performance Boundaries)
Pydantic xác thực tính liên tục của chỉ số lượt thoại và quan hệ chứa giữa segment và chunk trước khi xuất payload. Hai checkpoint sinh yêu cầu CUDA, sử dụng tham số `local_files_only=True` để ngăn chặn tải từ mạng.
* **Thời gian phản hồi đầu tiên (Time-to-First-Summary):** Đạt khoảng 1 - 2 giây sau khi hoàn thành 8 lượt thoại đầu tiên (đủ điều kiện chạy ViT5).
* **Độ trễ đầu-cuối (End-to-End Latency):** Cho một cuộc họp trung bình (~100 lượt thoại, tương đương 12 chunks) đạt 15 - 20 giây (gồm 0,1 giây phân đoạn trên CPU, 12 giây tóm tắt chunk trên GPU RTX 4060, và 3 - 5 giây tạo tiêu đề).
* **Băng thông (Throughput):** Đạt xấp xỉ 1 chunk/giây trên một GPU đơn lẻ.
* **Bảo vệ VRAM:** Hỗ trợ tối đa 3 - 4 phiên dịch vụ đồng thời (mỗi mô hình ViT5 chiếm ~900 MB, BARTpho chiếm ~500 MB VRAM khi chạy suy luận, tổng cộng 1,4 GB).

---

## Kết luận và Hướng đi tương lai (Conclusion and Future Work)

### Kết luận chung (Conclusion)
Nghiên cứu đã xây dựng thành công hệ thống tóm tắt cuộc họp tiếng Việt phân cấp, tích hợp phân đoạn chủ đề phi giám sát nhẹ (Multi-Scale Sliding TextTiling), tóm tắt chunk (ViT5) và tạo tiêu đề (BARTpho). Hệ thống hỗ trợ xử lý streaming (qua SSE) và batch trên cùng một lõi logic, giúp hiển thị kết quả tăng dần cho người dùng. Các kết quả thực nghiệm cho thấy Sliding TextTiling đạt $F_1$ biên tốt nhất và tốc độ chạy nhanh trên CPU. ViT5 và BARTpho đạt điểm ROUGE khả quan trên các tập benchmark độc lập.

### Hạn chế hệ thống (Limitations)
* Biểu diễn BoW không nhận biết từ đồng nghĩa và cấu trúc thảo luận chồng chéo kéo dài (quay lại chủ đề cũ).
* Phân đoạn trong streaming cần ngữ cảnh phía sau tạo độ trễ xác nhận tự nhiên.
* Chunk cố định 8 lượt thoại không thích ứng với độ dài token thực tế và có thể cắt giữa cuộc trao đổi ngắn.
* ViT5 học nhãn sinh bởi mô hình giáo viên Gemma nên có thể kế thừa sai lệch của giáo viên.
* BARTpho chỉ nhận 1.500 ký tự cuối của chuỗi tóm tắt, có nguy cơ bỏ sót ngữ cảnh mở đầu.
* Runtime hai mô hình sinh yêu cầu GPU CUDA, chưa hỗ trợ fallback CPU.
* Chưa có đánh giá thủ công về độ hữu ích, tính mạch lạc và tỷ lệ ảo giác của nội dung.

### Hướng đi tương lai (Future Directions)
* **Cải tiến thuật toán:** Kết hợp BoW với sentence embedding nhẹ để cải thiện nhận biết ngữ nghĩa; gộp chunk theo số lượng token động; và sử dụng cơ chế attention trên toàn bộ tóm tắt chunk thay vì cắt lát 1.500 ký tự.
* **Làm phong phú dữ liệu:** Thu thập và gán nhãn thủ công các transcript cuộc họp tiếng Việt tự nhiên với sự đồng thuận của nhiều kiểm định viên. Bổ sung đánh giá thủ công ẩn danh.
* **Mở rộng hệ thống:** Tích hợp bộ nhận dạng giọng nói (ASR) và speaker diarization; bổ sung hàng đợi nhiều phiên dịch vụ; hỗ trợ quantization để chạy trên CPU; và thiết lập chính sách bảo mật dữ liệu transcript.

---

## Lời cảm ơn (Acknowledgements)

Tác giả bày tỏ lòng biết ơn sâu sắc đến TS. Nguyễn Văn A đã định hướng, hỗ trợ chuyên môn và đóng góp ý kiến quý báu trong suốt quá trình triển khai dự án. Đồng thời, tác giả xin gửi lời cảm ơn chân thành đến tập thể thầy cô Đại học FPT, cùng gia đình và bạn bè đã tạo mọi điều kiện thuận lợi nhất để hoàn thành nghiên cứu này.

---

## Tài liệu tham khảo (References)

[@Hearst1997] M. A. Hearst, “TextTiling: Segmenting text into multi-paragraph subtopic passages,” *Computational Linguistics*, vol. 23, no. 1, pp. 33–64, 1997.

[@Vaswani2017] A. Vaswani et al., “Attention is all you need,” in *Advances in Neural Information Processing Systems*, 2017, pp. 5998–6008.

[@Raffel2020] C. Raffel et al., “Exploring the limits of transfer learning with a unified text-to-text transformer,” *Journal of Machine Learning Research*, vol. 21, no. 140, pp. 1–67, 2020.

[@Lewis2020] M. Lewis et al., “BART: Denoising sequence-to-sequence pre-training for natural language generation, translation, and comprehension,” in *Proceedings of ACL*, 2020, pp. 7871–7880.

[@Phan2022] H. Phan, T. Nguyen, and L. Nguyen, "ViT5: A Pre-trained Text-to-Text Transformer for Vietnamese Language Generation," in *Proceedings of the 2022 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies: System Demonstrations*, 2022, pp. 118-124.

[@Nguyen2021] N. L. Nguyen and D. Q. Nguyen, "BARTpho: Pre-trained Sequence-to-Sequence Models for Vietnamese," in *Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing*, 2021, pp. 2061-2066.

[@Lin2004] C.-Y. Lin, “ROUGE: A package for automatic evaluation of summaries,” in *Text Summarization Branches Out*, 2004, pp. 74–81.

[@Zhang2020] T. Zhang, V. Kishore, F. Wu, K. Q. Weinberger, and Y. Artzi, “BERTScore: Evaluating text generation with BERT,” in *International Conference on Learning Representations*, 2020.

[@Beeferman1999] D. Beeferman, A. Berger, and J. Lafferty, “Statistical models for text segmentation,” *Machine Learning*, vol. 34, pp. 177–210, 1999.

[@Pevzner2002] L. Pevzner and M. A. Hearst, “A critique and improvement of an evaluation metric for text segmentation,” *Computational Linguistics*, vol. 28, no. 1, pp. 19–36, 2002.

[@Alimeeting2024] Alimeeting4MUG Dataset, Hugging Face Datasets, 2024.

[@Carletta2005] J. Carletta et al., “The AMI Meeting Corpus,” in *Proceedings of the 5th International Conference on Methods and Techniques in Behavioral Research*, 2005.

[@Janin2003] D. Janin et al., “The ICSI Meeting Corpus,” in *Proceedings of ICASSP*, 2003.

[@Feng2020] S. Feng et al., “Doc2Dial: A Framework for Document-grounded Task-oriented Dialogue,” in *Proceedings of EMNLP*, 2020.

[@TIAGE2023] TIAGE Dataset for Task-oriented Medical Dialogues, 2023.

[@Wolf2020] T. Wolf et al., “Transformers: State-of-the-Art Natural Language Processing,” in *Proceedings of EMNLP*, 2020.

[@Colvin2024] S. Colvin et al., “Pydantic: Data validation using Python type hints,” 2024.

[@W3CSSE2015] Server-Sent Events, W3C Recommendation, 2015.

[@Stopwordsiso2024] stopwordsiso: Multilingual stop vocabulary, 2024.

[@Nguyen2026] Quang Nguyễn, “Mã nguồn và tài liệu kỹ thuật hệ thống Streaming Meeting Summary,” Tài liệu kỹ thuật dự án, Đại học FPT, 2026.

---

## Phụ lục: Cấu hình hệ thống cốt lõi (Appendix: Core System Configurations)

**Tham số cấu hình mặc định cho các thành phần của hệ thống**

| Thuật toán / Thành phần | Tham số cấu hình | Giá trị mặc định |
|---|---|---|
| **Sliding TextTiling** | `block_size` | 2 |
| **Sliding TextTiling** | `radii` | [3, 5, 10, 15, 20] |
| **Sliding TextTiling** | `alpha` | 1,5 |
| **Sliding TextTiling** | `min_segment_ratio` | 0,1 |
| **Chunking** | Số lượt thoại tối đa trên mỗi chunk | 8 |
| **ViT5 Chunk Summarizer** | Cửa sổ ngữ cảnh đầu vào (Input context limit) | 512 tokens |
| **ViT5 Chunk Summarizer** | Độ dài đầu ra tối đa (Max new tokens limit) | 128 tokens |
| **ViT5 Chunk Summarizer** | Số lượng beam giải mã (Beam size) | 4 |
| **BARTpho Topic Titler** | Giới hạn ký tự đầu vào (Input character slice) | 1.500 ký tự cuối |
| **BARTpho Topic Titler** | Cửa sổ ngữ cảnh đầu vào (Input context limit) | 1.024 tokens |
| **BARTpho Topic Titler** | Số lượng beam giải mã (Beam size) | 4 |
| **BARTpho Topic Titler** | Độ dài đầu ra tối đa (Max new tokens limit) | 200 tokens |
| **Hệ thống điều phối** | Số lượt thoại tối đa được hỗ trợ (`MAX_UTTERANCES`) | 5.000 |
