

## Đặc tả Dự án (Project Specification)

**Tóm tắt (Abstract)**

Các yếu tố Môi trường, Xã hội và Quản trị (ESG) đã trở thành các chỉ số quan trọng để đánh giá mức độ phát triển bền vững và các thực hành đạo đức của doanh nghiệp. Tuy nhiên, các hệ thống đánh giá ESG hiện tại thường đối mặt với các vấn đề như tiêu chí không nhất quán và độ bao phủ ngôn ngữ hạn chế, đặc biệt là đối với dữ liệu tiếng Việt. Để giải quyết những thách thức này, chúng tôi giới thiệu một khung đơn giản (framework) toàn diện cho việc phân loại văn bản và tính điểm ESG. Chúng tôi đã xây dựng bộ dữ liệu ViEn-ESG, một bộ dữ liệu song ngữ Việt - Anh chất lượng cao với 130.798 cặp câu - nhãn, được phát hành công khai nhằm thúc đẩy các nghiên cứu sâu hơn. Chúng tôi đã tinh chỉnh (fine-tune) mô hình dựa trên kiến trúc BERT cho nhiệm vụ phân loại ESG, được thiết kế đặc biệt cho các báo cáo tài chính và báo cáo bền vững bằng tiếng Việt. Các mô hình của chúng tôi thể hiện hiệu suất phân loại mạnh mẽ với độ chính xác 94,66% trên mô hình chỉ sử dụng tiếng Việt; trong kho lưu trữ mô hình song ngữ, điểm F1 đạt 94,83% đối với tiếng Anh và 91,94% đối với tiếng Việt. Bên cạnh việc phân loại, chúng tôi cũng triển khai một cơ chế tính điểm mạnh mẽ để tính toán điểm ESG bằng cách tổng hợp các tín hiệu cảm xúc (sentiment) trong từng khía cạnh ESG, mang lại một đánh giá định lượng và dễ giải thích hơn về tính bền vững của doanh nghiệp. Kết quả của chúng tôi nêu bật hiệu quả của các mô hình ngôn ngữ tiền huấn luyện (pre-trained language models) trong bối cảnh tài nguyên thấp, cùng với cơ chế tính điểm tích hợp, từ đó cung cấp các điểm chuẩn (benchmarks) mới và các công cụ thực tế cho phân tích ESG tại thị trường Việt Nam.

**Từ khóa:** Phân loại ESG, Tính điểm ESG, Bộ dữ liệu ESG.

## Mở đầu (Introduction)

Các yếu tố Môi trường, Xã hội và Quản trị (ESG) đã nhận được sự chú ý đáng kể như những chỉ số quan trọng để đánh giá tính bền vững, tác động đạo đức và việc tạo ra giá trị dài hạn của doanh nghiệp [@Kiriu2020]. Sự gia tăng của ESG như một khung nền tảng để đánh giá hiệu quả hoạt động của doanh nghiệp phản ánh một sự chuyển dịch mô hình trong cách các bên liên quan — bao gồm nhà đầu tư, cơ quan quản lý, người tiêu dùng và cộng đồng — đánh giá giá trị doanh nghiệp vượt ra ngoài các chỉ số tài chính truyền thống. Sự chuyển đổi này được thúc đẩy bởi các bằng chứng ngày càng tăng cho thấy các công ty có thực hành ESG mạnh mẽ sẽ thể hiện hiệu quả tài chính vượt trội trong dài hạn, giảm thiểu rủi ro vận hành và tăng cường niềm tin của các bên liên quan [@Aydomu2022].

Việc đánh giá hiệu quả ESG của một công ty giúp khám phá các góc nhìn sâu sắc về khía cạnh phi tài chính trong hoạt động của họ, đồng thời giúp các bên liên quan hiểu được đóng góp của họ đối với sự phát triển bền vững [@ebert]. Các yếu tố môi trường bao gồm tác động của công ty đối với tài nguyên thiên nhiên, các nỗ lực giảm thiểu biến đổi khí hậu, các biện pháp kiểm soát ô nhiễm và cam kết đối với các nguyên tắc kinh tế tuần hoàn. Các cân nhắc về xã hội bao gồm thực hành lao động, gắn kết cộng đồng, an toàn sản phẩm, bảo vệ dữ liệu, cùng các sáng kiến về đa dạng và hòa nhập. Các khía cạnh quản trị tập trung vào thành phần hội đồng quản trị, thù lao của ban điều hành, các biện pháp phòng chống tham nhũng, tính minh bạch trong báo cáo và bảo vệ quyền lợi của các bên liên quan [@Berg2019]. Việc đánh giá toàn diện các khía cạnh này mang lại cái nhìn tổng thể về trách nhiệm doanh nghiệp và các thực hành kinh doanh bền vững.

Nhu cầu ngày càng tăng đối với việc đánh giá khách quan và hiệu quả các hoạt động ESG của công ty đã làm nổi bật những hạn chế đáng kể của các phương pháp đánh giá thủ công truyền thống. Phân tích thủ công khối lượng dữ liệu văn bản khổng lồ như báo cáo bền vững, hồ sơ hàng năm, bài báo và tài liệu quản lý không chỉ tốn công sức và thời gian mà còn dễ gặp lỗi do con người, định kiến chủ quan và khả năng bị thao túng [@Luccioni2020]. Khối lượng thông tin liên quan đến ESG do các tập đoàn tạo ra đã tăng theo cấp số nhân, với các báo cáo bền vững hiện nay kéo dài hàng trăm trang và chứa ngôn ngữ phức tạp, sắc thái đòi hỏi phải có chuyên môn sâu để diễn giải chính xác. Hơn nữa, các tiêu chí đánh giá khác nhau giữa các tổ chức xếp hạng ESG khác nhau — chẳng hạn như MSCI, Sustainalytics và Refinitiv — thường dẫn đến các đánh giá không nhất quán và đôi khi mâu thuẫn về cùng một công ty, làm phức tạp hóa việc đưa ra nhận định khách quan cho các nhà đầu tư và các bên liên quan khác [@Billio2020,Lee2023].

Những tiến bộ gần đây trong xử lý ngôn ngữ tự nhiên (NLP) mở ra các giải pháp đầy triển vọng để tự động hóa và chuẩn hóa các đánh giá ESG, giải quyết cả thách thức về khả năng mở rộng lẫn tính nhất quán. Việc áp dụng các kỹ thuật NLP vào phân tích ESG đại diện cho một lĩnh vực đang phát triển nhanh chóng, bao gồm nhiều tác vụ phức tạp [@Avramov2022]. Các nhà nghiên cứu đang tận dụng NLP cho các hệ thống tính điểm ESG tự động có thể xử lý lượng lớn dữ liệu văn bản theo thời gian thực, phân loại văn bản vào các danh mục ESG cụ thể với độ chi tiết cao, xác định và định lượng các rủi ro cũng như cơ hội liên quan đến ESG, trích xuất thông tin có cấu trúc từ các báo cáo và nguồn tin tức phi cấu trúc, phát hiện các vấn đề ESG mới nổi từ các truyền thông tài chính và thực hiện phân tích cảm xúc đối với các công bố thông tin liên quan đến ESG [@sec-bert]. Các ứng dụng này mở rộng vượt ra ngoài việc phân loại đơn thuần để bao gồm các tác vụ phức tạp như đánh giá tính trọng yếu của ESG (ESG materiality assessment), đo lường tác động và mô hình hóa dự đoán các xu hướng hiệu quả ESG.

Một trọng tâm lớn trong lĩnh vực nghiên cứu này liên quan đến việc tận dụng các mô hình ngôn ngữ tiền huấn luyện (PLMs) mạnh mẽ, đặc biệt là các mô hình dựa trên kiến trúc Transformer như BERT [@bert] và các biến thể của nó bao gồm RoBERTa [@roberta], DistilBERT [@distilbert], Sentence-BERT [@sentence-bert], và các mô hình chuyên biệt theo miền như FinBERT và FinBERT-ESG [@finbert]. Các mô hình này đã chứng minh hiệu suất đặc biệt trong việc hiểu ngôn ngữ tài chính và bền vững phức tạp, nắm bắt các sắc thái ngữ cảnh vốn mang tính quyết định để đánh giá ESG chính xác. Tuy nhiên, bất chấp thành công của chúng, các phương pháp tiếp cận hiện tại để phân loại ESG bằng cách sử dụng các mô hình này thường dựa vào việc thêm các đầu phân loại (classification heads) cụ thể cho tác vụ trong quá trình tinh chỉnh, điều này làm phát sinh một số lo ngại về mặt phương pháp luận chưa được giải quyết thỏa đáng trong các tài liệu nghiên cứu.

Hơn nữa, các hệ thống phân loại ESG hiện tại thường gặp khó khăn với khả năng áp dụng đa ngôn ngữ, đặc biệt là đối với các thị trường mới nổi nơi việc báo cáo ESG được thực hiện bằng ngôn ngữ địa phương. Phần lớn các bộ dữ liệu và mô hình ESG hiện có đều lấy tiếng Anh làm trung tâm, tạo ra rào cản lớn cho việc phân tích ESG toàn cầu một cách toàn diện. Hạn chế này đặc biệt problematic đối với các nhà đầu tư quốc tế và các tập đoàn đa quốc gia cần đánh giá hiệu quả ESG trên các bối cảnh ngôn ngữ và văn hóa đa dạng. Sự thiếu hụt các bộ dữ liệu ESG được gắn nhãn chất lượng cao bằng các ngôn ngữ khác ngoài tiếng Anh là một điểm nghẽn dai dẳng trong việc phát triển năng lực phân tích ESG thực sự mang tính toàn cầu.

Trong luận văn này, chúng tôi giải quyết khoảng trống đó bằng cách giới thiệu một quy trình (pipeline) phân loại ESG toàn diện được thiết kế riêng cho tiếng Việt. **Các đóng góp chính của chúng tôi bao gồm:**

1. **Chúng tôi giới thiệu bộ dữ liệu ViEn-ESG, một bộ dữ liệu song ngữ (Việt – Anh) quy mô lớn bao gồm 130.798 mẫu ở cấp độ câu liên quan đến ESG, cùng với một tập con bổ sung gồm 6.430 câu được gắn nhãn cảm xúc. Theo hiểu biết của chúng tôi, đây là tài nguyên đầu tiên thuộc loại này được công bố công khai, nhằm thúc đẩy nghiên cứu trong phân tích ESG bằng tiếng Việt.**
2. **Chúng tôi phát triển một mô hình dựa trên BERT tiên tiến (state-of-the-art) cho nhiệm vụ phân loại ESG, được tinh chỉnh trên bộ dữ liệu của chúng tôi. Hệ thống này bao gồm mô hình chuyên dụng đầu tiên cho việc phân loại ESG tiếng Việt, đạt hiệu suất mạnh mẽ ở cả tiếng Anh và tiếng Việt, qua đó chứng minh tính hiệu quả của các mô hình ngôn ngữ tiền huấn luyện trong các bối cảnh tài nguyên thấp và chuyên biệt theo miền.**
3. **Chúng tôi giới thiệu một cơ chế tính điểm ESG mạnh mẽ nhằm tổng hợp các tín hiệu cảm xúc trên các khía cạnh Môi trường, Xã hội và Quản trị, mang lại một phương pháp tiếp cận định lượng và có thể giải thích được để đánh giá tính bền vững của doanh nghiệp.**
4. **Luận văn này thiết lập một điểm chuẩn (benchmark) mới cho việc phân loại ESG tự động bằng tiếng Việt và cung cấp các công cụ thực tế để hỗ trợ phân tích ESG cho các nhà nghiên cứu, những người hành nghề và các bên liên quan.**

---

## Nghiên cứu liên quan (Related Work)

### Các phương pháp tiếp cận phân loại văn bản ESG (ESG Text Classification Approaches)

==Tổng quan từ các nghiên cứu khác==
Mô hình E-BERT [@ebert], được huấn luyện đặc biệt dựa trên kiến trúc BERT của Google cho các tác vụ xếp hạng ESG, đã đạt được độ chính xác đáng chú ý là 93% trong việc tự động hóa quy trình đánh giá, hướng tới các kết quả chính xác và nhất quán. Các mô hình dựa trên BERT khác cũng cho thấy kết quả mạnh mẽ trong các tác vụ như phân loại câu là bền vững hoặc không bền vững hoặc xác định các vấn đề ESG. Ngoài ra, nghiên cứu tinh chỉnh SEC-BERT [@sec-bert-ft] đã phát triển một mô hình SEC-BERT [@sec-bert] thích ứng theo miền để phát hiện các vấn đề liên quan đến ESG từ tin tức tài chính, đạt được hiệu suất cải thiện thông qua tiền tinh chỉnh trong miền (in-domain pre-fine-tuning). Hệ thống của họ phân loại tin tức thành 33 loại vấn đề ESG và vận hành công cụ Phát hiện Vấn đề ESG (EID), cho phép các nhà đầu tư xác định rủi ro ESG một cách hiệu quả. Nghiên cứu cũng khám phá việc tăng cường dữ liệu đa ngôn ngữ và các mô hình cơ sở zero-shot dựa trên LLM, nhận thấy các mô hình chuyên biệt theo miền mang lại hiệu quả cao hơn rõ rệt.

ESG-KIBERT [@esg-kibert], một mô hình dựa trên BERT được huấn luyện nâng cao trên các kho ngữ liệu chuyên biệt về ESG, tích hợp cơ chế chú ý cứng (hard attention mechanism) để nâng cao hiệu suất phân loại ESG. Mô hình đạt độ chính xác 99,72% trên tác vụ bốn lớp (E, S, G, None) và được kết hợp với phân tích cảm xúc cùng hệ thống trọng số đặc thù theo ngành bằng cách sử dụng bản đồ tính trọng yếu của SASB để tạo ra các xếp hạng ESG minh bạch và nhận biết được miền chuyên biệt.

ESGify [@esgify], một mô hình mã nguồn mở dựa trên NLP được xây dựng trên MPNet [@mpnet] cho nhiệm vụ phân loại rủi ro ESG đa nhãn. Tận dụng bộ dữ liệu gồm 14,000 câu được gán nhãn thủ công từ các báo cáo ESG, mô hình đạt được hiệu suất vượt trội so với GPT-3.5 nhờ sử dụng các chiến lược tăng cường dữ liệu phù hợp như dịch ngược (back translation) và các ví dụ do LLM tạo ra.

Bất chấp những tiến bộ này, các phát triển gần đây cũng đã khám phá việc đánh giá hiệu quả ESG thông qua các phương pháp học máy [@Jiang2024], nơi các nhà nghiên cứu đã phát triển các khung làm việc để đánh giá hiệu quả bền vững của doanh nghiệp bằng cách sử dụng các kỹ thuật phân tích tiên tiến và bộ dữ liệu có cấu trúc từ các công ty thuộc danh sách Fortune 500. Sự xuất hiện của các bộ dữ liệu ESG chuyên biệt theo miền đã mở rộng sang các ứng dụng chuyên sâu như tính khả giải thích của xếp hạng ESG [@DelVitto2023], nơi các nhà nghiên cứu phát triển các kho ngữ liệu được gắn nhãn được thiết kế cụ thể để hiểu và diễn giải các phương pháp tính điểm ESG thông qua các kỹ thuật học máy.

### Khung đánh giá và tính điểm ESG (ESG Scoring and Evaluation Frameworks)

Mô hình Rasch [@Soares2024] đã đề xuất một khung làm việc đổi mới cho việc tính điểm ESG bằng cách kết hợp NLP với Lý thuyết Ứng đáp Câu hỏi (IRT). Sử dụng các bài báo tiếng Bồ Đào Nha về Petrobras, phương pháp này đã trích xuất cảm xúc liên quan đến ESG và chứng minh tính mạnh mẽ về mặt tâm trắc học của nó, mang lại các động lực thời gian đáng tin cậy hơn trong hiệu quả ESG. Tương tự, Patel và các cộng sự [@Patel2023] đã phát triển một hệ thống tính điểm ESG có hệ thống bằng cách tận dụng Phân tích Mạng lưới Xã hội (SNA) và học máy, nêu bật cách mạng lưới các bên liên quan và cảm xúc văn bản có thể được mô hình hóa chung để tạo ra các xếp hạng ESG toàn diện và bền vững hơn. Một nghiên cứu khác [@Zhang2023] đã cung cấp một khảo sát về các phương pháp tính điểm ESG dựa trên cảm xúc, nhấn mạnh rằng việc tính điểm dựa trên xác suất với các mô hình học sâu tiên tiến như FinBERT mang lại độ nhạy cao hơn đối với ngôn ngữ sắc thái so với các phương pháp cảm xúc dựa trên tỷ lệ.

Xây dựng trên những nền tảng này, ESG-KIBERT [@esg-kibert] đại diện cho một sự chuyển dịch mô hình trong đánh giá ESG định hướng bằng cảm xúc. Mô hình mở rộng BERT thông qua tiền huấn luyện trên các kho ngữ liệu chuyên biệt về ESG và thực hiện đồng thời phân tích phân loại ESG và phân tích cảm xúc ở cấp độ câu. ESG-KIBERT tích hợp sâu hơn các trọng số tính trọng yếu đặc thù theo ngành của SASB, đảm bảo rằng điểm cảm xúc không chỉ chính xác về mặt ngôn ngữ mà còn phù hợp về mặt tài chính và lĩnh vực kinh doanh. Các kết quả thực nghiệm cho thấy nó vượt trội hơn cả các mô hình dựa trên tỷ lệ và các mô hình dựa trên bằng chứng, đạt độ chính xác 99,72% và có sự tương đồng mạnh mẽ với các điểm chuẩn của MSCI. Việc tổng hợp minh bạch phân cực cảm xúc và trọng số nhạy cảm với lĩnh vực đã thiết lập nó như một phương pháp tiên tiến cho việc tính điểm ESG.

### Các bộ dữ liệu và tài nguyên chuyên biệt về ESG (ESG-Specific Datasets and Resources)

Việc phát triển các bộ dữ liệu chuyên biệt cho các ứng dụng NLP và AI theo miền ngày càng trở nên quan trọng khi các nhà nghiên cứu tìm cách giải quyết các thách thức và yêu cầu độc đáo của các lĩnh vực chuyên môn khác nhau. Trong khi các bộ dữ liệu đa mục đích như OpenWebText [@openwebtext], Common Crawl [@commoncrawl] và The Pile [@thepile] đã cung cấp độ bao phủ ngôn ngữ rộng rãi cho việc tiền huấn luyện các mô hình ngôn ngữ lớn, các ứng dụng chuyên biệt theo miền đòi hỏi các tài nguyên có mục tiêu rõ ràng hơn. Trong miền y sinh, các ví dụ nổi tiếng bao gồm MIMIC-III [@mimic3] cho phân tích ghi chú lâm sàng, PubMed [@pubmed] cho khai thác tài liệu y sinh và BioASQ-QA [@bioasq-qa] cho hệ thống trả lời câu hỏi y sinh. Trong miền tài chính, các bộ dữ liệu như FiQA [@fiqa] cho tác vụ trả lời câu hỏi và phân tích cảm xúc trong văn bản tài chính đã cho phép đạt được những tiến bộ trong NLP tài chính chuyên sâu. Cộng đồng thị giác máy tính đã được hưởng lợi to lớn từ ImageNet [@imagenet], công cụ thúc đẩy các tiến bộ trong phân loại hình ảnh và học chuyển giao, trong khi xử lý tiếng nói đã tiến bộ với các kho ngữ liệu như LibriSpeech [@librispeech] cho nhận dạng tiếng nói tự động. Những tài nguyên chuyên biệt theo miền này đã chứng minh tầm quan trọng cốt lõi của các bộ dữ liệu mục tiêu trong việc phát triển các hệ thống AI mạnh mẽ có khả năng hiểu được ngôn ngữ sắc thái, thông tin hình ảnh và thuật ngữ chuyên ngành của các miền kỹ thuật và chuyên môn.

Trong miền ESG, các bộ dữ liệu rất khan hiếm. Các bộ dữ liệu ESG ban đầu chủ yếu lấy tiếng Anh làm trung tâm và có quy mô tương đối nhỏ. Schimanski và các cộng sự [@Tobias2024] đã phát triển ba bộ dữ liệu chuyên biệt quy mô 2.000 câu được thiết kế cho việc phân loại văn bản ESG chính xác. Một bộ dữ liệu đáng chú ý khác được tạo ra bởi [@esgminer], các tác giả đã thu thập hơn 450.000 tiêu đề báo, với khoảng 27.000 tiêu đề liên quan đến ESG từ tài khoản Twitter của tờ The Guardian. Sau đó, họ đã gán nhãn thủ công các tiêu đề phù hợp với các khía cạnh ESG sau khi kiểm tra các thẻ (tags) về mức độ liên quan đến ESG.

Các phương pháp tiếp cận đa ngôn ngữ đã nhận được sự chú ý đặc biệt, chẳng hạn như ESG-Kor [@esgkor] đại diện cho một nỗ lực tiên phong trong việc phát triển bộ dữ liệu ESG đa ngôn ngữ, cung cấp một bộ dữ liệu tiếng Hàn toàn diện bao gồm 118.946 câu cho nhiệm vụ trích xuất thông tin liên quan đến ESG với các nhãn thủ công dựa trên các quy tắc khách quan từ các cơ quan đánh giá ESG. Bộ dữ liệu này đặc biệt nhắm vào việc trích xuất thông tin Môi trường, Xã hội và Quản trị từ các báo cáo bền vững của các công ty Hàn Quốc, giải quyết khoảng trống nghiêm trọng về tài nguyên ESG phi tiếng Anh và chứng minh hiệu suất phân loại đáng kể với các mô hình ngôn ngữ tiền huấn luyện tiếng Hàn. Mặc dù các tác vụ ESG đa ngôn ngữ đang dần xuất hiện, liên quan đến các bộ dữ liệu bằng các ngôn ngữ như tiếng Trung [@Pontes2023], tiếng Anh [@chen-etal-2023-multi-lingual], tiếng Pháp và tiếng Nhật [@kao-etal-2024-imntpu], một phần lớn các nghiên cứu hiện tại vẫn tập trung chủ yếu vào dữ liệu tiếng Anh. Gần đây hơn, điểm chuẩn ESG-Activities [@esgactive] giới thiệu một phương pháp tiếp cận mới cho việc phân loại văn bản ESG bằng cách tập trung vào các hoạt động môi trường ở mức độ chi tiết bao gồm 1.325 đoạn văn bản được gắn nhãn như được định nghĩa trong phân loại ESG của EU. Bộ dữ liệu này kết hợp một cách độc đáo dữ liệu được tinh chọn thủ công với các ví dụ được tạo nhân tạo nhằm nâng cao hiệu suất mô hình, chứng minh rằng các mô hình nhỏ hơn được tinh chỉnh có thể vượt trội hơn các giải pháp thương mại lớn hơn trong các tác vụ phân loại ESG cụ thể.

Phần còn lại của luận văn này được tổ chức như sau. Trong Mục METHOD, chúng tôi mô tả phương pháp luận và trình bày các mô hình ngôn ngữ được lựa chọn sử dụng cho phân loại ESG. Mục DATASET giới thiệu bộ dữ liệu ViEn-ESG, chi tiết hóa quy trình thu thập dữ liệu, phương pháp luận gắn nhãn và phân tích dữ liệu. Trong Mục CONFIG, chúng tôi phác thảo cấu hình mô hình, tiếp theo là phần đánh giá toàn diện về hiệu suất mô hình trên các tác vụ phân loại ESG tiếng Việt và đa ngôn ngữ. Mục DEMO trình bày bản thử nghiệm (demo) cho công cụ phân loại ESG của chúng tôi. Cuối cùng, Mục CONCLUSION kết luận luận văn và thảo luận về các hướng đi cho công việc tương lai.

---

## Phương pháp luận (Methodology)

[[Methodology - phân tích nguồn gốc]]

Phương pháp tiếp cận của chúng tôi tận dụng các kỹ thuật Xử lý Ngôn ngữ Tự nhiên (NLP) tiên tiến, cụ thể là tinh chỉnh một mô hình ngôn ngữ dựa trên kiến trúc transformer tiền huấn luyện, để giải quyết tác vụ phân loại ESG trong ngôn ngữ tiếng Việt. Các yếu tố ESG được coi là các chỉ số quan trọng để đánh giá tính bền vững và khả năng tạo giá trị của doanh nghiệp, và NLP đã nổi lên như một công cụ có giá trị để phân tích dữ liệu văn bản liên quan. Do thách thức đã được xác định về sự hạn chế của các bộ dữ liệu ESG toàn diện được gắn nhãn, đặc biệt là đối với các ngôn ngữ ít tài nguyên như tiếng Việt, phương pháp luận của chúng tôi tập trung vào việc xây dựng một hệ thống phân loại mạnh mẽ được hỗ trợ bởi một bộ dữ liệu quy mô lớn mới được xây dựng.

### Phân loại ESG sử dụng các mô hình dựa trên kiến trúc BERT (ESG Classification using BERT-based Models)

BERT [@bert] là một mô hình ngôn ngữ tiên tiến được sử dụng trong nhiều tác vụ NLP, lần đầu tiên được giới thiệu trong bài báo “BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding”. Sức mạnh của BERT đến từ một vài yếu tố. Thứ nhất, BERT có kích thước nhỏ gọn, chỉ với 110 triệu tham số. Thứ hai, mạng thần kinh được thiết kế có mục đích để nắm bắt các mối quan hệ phức tạp giữa các từ và các câu. BERT là một mô hình kiến trúc mã hóa (encoder model) dựa trên kiến trúc Transformer [@transformer] — với cơ chế tự chú ý (self-attention) ở lõi của nó — được thiết kế để tạo ra các biểu diễn ngữ cảnh cho các từ hoặc các câu. Với bản chất hai chiều (bidirectional), BERT xuất sắc trong việc hiểu ngữ nghĩa tổng thể của một câu, khiến nó rất phù hợp cho các tác vụ như phân loại thông tin ESG. Thứ ba, BERT đã được tiền huấn luyện trên các bộ dữ liệu văn bản lớn bao gồm BookCorpus và English Wikipedia, cho phép mô hình học được cả biểu diễn từ và câu, từ đó tạo điều kiện thuận lợi cho học chuyển giao (transfer learning).

BERT là một khung làm việc học chuyển giao, và việc sử dụng nó thường bao gồm hai giai đoạn: tiền huấn luyện và tinh chỉnh. Nhiều mô hình BERT đã được tiền huấn luyện trên các bộ dữ liệu văn bản chưa được gắn nhãn khác nhau. Các mô hình này sau đó có thể được áp dụng trực tiếp cho một loạt các tác vụ: phân loại văn bản, nhận dạng thực thể có tên (NER), trả lời câu hỏi, hoặc phân loại cảm xúc. Sau khi phiên bản BERT gốc được giới thiệu, một vài mô hình cải tiến như RoBERTa [@roberta], ALBERT [@albert], DistilBERT [@distilbert] đã được phát triển dựa trên kiến trúc của BERT, đạt được hiệu suất cao hơn thông qua các sửa đổi nhỏ trong thiết kế mô hình hoặc các siêu tham số tiền huấn luyện. Các mô hình tiền huấn luyện này được cung cấp công khai cho cộng đồng nghiên cứu và có thể được tinh chỉnh sâu hơn cho các tác vụ ngôn ngữ cụ thể.

Chúng tôi thử nghiệm với một bộ các mô hình dựa trên BERT, mỗi mô hình được tinh chỉnh cụ thể cho nhiệm vụ phân loại ESG. Các mô hình này dựa trên các kiến trúc đã được thiết lập và nổi tiếng với thành công trong một loạt các tác vụ phân loại NLP. Mục tiêu của chúng tôi là đánh giá hiệu quả của các nền tảng mô hình khác nhau trong bối cảnh ESG tiếng Việt.

Cách tiếp cận tiêu chuẩn cho các tác vụ phân loại sử dụng các mô hình dựa trên BERT bao gồm một quy trình tinh chỉnh có cấu trúc đi theo một quy trình nhiều giai đoạn giúp chuyển đổi văn bản đầu vào thành các dự đoán phân loại thông qua các thành phần chuyên dụng cho từng tác vụ cụ thể.

Xét một câu đầu vào $X = \{x_1, x_2, \dots, x_n\}$ có độ dài $n$. Quy trình phân loại có thể được biểu diễn một cách chính thức thông qua các phép biến đổi tuần tự sau đây.

**Nhúng đầu vào (Input Embedding):**
Câu đầu vào trải qua một phép biến đổi nhúng ban đầu nhằm chuyển đổi các token rời rạc thành các biểu diễn vectơ dày đặc:

$$
H_0 = \text{Embedding}(X)
$$

Trong đó $H_0 \in \mathbb{R}^{n \times d}$ đại diện cho các nhúng token ban đầu với số chiều $d$, bao gồm cả các token đặc biệt như [CLS] và [SEP] vốn cung cấp thông tin cấu trúc cho mô hình.

**Mã hóa Transformer (Transformer Encoding):**
Đầu vào được nhúng đi qua nhiều lớp transformer, nơi mỗi lớp áp dụng các phép biến đổi tự chú ý và truyền thẳng (feed-forward):

$$
H_L = \text{Transformer}_L(H_{L-1}), \quad L = 1, 2, \dots, M
$$

Trong đó $M$ là tổng số lớp transformer, và $H_L \in \mathbb{R}^{n \times d}$ đại diện cho các trạng thái ẩn theo ngữ cảnh sau lớp thứ $L$. Mỗi lớp transformer nắm bắt các cấu trúc và mối quan hệ phụ thuộc ngôn ngữ ngày càng phức tạp.

**Đầu phân loại (Classification Head):**
Phép phân loại cuối cùng được thực hiện bằng cách sử dụng một đầu phân loại tuyến tính chuyên dụng hoạt động trên biểu diễn của token [CLS]:

$$
y = \text{Softmax}(W_c H_M[0] + b_c)
$$

Trong đó $H_M[0] \in \mathbb{R}^{d}$ là biểu diễn của token [CLS] sau lớp transformer cuối cùng, $W_c \in \mathbb{R}^{|Y| \times d}$ là ma trận trọng số phân loại, $b_c \in \mathbb{R}^{|Y|}$ là vectơ chệch phân loại, $Y = \{E, S, G, N\}$ là tập hợp các nhãn phân loại ESG và $y \in \mathbb{R}^{|Y|}$ đại diện cho phân phối xác suất lớp được dự đoán.

**Mục tiêu huấn luyện (Training Objective):**
Các tham số của mô hình được tối ưu hóa để giảm thiểu hàm mất mát entropy chéo (cross-entropy loss) giữa nhãn dự đoán và nhãn thực tế:

$$
\mathcal{L}_{\text{CE}} = -\sum_{i=1}^{|Y|} y_i \log(\hat{y}_i)
$$

Trong đó $\mathcal{L}_{\text{CE}}$ là hàm mất mát Entropy chéo, $y_i$ là nhãn thực tế, và $y \in \{0,1,2,3\}^{|Y|}$ là vectơ nhãn thực tế đã được mã hóa.

### Hệ thống tính điểm (Scoring System)

Bộ dữ liệu được xây dựng để hỗ trợ nhiệm vụ phân loại cảm xúc ESG bằng tiếng Việt. Mỗi mẫu trong bộ dữ liệu bao gồm một đoạn văn bản tiếng Việt và các nhãn tương ứng với miền đó, đại diện cho cảm xúc tiêu cực, trung tính hoặc tích cực (ví dụ: Môi trường Tiêu cực, Môi trường Trung tính, Môi trường Tích cực).

Để nâng cao hiệu quả phân tích và đảm bảo tính chính xác trong quá trình huấn luyện, chúng tôi đã chia bộ dữ liệu ban đầu thành ba tập con, mỗi tập đại diện cho một lớp chủ đề riêng biệt: E (Môi trường), S (Xã hội), và G (Quản trị). Sau khi phân chia, chúng tôi huấn luyện các mô hình riêng biệt cho từng lớp để phân biệt rõ ràng giữa các trạng thái cảm xúc (tiêu cực, trung tính và tích cực) trong phạm vi dữ liệu tương ứng. Cách tiếp cận phân chia này cho phép các mô hình tập trung vào và học hỏi các đặc điểm độc đáo của từng lớp, từ đó cải thiện độ chính xác và hiệu quả của quy trình phân tích. Chúng tôi tin rằng phương pháp này không chỉ nâng cao hiệu suất của các mô hình mà còn làm tăng tính tin cậy và độ chính xác trong việc phân loại cảm xúc cho từng lớp.

#### Kiến trúc mô hình tính điểm (Scoring Model Architecture)

Chúng tôi đã tinh chỉnh một mô hình ngôn ngữ dựa trên kiến trúc transformer tiền huấn luyện chuyên dụng cho văn bản tiếng Việt. Đối với mỗi miền ESG, một mô hình phân loại đa nhãn riêng biệt đã được xây dựng, tiếp nhận đầu vào đã được tiền xử lý và dự đoán các đầu ra tương ứng với các lớp cảm xúc tiêu cực, trung tính và tích cực. Kiến trúc mô hình bao gồm một mạng xương sống BERT tiêu chuẩn, tiếp theo là một lớp đầu ra dày đặc (dense output layer) cho dự đoán đa nhãn. Để giải quyết vấn đề mất cân bằng lớp, chúng tôi đã sử dụng hàm mất mát Entropy chéo nhị phân (Binary Cross-Entropy loss) kết hợp với các trọng số lớp tùy chọn. Tương tự như phân loại ESG, do đặc điểm của tiếng Việt, các khoảng trắng không được sử dụng để phân tách các từ trong từ ghép. Chúng tôi tiếp tục sử dụng công cụ ViTokenizer trong thư viện Pyvi để phân tích chuỗi văn bản đầu vào và xác định chính xác ranh giới của từ.

Giai đoạn huấn luyện ban đầu bao gồm việc tinh chỉnh mô hình tiền huấn luyện duy nhất trên bộ dữ liệu được gắn nhãn của miền ESG đã chọn. Các siêu tham số, bao gồm tốc độ học (learning rate), kích thước lô (batch size) và số lượng kỷ nguyên (epochs) đã được tối ưu hóa thông qua các thử nghiệm và tinh chỉnh thực tế để cân bằng giữa tốc độ hội tụ và rủi ro quá khớp (overfitting). Các cơ chế dừng sớm (early stopping) đã được triển khai bằng cách giám sát hàm mất mát trên tập kiểm định và điểm số macro-F1 trên tập kiểm định được giữ lại.

Các chỉ số hiệu suất bao gồm độ chính xác (precision), độ triệu hồi (recall), và điểm F1-score cho từng lớp cảm xúc, cũng như các điểm trung bình macro, micro và trung bình có trọng số để cung cấp một đánh giá toàn diện. Tác động của dữ liệu nhãn giả (pseudo-labeled data) đã được phân tích cả về mặt định lượng (thông qua các chỉ số) và định tính (thông qua việc kiểm tra các dự đoán giả có độ tin cậy cao). Tất cả siêu dữ liệu thử nghiệm, bao gồm các phần chia nhãn, nhật ký huấn luyện và kết quả chi tiết, đều được lưu trữ để đảm bảo tính tái lập.

#### Tính toán và đánh giá điểm ESG (ESG Score Computation and Evaluation)

Dựa trên phương pháp được đề xuất trong nghiên cứu ESG-KIBERT [@esg-kibert], chúng tôi đã áp dụng phương pháp tính điểm ESG dựa trên các trọng số đặc thù theo ngành và phân tích cảm xúc. Mô hình cảm xúc phân loại mỗi câu thành ba danh mục cảm xúc: tích cực, trung tính hoặc tiêu cực, tương ứng với E, S, và G. Điểm cảm xúc được gán lần lượt là +1 (tích cực), 0 (trung tính) và -1 (tiêu cực), tạo ra một thang đo rõ ràng và cân bằng.

Chúng tôi áp dụng phương pháp này bởi vì khung tiêu chuẩn SASB được lựa chọn thay vì các khung khác như GRI hay Lực lượng Đặc nhiệm về Công bố Thông tin Tài chính Liên quan đến Khí hậu (TCFD) nhờ vào cách tiếp cận đặc thù theo ngành của nó, cho phép tùy chỉnh chính xác hơn các trọng số ESG. Hơn nữa, các tác giả đã căn chỉnh các phân loại ngành của SASB với khung phân ngành của MSCI để thiết lập một cấu trúc phân tích mạch lạc đáp ứng các yêu cầu của thị trường tài chính. Phương pháp này nhấn mạnh tầm quan trọng của các yếu tố ESG cụ thể đối với từng ngành, từ đó nâng cao tính tin cậy của quy trình đánh giá.

[Hình ảnh của Bản đồ tính trọng yếu dựa trên SASB cho việc tính trọng số yếu tố ESG theo ngành.] *(Lưu ý: Thay thế cho figures/esg_score_tab.png)*

Bản đồ tính trọng yếu minh họa các lĩnh vực ngành công nghiệp với các mức độ liên quan ESG khác nhau. Đổ bóng đậm đại diện cho các lĩnh vực liên kết với hơn 50% các ngành công nghiệp, trong khi đổ bóng nhạt biểu thị các lĩnh vực liên kết với ít hơn 50%. Các tác giả đã rút ra các giá trị định lượng để tăng cường tính nhất quán và tính trực quan của các đánh giá ESG. Trọng số được gán theo cường độ đổ bóng: 0.25 cho màu tím nhạt, đại diện cho giá trị trung vị của khoảng tầm quan trọng dưới 50%, và 0.75 cho màu tím đậm, đại diện cho giá trị trung vị của khoảng tầm quan trọng trên 50%. Tổng trọng số cho mỗi ngành được xác định bằng cách cộng các điểm số có trọng số trong từng trụ cột. Trụ cột Môi trường được phân loại là "E", Vốn Xã hội và Vốn Con người được nhóm lại dưới nhãn "S", và Mô hình Kinh doanh & Đổi mới cùng với Sự Lãnh đạo & Quản trị được phân loại là "G".

$$
ESG_{\text{company}} = W_E \sum_{i=1}^{N_E} S_{E,i} + W_S \sum_{j=1}^{N_S} S_{S,j} + W_G \sum_{k=1}^{N_G} S_{G,k}
$$

Trong đó $W_E, W_S, W_G$ đại diện cho trọng số đặc thù theo ngành đối với E, S, G mà công ty cụ thể đó thuộc về, và $S_{E,i}, S_{S,j}, S_{G,k}$ chỉ ra điểm cảm xúc được gán cho mỗi câu được gắn nhãn tương ứng là E, S, G. Dựa trên công thức được cung cấp bởi các tác giả trong bài báo, chúng tôi cũng đã áp dụng công thức tính toán xếp hạng ESG dựa trên các trọng số đặc thù theo ngành và phân tích cảm xúc.

### Lựa chọn mô hình (Model Selection)

Chúng tôi thử nghiệm với một bộ các mô hình dựa trên kiến trúc BERT, mỗi mô hình được tinh chỉnh đặc biệt cho nhiệm vụ phân loại ESG. Các mô hình này dựa trên các kiến trúc đã được thiết lập tốt và nổi tiếng với thành công trong một loạt các tác vụ phân loại NLP. Mục tiêu của chúng tôi là đánh giá hiệu quả của các nền tảng mô hình khác nhau trong bối cảnh ESG tiếng Việt.

Việc lựa chọn các mô hình dựa trên BERT làm nền tảng cho các bộ phân loại của chúng tôi xuất phát từ hiệu quả đã được chứng minh của chúng trên một phổ rộng các tác vụ NLP, bao gồm phân loại văn bản, trích xuất thông tin và phân tích cảm xúc. Kiến trúc Transformer, nền tảng xây dựng nên BERT và các biến thể của nó, xuất sắc trong việc nắm bắt các mối phụ thuộc khoảng cách xa và các mối quan hệ ngữ cảnh trong văn bản, điều này mang tính quyết định để hiểu được ngôn ngữ thường ẩn ý và phức tạp được sử dụng trong các công bố thông tin ESG.

Chúng tôi sử dụng một mô hình tiền huấn luyện được huấn luyện trên các bộ dữ liệu quy mô lớn để phát triển bộ phân loại ESG cho mô hình ESG tiếng Việt. Chúng tôi đã sử dụng PhoBERT [@phobert], cùng với các thử nghiệm sử dụng các mô hình ngôn ngữ tiếng Việt khác như ViSoBERT [@visobert], viBERT [@velectra] và vELECTRA [@velectra].

**Các mô hình được lựa chọn trong thử nghiệm của chúng tôi**

| Mạng xương sống (Backbone)              | Số tham số | Nguồn dữ liệu huấn luyện                                             |
| ------------------------------------------- | ------------ | ------------------------------------------------------------------------- |
| PhoBERT (2020)                              | 135M         | Wikipedia tiếng Việt (1GB), Báo chí tiếng Việt (19GB)               |
| ViSoBERT (2023)                             | 97M          | Bình luận trên mạng xã hội tiếng Việt (Facebook, TikTok, Youtube) |
| vELECTRA (2020)                             | 110M         | NewsCorpus, OscarCorpus (58.4 GB)                                         |
| viBERT (2020)                               | 115M         | Tập con dữ liệu 10GB của vELECTRA                                     |
| BERT-base-multilingual-uncased/cased (2017) | 168/179M     | BookCorpus, Wikipedia của 104 ngôn ngữ                                 |
| DistilBERT-base-multilingual-cased (2019)   | 168M         | BookCorpus, Wikipedia của 104 ngôn ngữ                                 |
| XLM-RoBERTa-base (2019)                     | 124/279M     | BookCorpus, Wikipedia, OpenWebText, Stories, CC-News (160GB)              |
| DeBERTa-v3-small/base (2022)                | 141/184M     | BookCorpus, Wikipedia, OpenWebText, Stories (78GB)                        |
| FinBERT (2022)                              | 109M         | Tinh chỉnh BERT trên dữ liệu tài chính TRC2                         |

Đối với thiết lập mô hình đa ngôn ngữ, chúng tôi đặc biệt chọn thử nghiệm với một bộ các mô hình, bao gồm BERT-base-cased, BERT-base-uncased, RoBERTa-base, XLM-RoBERTa-base, DeBERTa-v3-base, DeBERTa-v3-small, FinBERT và DistilBERT-base-cased, để cung cấp một phân tích so sánh. Điều này cho phép chúng tôi đánh giá không chỉ khả năng áp dụng chung của các mô hình transformer mà còn cả thế mạnh tương đối của các biến thể kiến trúc và chiến lược tiền huấn luyện khác nhau khi áp dụng vào miền cụ thể của văn bản ESG tiếng Việt. Quyết định tinh chỉnh các mô hình này, thay vì huấn luyện từ đầu, được thúc đẩy bởi nhu cầu tận dụng tri thức ngôn ngữ sâu rộng đã được mã hóa sẵn bên trong chúng, từ đó giảm thiểu các yêu cầu về dữ liệu và chi phí tính toán liên quan đến việc huấn luyện các mô hình lớn trên một bộ dữ liệu miền hạn chế. Các mô hình được chi tiết hóa trong Bảng trên.

---

## Bộ dữ liệu (Dataset)

Trong phần này, chúng tôi trình bày các bộ dữ liệu được sử dụng để phát triển và đánh giá các mô hình phân loại ESG của chúng tôi. Việc phân loại văn bản hiệu quả theo miền cụ thể đòi hỏi dữ liệu được gắn nhãn chất lượng cao nhằm nắm bắt được các đặc điểm ngôn ngữ và tính đa dạng chủ đề của miền mục tiêu. Chúng tôi đã thu thập một cách hệ thống các nội dung liên quan đến ESG từ các báo cáo bền vững của doanh nghiệp và các nguồn tin tức tài chính, tiếp theo là các quy trình tiền xử lý toàn diện, gắn nhãn thủ công và nhiều kỹ thuật gắn nhãn khác để tạo ra các nhãn thực tế khách quan (ground truth) đáng tin cậy cho mục đích huấn luyện và đánh giá. Bộ dữ liệu của chúng tôi có thể truy cập tại [https://huggingface.co/datasets/nguyen599/ViEn-ESG-100](https://huggingface.co/datasets/nguyen599/ViEn-ESG-100).

**Tổng quan về các bộ dữ liệu được sử dụng cho phân loại ESG và phân tích cảm xúc.**

| Loại dữ liệu | Ngôn ngữ   | Số câu | Nguồn                            | Kỹ thuật gắn nhãn |
| --------------- | ------------ | -------- | --------------------------------- | --------------------- |
| Phân loại ESG | Tiếng Anh   | 45.942   | Báo cáo doanh nghiệp, Tin tức | Gắn nhãn thủ công |
| Phân loại ESG | Tiếng Việt | 60.222   | Báo cáo doanh nghiệp, Tin tức | Gắn nhãn thủ công |
| Phân loại ESG | Tiếng Việt | 14.634   | Báo cáo doanh nghiệp, Tin tức | Gắn nhãn giả       |
| Phân loại ESG | Tiếng Việt | 10.000   | Dữ liệu tiếng Anh              | Dịch máy            |
| Cảm xúc ESG   | Tiếng Việt | 6.430    | Báo cáo doanh nghiệp           | Thủ công            |

### Mô tả bộ dữ liệu (Dataset Description)

Một viên đá tảng của nghiên cứu này là việc phát triển và sử dụng {bộ dữ liệu ViEn-ESG}, một kho ngữ liệu song ngữ (tiếng Anh và tiếng Việt) quy mô lớn, mới lạ được tuyển chọn đặc biệt cho các tác vụ phân loại ESG. Việc tạo ra bộ dữ liệu này được thúc đẩy bởi sự khan hiếm đáng kể của dữ liệu được gắn nhãn chất lượng cao công khai cho phân tích ESG, đặc biệt là đối với các ngôn ngữ ít tài nguyên như tiếng Việt. Giải quyết khoảng trống này là điều cốt lõi để thúc đẩy các ứng dụng NLP trong tài chính bền vững và đánh giá trách nhiệm doanh nghiệp tại các thị trường mới nổi. ViEn-ESG bao gồm tổng cộng 130.798 mẫu ở cấp độ câu, được thu thập và gán nhãn một cách tỉ mỉ để phục vụ như một nền tảng vững chắc cho việc huấn luyện và đánh giá các mô hình phân loại ESG. Ngoài ra, chúng tôi đã chọn một tập con gồm 6.430 câu từ bộ dữ liệu ViEn-ESG và tạo một nhãn phân đoạn bao gồm cảm xúc Tiêu cực, Trung tính hoặc Tích cực để nắm bắt các tín hiệu cảm xúc liên quan đến các phát biểu về ESG. Tập con được gắn nhãn cảm xúc này đóng vai trò quan trọng trong việc huấn luyện thành phần phân tích cảm xúc thuộc khung làm việc của chúng tôi, thành phần này sau đó được tích hợp vào cơ chế tính điểm ESG. Bằng cách tận dụng các nhãn cảm xúc này, chúng tôi cho phép mô hình tính toán điểm số ESG chi tiết bằng cách tổng hợp các phân phối cảm xúc trên các khía cạnh Môi trường, Xã hội và Quản trị. Thiết kế này đảm bảo rằng quy trình tính điểm vừa có thể giải thích được vừa có cơ sở định lượng, cung cấp một công cụ thực tế để đánh giá tính bền vững của doanh nghiệp vượt ra ngoài việc phân loại danh mục đơn thuần.

[Hình ảnh sơ đồ tổng quan quy trình gán nhãn dữ liệu (Pipeline_data.pdf)]

### Thu thập dữ liệu (Data Collection)

Các báo cáo bền vững của doanh nghiệp đại diện cho các công bố toàn diện về hiệu quả hoạt động của tổ chức trên các khía cạnh môi trường, xã hội và quản trị, đóng vai trò là phương tiện chính để truyền tải các thành tựu phi tài chính và các cam kết ESG tới các nhóm bên liên quan đa dạng. Các tài liệu này đã trở nên nổi bật khi các khung quản lý ngày càng bắt buộc tính minh bạch về ESG và các nhà đầu tư yêu cầu trách nhiệm giải trình cao hơn liên quan đến các thực hành kinh doanh bền vững [@Agbakwuru2024]. Sự nhấn mạnh ngày càng tăng vào việc công bố thông tin ESG đã dẫn dắt các công ty thuộc nhiều ngành công nghiệp khác nhau xuất bản các báo cáo bền vững chi tiết, ghi lại tài liệu về quản lý môi trường, các sáng kiến trách nhiệm xã hội và cấu trúc quản trị của họ.

Bộ dữ liệu ViEn-ESG rút ra từ hai nguồn dữ liệu chính: các bài báo tin tức về ESG và các công bố thông tin bền vững chính thức của doanh nghiệp. Đối với nội dung các bài báo tin tức, chúng tôi đã thu thập một cách hệ thống các bài báo tập trung vào ESG được xuất bản từ ngày 1 tháng 1 năm 2015 đến ngày 14 tháng 8 năm 2024, tìm kiếm nội dung tiếng Anh từ trang ESGToday và các bài báo tiếng Việt từ các trang tin tức uy tín như VnExpress và Vietnam News. Để đảm bảo tính liên quan về mặt chủ đề, chúng tôi đã chọn các bài báo được gắn thẻ rõ ràng với từ khóa "ESG" hoặc được phân loại trong các phần liên quan đến ESG, đảm bảo rằng tất cả nội dung được thu thập đều trực tiếp giải quyết các chủ đề môi trường, xã hội hoặc quản trị.

Thành phần công bố thông tin của doanh nghiệp bao gồm một tập hợp các báo cáo bền vững từ các doanh nghiệp lớn của Việt Nam niêm yết trên Sở Giao dịch Chứng khoán Thành phố Hồ Chí Minh (HOSE) [@hose] và Sở Giao dịch Chứng khoán Hà Nội (HNX) [@hnx], cùng với các báo cáo tiếng Anh được thu thập từ các công ty thuộc chỉ số Standard and Poor's 500 (S&P 500) thuộc mười lĩnh vực kinh tế chính, bao gồm công nghệ, bán lẻ, hàng tiêu dùng, chăm sóc sức khỏe, ô tô, hàng không, điện tử, dịch vụ truyền thông, tài chính và công nghiệp nặng, với ngày xuất bản kéo dài từ năm 2012 đến năm 2024 nhằm nắm bắt các thực hành ESG và tiêu chuẩn báo cáo không ngừng phát triển trong hơn một thập kỷ.

### Tiền xử lý dữ liệu (Data Preprocessing)

Chúng tôi đã thu thập 348 báo cáo bền vững, trích xuất được 65.103 đoạn văn bản được tinh chọn. Với bộ dữ liệu tin tức, chúng tôi đã thu thập tổng cộng 68.553 câu, giúp bộ dữ liệu toàn diện đạt tới 130.798 mục nhập văn bản, cung cấp độ bao phủ rộng rãi cho truyền thông doanh nghiệp liên quan đến ESG trên nhiều định dạng và ngữ cảnh khác nhau. Các báo cáo bền vững được thu thập, chủ yếu phân phối dưới định dạng PDF, chứa nhiều nội dung phi cấu trúc. Chúng tôi quyết định chỉ giữ lại văn bản và loại bỏ các yếu tố bảng biểu và hình ảnh trực quan như biểu đồ hoặc sơ đồ. Tổng quan về sự phân bổ của các báo cáo bền vững theo danh mục và ngôn ngữ được minh họa trong Hình bên dưới, làm nổi bật tính đa dạng của các ngành và bản chất song ngữ của dữ liệu được thu thập.

[Hình ảnh của Biểu đồ phân bổ Báo cáo bền vững theo Danh mục và Ngôn ngữ (pdfbyctg.pdf)]

Trong bước tiền xử lý, chúng tôi đã sử dụng thư viện xử lý ngôn ngữ tự nhiên spaCy [@spacy] để thực hiện phân đoạn ở cấp độ câu đối với nội dung văn bản được trích xuất, cho phép gắn nhãn chính xác ở mức độ chi tiết của câu. Quy trình tiền xử lý tích hợp một số thủ tục chuẩn hóa dữ liệu bao gồm chuẩn hóa định dạng số, loại bỏ có hệ thống các ký tự và biểu tượng phi văn bản, và loại bỏ các câu trùng lặp. Các biện pháp hậu xử lý bao gồm một đợt rà soát thủ công toàn diện để xác định và sửa chữa các lỗi phân đoạn tự động, ranh giới câu không phù hợp và các đoạn nội dung quá ngắn hoặc quá dài, với các đoạn có vấn đề được sửa đổi thủ công thông qua phân đoạn thích hợp hoặc bị loại bỏ hoàn toàn khỏi bộ dữ liệu.

### Phương pháp luận gắn nhãn và Đảm bảo chất lượng (Annotation Methodology and Quality Assurance)

#### Gắn nhãn thủ công (Manual Labeling)

[Hình ảnh của Quy trình gán nhãn dữ liệu thủ công (data_pipeline.pdf)]

Việc phát triển hệ thống phân loại ESG của chúng tôi đòi hỏi phải thiết lập một nền tảng lý thuyết vững chắc dựa trên các tiêu chuẩn đánh giá ESG được quốc tế công nhận. Chúng tôi đã dựa vào các khung phương pháp luận được sử dụng bởi các tổ chức xếp hạng ESG toàn cầu nổi tiếng, chẳng hạn như Morgan Stanley Capital International (MSCI), Sustainalytics, và Dự án Tiết lộ Carbon (CDP). Quy trình gán nhãn được thể hiện trong Hình trên, một nhóm gồm bốn chuyên gia miền, mỗi người đều sở hữu kiến thức chuyên sâu về các phương pháp đánh giá ESG và quen thuộc với các tiêu chuẩn đánh giá của các tổ chức này, đã cùng nhau phát triển và tinh chỉnh các hướng dẫn gắn nhãn thông qua các quá trình thảo luận lặp đi lặp lại và xây dựng sự đồng thuận. Các quy tắc gán nhãn cho phân loại ESG được chi tiết hóa trong Bảng dưới đây. Trong Bảng tiếp theo, chúng tôi trình bày các quy tắc gán nhãn cho cảm xúc ESG.

**Các quy tắc gán nhãn cho bộ dữ liệu ViEn-ESG**

| Lớp        | Quy tắc                                                                                                                                                                                                                                                                                                                                                                          |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **E** | Các yếu tố môi trường bao gồm việc giảm thiểu các chất độc hại, quản lý thân thiện với môi trường, biến đổi khí hậu, phát thải carbon, tài nguyên thiên nhiên, ô nhiễm và chất thải, hiệu quả môi trường, sử dụng tài nguyên, đổi mới sản phẩm và tiết kiệm năng lượng.                                                |
| **S** | Các yếu tố xã hội bao gồm vốn con người, trách nhiệm sản phẩm, người lao động, môi trường làm việc, đối tác và đối thủ cạnh tranh, người tiêu dùng, đóng góp cho cộng đồng, quyền con người, giới tính và sự đa dạng, các tiêu chuẩn lao động, sự hài lòng của khách hàng, bảo vệ thông tin và quyền riêng tư. |
| **G** | Các yếu tố quản trị bao gồm hành vi của doanh nghiệp, quyền của cổ đông, hội đồng quản trị, các cơ quan kiểm toán, công bố thông tin, các bên liên quan, chiến lược CSR, cổ tức của ban điều hành, quản lý đạo đức, luật pháp và thuế.                                                                                            |
| **N** | Trung tính chứa thông tin ESG như một yếu tố trung hòa, bị loại trừ khỏi các danh mục môi trường, xã hội và quản trị, hoặc bao gồm hai danh mục trong cùng một câu, chẳng hạn như môi trường - xã hội, hoặc xã hội - quản trị.                                                                                                           |

**Các quy tắc gán nhãn cho bộ dữ liệu cảm xúc.**

| Lớp                    | Quy tắc                                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Môi trường** | Tích cực: Các thực hành bền vững, đổi mới xanh, năng lượng tái tạo, giảm phát thải carbon. |

Trung tính: Báo cáo mô tả hoặc thực tế mà không có giọng điệu đánh giá rõ ràng.

Tiêu cực: Các vi phạm môi trường, ô nhiễm, hoạt động không bền vững, nạn phá rừng. |
| **Xã hội** | Tích cực: Các sáng kiến cải thiện phúc lợi xã hội, sự công bằng, tính đa dạng, hỗ trợ cộng đồng.

Trung tính: Các mô tả khách quan hoặc báo cáo thông tin về các vấn đề xã hội.

Tiêu cực: Tranh chấp lao động, phân biệt đối xử, tác hại xã hội, vi phạm quyền con người. |
| **Quản trị** | Tích cực: Lãnh đạo mạnh mẽ, chính sách minh bạch, quản trị hiệu quả, tuân thủ các quy định.

Trung tính: Cập nhật thực tế về các thực hành quản trị mà không có cảm xúc rõ ràng.

Tiêu cực: Các vụ bê bối, tham nhũng, gian lận, thất bại trong quản trị, thiếu minh bạch. |

Để đảm bảo chất lượng và tính tin cậy cao nhất của các nhãn trong bộ dữ liệu, chúng tôi đã triển khai một phương pháp luận gán nhãn hai giai đoạn nghiêm ngặt liên quan đến bốn người gán nhãn, những người đã được đào tạo kỹ lưỡng về các hướng dẫn phân loại ESG và sở hữu kiến thức miền sâu rộng. Trong giai đoạn ban đầu, những người gán nhãn độc lập phân loại các câu thể hiện sự phân biệt danh mục rõ ràng, tập trung vào các ví dụ không mơ hồ vốn có thể dễ dàng gán cho các danh mục Môi trường, Xã hội, Quản trị hoặc Không phải ESG. Giai đoạn thứ hai liên quan đến các phiên thảo luận cộng tác, nơi những người gán nhãn tham gia vào các cuộc thảo luận có cấu trúc để giải quyết các trường hợp thách thức xuất hiện sự mơ hồ trong phân loại hoặc các đặc điểm chồng chéo giữa nhiều khía cạnh ESG. Để duy trì các tiêu chuẩn kiểm soát chất lượng nghiêm ngặt, chúng tôi đã thiết lập một khung ra quyết định dựa trên sự đồng thuận, theo đó các câu chỉ được đưa vào bộ dữ liệu cuối cùng khi tất cả bốn người gán nhãn đạt được sự đồng thuận nhất trí, từ đó đảm bảo độ tin cậy liên người gán nhãn (inter-annotator reliability) mạnh mẽ đồng thời giảm thiểu định kiến chủ quan.

**Hệ số Kappa của Cohen đo lường mức độ đồng thuận giữa những người gán nhãn trên các danh mục ESG và các ngôn ngữ trong bộ dữ liệu ViEn-ESG.**

| Danh mục          | Tiếng Anh      | Tiếng Việt    | Tất cả        |
| ------------------ | --------------- | --------------- | --------------- |
| Môi trường      | 0.987           | 0.979           | 0.983           |
| Xã hội           | 0.984           | 0.982           | 0.983           |
| Quản trị         | 0.990           | 0.989           | 0.989           |
| Trung tính        | 0.984           | 0.974           | 0.979           |
| **Tất cả** | **0.986** | **0.981** | **0.984** |

Các trường hợp khác đã bị loại bỏ một cách hệ thống khỏi bộ dữ liệu để bảo vệ chất lượng gắn nhãn, dẫn đến việc loại bỏ ít hơn 0,2% tổng số câu do sự bất đồng quan điểm kéo dài giữa những người gán nhãn. Sự đồng thuận giữa những người gán nhãn của chúng tôi đã được đánh giá định lượng bằng hệ số kappa của Cohen [@Cohen1960], hệ số này chứng minh mức độ đồng thuận đặc biệt cao trên tất cả các danh mục và ngôn ngữ, với điểm số dao động từ 0,974 đến 0,990 như được chi tiết trong Bảng trên, chỉ ra mức độ đồng thuận gần như hoàn hảo theo các hướng dẫn diễn giải đã được thiết lập và xác thực tính nhất quán cũng như độ tin cậy của quy trình gắn nhãn của chúng tôi.

**Mẫu dữ liệu được gắn nhãn trong bộ dữ liệu ViEn-ESG.**

| Lớp        | Câu mẫu                                                                                                                                                                                                                                  |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **E** | Trữ lượng dầu, khí đốt và than đá đã biết có thể được khai thác trong vài thập kỷ tới, theo cách hiệu quả về chi phí bằng cách sử dụng các công nghệ hiện tại, ở mức giá năng lượng hiện tại. |

Hệ quả phát triển tốt đáng chú ý này làm giảm 25% chất thải từ các quy trình API fermion.

Phát thải khí nhà kính đã giảm để đáp ứng mục tiêu giảm thiểu (thấp hơn 15% so với mức của năm tài chính 2013). |
| **S** | Các nền kinh tế cần lực lượng lao động được giáo dục và có kỹ năng để đảm bảo sức khỏe kinh tế của họ.

Một trong những trọng tâm của Servicio País là khôi phục các không gian công cộng gần các trường học và khu dân cư nhằm cải thiện chất lượng cuộc sống của người dân.

Hơn nữa, các cơ hội chăm sóc sức khỏe tại chỗ cho nhân viên được bao gồm trong chương trình này, bao gồm quyền tiếp cận máy đo huyết áp, xe chụp X-quang tuyến vú di động, hiến máu, phòng tiêm chủng cúm, sàng lọc sinh trắc học và một chuyến thăm khám tại chỗ hàng năm từ bác sĩ chăm sóc sức khỏe. |
| **G** | Ban quản lý cấp cao rà soát các kết quả của hệ thống gắn kết hàng năm.

Ủy ban Kiểm toán cung cấp sự giám sát đối với báo cáo tài chính và rủi rò pháp lý.

Hệ thống kiểm soát kế toán nội bộ được hỗ trợ bởi các chính sách và hướng dẫn bằng văn bản, việc lựa chọn và đào tạo các nhân viên có trình độ, một cấu trúc tổ chức cung cấp sự phân chia trách nhiệm thích hợp và một chương trình kiểm toán nội bộ. |
| **N** | Về Evercomm: Evercomm là một công ty phần mềm hỗ trợ các doanh nghiệp tiến tới phát thải ròng bằng không (net zero).

Tính đến ngày nộp hồ sơ này, chúng tôi không nhận thấy bất kỳ vấn đề nào bắt buộc phải công bố theo tiêu chuẩn này.

Một sự gia tăng của $ do sự leo thang giá cả trên toàn ngành và tăng lương theo tiến trình thông thường cho nhân sự quản lý tài sản tại chỗ. |

Lịch trình gán nhãn của bốn người gán nhãn bao gồm các phiên làm việc hai giờ hàng ngày được tiến hành năm ngày mỗi tuần, với việc những người gán nhãn đạt được tốc độ năng suất từ 600-700 câu mỗi giờ, chuyển dịch thành khoảng 7.000 câu được gắn nhãn trên mỗi người gán nhãn mỗi tuần. Toàn bộ dòng thời gian gắn nhãn kéo dài khoảng 3-4 tháng, với giai đoạn ba tháng đầu tiên được dành riêng để xử lý các câu có thể phân loại rõ ràng, tiếp theo là một tháng bổ sung của giai đoạn chuyên sâu tập trung vào thảo luận cộng tác và giải quyết các trường hợp thách thức, đảm bảo độ bao phủ kỹ lưỡng và sự chú ý tỉ mỉ đến chất lượng trong suốt toàn bộ quy trình xây dựng bộ dữ liệu.

Phương pháp luận gắn nhãn thủ công nghiêm ngặt này, vốn phản chiếu các thực hành tốt nhất được thiết lập trong các nghiên cứu tạo bộ dữ liệu chuyên biệt theo miền khác, đảm bảo dữ liệu giám sát chất lượng cao phản ánh chính xác các nguyên tắc ESG và các sắc thái ngôn ngữ trên cả bối cảnh tiếng Anh và tiếng Việt, cuối cùng cung cấp một nền tảng vững chắc để huấn luyện các mô hình phân loại ESG mạnh mẽ và đáng tin cậy, với các ví dụ đại diện cho các câu từ mỗi lớp trong bộ dữ liệu ViEn-ESG được trình bày trong Bảng trên. Trong Bảng dưới đây, chúng tôi trình bày sự phân bổ theo từng lớp của bộ dữ liệu ViEn-ESG.

**Phân bổ theo từng lớp của Bộ dữ liệu ViEn-ESG.**

| Lớp dữ liệu          | Tiếng Anh       | Tiếng Việt     | Tổng số         |
| ----------------------- | ---------------- | ---------------- | ----------------- |
| **Môi trường** | 10.517           | 19.080           | 29.597            |
| **Xã hội**      | 11.112           | 25.201           | 36.313            |
| **Quản trị**    | 9.103            | 18.046           | 27.149            |
| **Trung tính**   | 15.210           | 22.529           | 37.739            |
| **Tổng số**     | **45.942** | **84.856** | **130.798** |

#### Gắn nhãn giả để làm phong phú dữ liệu (Pseudo-labeling for Data Enrichment)

Chúng tôi cũng áp dụng kỹ thuật gắn nhãn giả (pseudo-labeling) để làm phong phú dữ liệu. Mô hình ban đầu được huấn luyện trên dữ liệu được gắn nhãn đã được sử dụng để tạo ra các dự đoán xác suất cho một kho ngữ liệu bên ngoài gồm các văn bản chưa được gắn nhãn. Chỉ những mẫu dữ liệu mà mô hình gán xác suất lớp cao nhất vượt quá một ngưỡng tin cậy được xác định trước là 0,94 mới được giữ lại. Đối với mỗi văn bản được giữ lại, các nhãn giả được gán cho các lớp tương ứng dựa trên các điểm số tin cậy này. Quy trình này tùy chọn áp dụng một lược đồ lặp đi lặp lại, điều chỉnh dần ngưỡng qua nhiều vòng để tối đa hóa cả số lượng và chất lượng của các mẫu được gắn nhãn tự động.

Dữ liệu được gắn nhãn giả thu được sau đó được kết hợp với tập huấn luyện gốc. Mô hình sau đó được tái huấn luyện trên bộ dữ liệu hỗn hợp này, tận dụng cả các mẫu do con người gán nhãn và các mẫu được máy gắn nhãn có độ tin cậy cao.

Trong các phương pháp gắn nhãn giả truyền thống, việc sử dụng một mô hình duy nhất để dự đoán nhãn cho dữ liệu chưa được gắn nhãn thường mang lại những rủi ro đáng kể. Cụ thể, nếu mô hình có độ chệch (bias) cao hoặc bị quá khớp trên tập huấn luyện ban đầu, các nhãn giả được tạo ra có thể chứa các lỗi hệ thống. Các lỗi này có thể tích tụ khi dữ liệu bị gắn nhãn sai được đưa ngược trở lại tập huấn luyện, dẫn đến một hiện tượng được gọi là định kiến xác nhận (confirmation bias) — nơi mô hình ngày càng củng cố các dự đoán sai lầm của chính nó.

[Hình ảnh sơ đồ Hệ hợp lực BERT cho các Nhãn giả Đáng tin cậy (pseudo_labeling.png)]

Để giảm thiểu các vấn đề do gắn nhãn giả, chúng tôi đề xuất một phương pháp tích hợp học máy đồng thể (ensemble learning) vào quy trình gắn nhãn giả. Phương pháp tiếp cận gắn nhãn bán giám sát này tận dụng một hệ hợp lực gồm nhiều mô hình BERT. Đầu tiên, dữ liệu huấn luyện được gắn nhãn được sử dụng để huấn luyện K mô hình BERT độc lập, mỗi mô hình được huấn luyện trên một tập con khác nhau của dữ liệu gốc. Sau khi quy trình huấn luyện hoàn tất, tất cả các mô hình BERT này đồng thời dự đoán nhãn cho dữ liệu chưa được gắn nhãn. Các nhãn dự đoán từ các mô hình này sau đó được tổng hợp bằng cơ chế bỏ phiếu (voting mechanism), nơi các nhãn có độ tin cậy cao nhất được lựa chọn làm nhãn giả. Cụ thể, các nhãn nhận được sự đồng thuận cao giữa các mô hình sẽ được ưu tiên. Cuối cùng, dữ liệu với các nhãn giả này được thêm ngược trở lại vào tập huấn luyện, từ đó cải thiện chất lượng của mô hình bằng cách sử dụng hiệu quả cả dữ liệu đã gắn nhãn và chưa gắn nhãn. Từ tập dữ liệu huấn luyện gốc gồm 27.366 câu, chúng tôi đã tạo thêm 14.634 câu bằng cách sử dụng dữ liệu chưa được gắn nhãn thông qua kỹ thuật gắn nhãn giả. Phương pháp tiếp cận này tận dụng sức mạnh của các mô hình BERT để giảm thiểu rủi ro gắn nhãn sai, giảm định kiến xác nhận và nâng cao tính ổn định của tập nhãn được mở rộng.

Các mô hình được lựa chọn bao gồm cả các transformer đa ngôn ngữ và các transformer được tối ưu hóa cho tiếng Việt: DistilBERT-base-multilingual, ViSoBERT, Vi-Electra, BERT-base-multilingual, PhoBERT, ViDeBERTa, RoBERTa-base. Mỗi vòng lặp huấn luyện sử dụng dữ liệu giả được tạo ra từ vòng trước đó để bổ sung cho bộ dữ liệu huấn luyện gốc, tạo ra một quy trình cải tiến lặp đi lặp lại.

**1) Vòng lặp đầu tiên (First Iteration):** Trong vòng lặp đầu tiên, các mô hình được huấn luyện trên tập con dữ liệu gồm 7 phần của dữ liệu gốc và chứng minh hiệu suất cơ sở đầy hứa hẹn. DistilBERT-base-multilingual đạt hiệu suất cao nhất với độ chính xác 87,36%, tiếp theo là ViSoBERT ở mức 87,23% và Vi-Electra ở mức 86,86%.

Vòng lặp đầu tiên đã tạo ra một lượng dữ liệu giả đáng kể với 8.830 mẫu cho lớp Môi trường, 7.667 cho Xã hội, 6.300 cho Quản trị, và 2.974 cho các lớp Không liên quan. Để đảm bảo tính cân bằng của bộ dữ liệu, chúng tôi đã điều chỉnh số lượng dữ liệu giả được sử dụng, dẫn đến tổng số 37.636 mẫu cho vòng lặp tiếp theo với sự phân bổ như sau: Không liên quan (tổng số 8.877: 5.903 gốc + 2.974 giả), Môi trường (tổng số 9.009: 4.384 gốc + 4.625 giả), Xã hội (tổng số 10.726: 10.026 gốc + 700 giả), và Quản trị (tổng số 9.024: 7.053 gốc + 1.971 giả).

**2) Vòng lặp thứ hai (Second Iteration):** Vòng lặp thứ hai cho thấy những cải thiện hiệu suất đáng kể trên tất cả các mô hình. Vi-Electra đạt hiệu suất tổng thể tốt nhất với độ chính xác 92,13%, đi kèm với điểm số F1 ấn tượng trên tất cả các lớp. ViSoBERT và ViDeBERTa cũng chứng minh hiệu suất mạnh mẽ với độ chính xác lần lượt là 91,33% and 91,13%.

Vòng lặp thứ hai đã tạo ra 8.255 mẫu dữ liệu giả mới, với Môi trường đóng góp 4.212 mẫu, Xã hội đóng góp 1.915 mẫu, Quản trị đóng góp 1.548 mẫu, và Không liên quan đóng góp 580 mẫu. Sau khi cân bằng dữ liệu, tổng số lượng mẫu cho vòng lặp cuối cùng đạt tới 42.000 mẫu với sự phân bổ như sau: Không liên quan (tổng số 11.077: 8.877 trước đó + 2.200 giả), Môi trường (tổng số 10.009: 9.009 trước đó + 1.000 giả), Xã hội (tổng số 11.310: 10.726 trước đó + 584 giả), và Quản trị (tổng số 9.604: 9.024 trước đó + 580 giả).

[Hình ảnh đồ thị Phân bổ dữ liệu theo từng vòng lặp gắn nhãn giả (final_distribution_train.pdf)]

**3) Vòng lặp thứ ba (Third Iteration):** Vòng lặp cuối cùng đánh dấu đỉnh cao hiệu suất của nghiên cứu của chúng tôi. Vi-Electra tiếp tục dẫn đầu với độ chính xác 94,66%, tiếp theo là BERT-base-multilingual ở mức 94,36% và ViSoBERT ở mức 93.83%. Đáng chú ý, tất cả các mô hình đều đạt độ chính xác trên 91%, chứng minh tính ổn định và hiệu quả của phương pháp luận gắn nhãn giả.

[Hình ảnh đồ thị Kết quả huấn luyện sau mỗi giai đoạn gắn nhãn giả (pseudo-result.pdf)]

Các kết quả nghiên cứu chứng minh một xu hướng cải tiến nhất quán qua các vòng lặp gắn nhãn giả. Độ chính xác trung bình của các mô hình đã tăng từ 85,75% ở vòng lặp đầu tiên lên 90,82% ở vòng lặp thứ hai, đạt đỉnh 93,47% ở vòng lặp cuối cùng. Đặc biệt, Vi-Electra cho thấy sự vượt trội nhất quán qua cả ba vòng lặp, cho thấy khả năng thích ứng xuất sắc với dữ liệu văn bản tiếng Việt.

Lớp Môi trường nhất quán đạt điểm số F1 cao nhất trên tất cả các mô hình, trong khi lớp Không liên quan đặt ra nhiều thách thức phân loại nhất. Điều này có thể được giải thích là do bản chất đa dạng và mơ hồ của lớp Không liên quan so với các lớp chuyên biệt theo miền cụ thể hơn.
Phương pháp tiếp cận gắn nhãn giả đã chứng minh tính hiệu quả đặc biệt trong việc làm phong phú dữ liệu và giải quyết các vấn đề mất cân bằng lớp. Bằng cách lựa chọn chiến lược các mẫu được gắn nhãn giả, chúng tôi đã có thể duy trì sự phân bổ lớp tốt hơn trong khi tăng dần kích thước bộ dữ liệu, đóng góp vào các cải thiện hiệu suất được quan sát.

#### Gắn nhãn thông qua Dịch máy (Annotation through Machine Translation)

Để mở rộng độ bao phủ của bộ dữ liệu tiếng Việt của chúng tôi, chúng tôi đã áp dụng một chiến lược gắn nhãn dựa trên dịch thuật nhằm tận dụng dữ liệu tiếng Anh chất lượng cao sẵn có. Cụ thể, chúng tôi đã chọn 10.000 câu tiếng Anh đã được gắn nhãn theo tiêu chuẩn vàng (gold-standard). Các câu này sau đó được dịch sang tiếng Việt bằng mô hình `erax-ai/EraX-Translator-V1.0` [@erax], một hệ thống dịch mã máy nơ-ron đã được chứng minh là đạt hiệu suất mạnh mẽ trong các tác vụ dịch thuật Anh-Việt. Bằng cách bảo tồn cấu trúc ngữ nghĩa của các câu gốc, phương pháp tiếp cận này cho phép chúng tôi kế thừa các nhãn tiếng Anh và trực tiếp gán chúng cho các bản dịch tiếng Việt tương ứng.

Lợi thế chính của phương pháp này là nó cho phép tạo ra dữ liệu được gắn nhãn một cách nhanh chóng và tiết kiệm chi phí trong bối cảnh ngôn ngữ ít tài nguyên, mà không cần đến việc gắn nhãn thủ công trên diện rộng. Hơn nữa, bởi vì các nhãn được bắt nguồn từ các câu tiếng Anh tương đương về mặt ngữ nghĩa, quy trình này đảm bảo tính liên kết giữa các ngôn ngữ và tạo điều kiện thuận lợi cho việc phát triển các điểm chuẩn xuyên ngôn ngữ (cross-lingual benchmarks). Để giảm thiểu rủi ro lỗi dịch thuật, chúng tôi đã áp dụng quy trình xác thực hậu dịch thuật bằng cách lấy mẫu một tập con của các đầu ra tiếng Việt và xác minh xem câu được dịch có bảo tồn ý nghĩa gốc và tính nhất quán của nhãn hay không. Trong thực tế, chúng tôi quan sát thấy rằng việc bảo tồn nhãn duy trì được mức độ tin cậy đối với các câu có cấu trúc tốt, mặc dù một số nhiễu nhỏ có thể xảy ra do các diễn đạt thành ngữ hoặc thuật ngữ chuyên ngành.

Bất chấp những hạn chế này, việc gắn nhãn dựa trên dịch thuật phục vụ như một giải pháp trung gian hiệu quả giữa gắn nhãn thủ công và gắn nhãn giả. Nó cung cấp một cơ chế có thể mở rộng để làm phong phú bộ dữ liệu với các ví dụ tiếng Việt đa dạng trong khi duy trì độ trung thực ngữ nghĩa đối với dữ liệu tiếng Anh gốc. Tài nguyên song ngữ thu được không chỉ củng cố tính mạnh mẽ của quá trình huấn luyện mô hình của chúng tôi mà còn đóng góp vào mục tiêu dài hạn là xây dựng các bộ dữ liệu ESG toàn diện hơn nhằm hỗ trợ các ứng dụng đa ngôn ngữ. Gợi ý (prompt) chi tiết được sử dụng để hướng dẫn quy trình dịch thuật được cung cấp trong Phụ lục TRANSLATE_PROMPT.

---

## Thực nghiệm và Phân tích (Experiments and Analysis)

Phần này chi tiết hóa thiết kế thực nghiệm và các kết quả của mô hình phân loại ESG được đề xuất của chúng tôi. Chúng tôi phác thảo các thiết lập triển khai, bao gồm các thông số kỹ thuật phần cứng, cấu hình huấn luyện và các giao thức đánh giá. Sau đó, chúng tôi trình bày một phân tích hiệu suất toàn diện trên cả hai tập con tiếng Anh và tiếng Việt của bộ dữ liệu ViEn-ESG, cùng với một đánh giá về các mô hình song ngữ và cơ chế tính điểm ESG.

### Thiết lập thực nghiệm và Chi tiết triển khai (Experimental Setup and Implementation Details)

Để giải quyết một cách toàn diện tác vụ phân loại ESG, chúng tôi đã áp dụng một chiến lược mô hình hóa đa chiều, huấn luyện bốn loại bộ phân loại riêng biệt dựa trên kiến trúc BERT được tinh chỉnh. Ba bộ phân loại nhị phân đã được phát triển, mỗi bộ chuyên trách xác định mức độ liên quan của một câu đối với một trụ cột ESG cụ thể: Môi trường (E), Xã hội (S), hoặc Quản trị (G). Phương pháp tiếp cận nhị phân này cho phép đánh giá tập trung trong từng khía cạnh và phù hợp với các phương pháp luận được sử dụng trong các tài liệu nghiên cứu trước đây nhằm xác định mức độ liên quan hoặc tác động. Bổ sung cho chúng, chúng tôi đã phát triển một bộ phân loại đa lớp, được gọi là ViBERT-ESG (và các biến thể của nó dựa trên các mạng xương sống khác), được thiết kế để phân loại một câu vào một trong bốn lớp loại trừ lẫn nhau: E, S, G, hoặc Trung tính (N). Lớp Trung tính phục vụ như một danh mục tổng hợp quan trọng cho các câu không liên quan đến ESG hoặc có khả năng trải dài trên nhiều khía cạnh một cách mơ hồ. Mô hình bốn lớp này cung cấp một phân loại tổng thể trên các trụ cột ESG chính.

**1) Chi tiết triển khai (Implementation Details):** Các thực nghiệm được tiến hành với các thông số kỹ thuật sau. Đối với tất cả các công việc, các tác vụ huấn luyện, kiểm thử và đánh giá mô hình được thực hiện trên bộ xử lý Intel Core i7–13700, 48 GB RAM và 2 GPU RTX 3060. Bộ dữ liệu được chia thành 70% dữ liệu huấn luyện, 15% dữ liệu kiểm định và 15% dữ liệu kiểm thử. Các siêu tham số chính được giữ nhất quán giữa các mô hình để đảm bảo so sánh công bằng, dựa trên các thực hành phổ biến cho việc tinh chỉnh các mô hình dạng BERT. Quy trình huấn luyện sử dụng tinh chỉnh toàn bộ tham số (full-parameter fine-tuning) với tối ưu hóa DeepSpeed ZeRO-3 [@deepspeed-zero3]. Tất cả các mô hình được huấn luyện với độ chính xác BFloat16 trong 3000 bước, bao gồm 200 bước khởi động (warm-up steps). Chúng tôi sử dụng tốc độ học là $5 \times 10^{-5}$ với lịch trình tốc độ học cosin (cosine learning rate scheduling), suy giảm trọng số (weight decay) là 0,01, kích thước lô là 48 và định mức chuẩn gradient tối đa (maximum gradient norm) là 2,5. Bộ tối ưu hóa là AdamW [@adamw], và độ dài chuỗi đầu vào tối đa được đặt thành 512 token. Để đảm bảo tính tái lập, chúng tôi đặt hạt giống ngẫu nhiên (random seed) thành 42 trong tất cả các thực nghiệm.

**2) Chỉ số đánh giá (Evaluation Metrics):** Trong thiết lập thực nghiệm của chúng tôi, chúng tôi chủ yếu báo cáo điểm số F1 trung bình macro ($F1_{\text{macro}}$) vì nó cung cấp một góc nhìn cân bằng về hiệu suất trên các lớp có tần suất khác nhau. Chúng tôi cũng bao gồm độ chính xác tổng thể như một chỉ số bổ sung để nắm bắt tính chính xác chung của dự đoán. Sự kết hợp này đảm bảo rằng cả tính cân bằng ở cấp độ lớp và hiệu suất phân loại tổng thể đều được đánh giá đúng đắn.

$$
F1_{\text{macro}} = \frac{\sum_{i=0}^{N} F1_i}{N}
$$

Trong đó $F1_i$ biểu thị điểm số F1 của lớp $i$, và $N$ là tổng số lớp. Chúng tôi báo cáo macro-F1 như chỉ số chính vì nó tính trọng số bình đẳng cho tất cả các lớp, làm cho nó đặc biệt phù hợp cho các bộ dữ liệu ESG mất cân bằng. Ngoài ra, chúng tôi cũng cung cấp độ chính xác tổng thể để đưa ra cái nhìn toàn diện hơn về hiệu suất mô hình.

### Hiệu suất trên Phân loại ESG Tiếng Việt (Performance on Vietnamese ESG Classification)

Chúng tôi đã áp dụng phương pháp tinh chỉnh cho mô hình bằng cách sử dụng các cặp câu và nhãn ESG, tận dụng một mô hình ngôn ngữ tiền huấn luyện. Trong thực nghiệm, chúng tôi đã sử dụng các mô hình BERT đa ngôn ngữ, phiên bản đa ngôn ngữ của BERT, và các mô hình tiếng Việt như PhoBert-Base, PhoBert-Large, viBert, viELECTRA, và ViSoBERT.

Các kết quả của phân loại đa lớp cho các câu liên quan đến ESG với 4 nhãn trong bộ dữ liệu ESG được trình bày trong Bảng dưới đây. Trong thực nghiệm, mỗi mô hình được huấn luyện 5 lần, và độ chính xác trung bình cùng độ chính xác cho từng lớp được tính toán bằng cách loại bỏ các giá trị độ chính xác cao nhất và thấp nhất.

**So sánh các mô hình dựa trên Transformer cho ngôn ngữ tiếng Việt**

| Mô hình                         | Độ chính xác tổng thể | F1 Môi trường (Env) | F1 Quản trị (Gov) | F1 Xã hội (Soc) | F1 Trung tính (Neu) |
| --------------------------------- | --------------------------- | ---------------------- | ------------------- | ----------------- | -------------------- |
| **viDEBERTA**               | 93.1                        | 96.21                  | 91.13               | 91.15             | 89.20                |
| **viELECTRA**               | **94.66**             | **98.30**        | **93.13**     | **94.36**   | **92.09**      |
| **PhoBERT-Base**            | 93.7                        | 96.50                  | 92.01               | 92.51             | 90.15                |
| **ViSoBERT**                | 93.83                       | 97.12                  | 92.23               | 93.11             | 91.02                |
| **BERT-Base-Multilingual**  | 94.36                       | 97.45                  | 92.89               | 93.81             | 91.80                |
| **RoBERTa**                 | 91.8                        | 94.21                  | 89.12               | 90.03             | 86.79                |
| **DistilBERT-Multilingual** | 93.86                       | 97.02                  | 92.15               | 93.06             | 91.11                |

Phân tích so sánh các mô hình dựa trên Transformer cho xử lý ngôn ngữ tiếng Việt cho thấy viELECTRA là mô hình đạt hiệu suất cao nhất, đạt được các kết quả vượt trội trên tất cả các chỉ số đánh giá. Với độ chính xác tổng thể là 94,66%, viELECTRA chứng minh hiệu suất đặc biệt trong tất cả các danh mục phân loại: Môi trường (98,30% F1), Quản trị (93,13% F1), Xã hội (94,36% F1), và Không liên quan/Trung tính (92,09% F1). Trong khi các mô hình khác cho thấy kết quả cạnh tranh — ViSoBERT (93,83%) và DistilBERT-Multilingual (93,86%) — không có mô hình nào vượt qua được hiệu suất cân bằng của PhoBERT-Base (độ chính xác 93,7%). Đánh giá cũng làm nổi bật hiệu suất tương đối yếu hơn của viDEBERTA (93,1%) và hiệu suất tốt của BERT-Base-Multilingual (94,36%), trong khi RoBERTa cho thấy độ chính xác tổng thể thấp nhất (91,8%), đặc biệt gặp khó khăn với việc phân loại nội dung Không liên quan (86,79% F1). Những phát hiện này thiết lập viELECTRA là mô hình mạnh mẽ nhất cho các tác vụ xử lý ngôn ngữ tiếng Việt, đặc biệt là đối với phân loại văn bản ESG có nhiều sắc thái. viELECTRA là lựa chọn tối ưu để phân loại thông tin ESG bằng tiếng Việt, với hiệu suất vượt trội trên các danh mục phân loại chính.

### Hiệu suất trên Phân loại ESG Song ngữ (Performance on Bilingual ESG Classification)

Đối với phần tiếng Anh của bộ dữ liệu, chúng tôi đã đánh giá điểm chuẩn của một số mô hình ESG công khai có sẵn, bao gồm `FinBERT-ESG`, `SEC-BERT-ft`, `ESGify`, và ba mô hình phân loại nhị phân. Các mô hình này khác nhau về độ chi tiết của nhãn: `FinBERT-ESG` dự đoán 9 danh mục liên quan đến ESG, `SEC-BERT-ft` hỗ trợ 33 loại vấn đề chi tiết, và `ESGify` xử lý 47 nhãn. Để cho phép so sánh nhất quán, chúng tôi đã ánh xạ tất cả các nhãn dự đoán thành một định dạng 4 lớp thống nhất E/S/G/N.

[Hình ảnh biểu đồ Hàm mất mát huấn luyện của các kết quả phân loại ESG trên bộ dữ liệu song ngữ. (loss_bert-base-multilingual-cased.pdf)]

**Điểm số F1 của các mô hình trên từng danh mục ESG trong bộ dữ liệu ViEn-ESG tiếng Anh.**

| Mô hình                        | Số tham số | Env             | Soc             | Gov             | Neu             | Tổng thể      |
| -------------------------------- | ------------ | --------------- | --------------- | --------------- | --------------- | --------------- |
| {SEC-BERT-ft}                    | 109M         | 83.12           | 66.77           | 66.53           | 60.30           | 68.12           |
| {FinBERT-ESG}                    | 109M         | 92.67           | 84.90           | 86.25           | 87.26           | 87.51           |
| {FinBERT-ESG-9-class}            | 109M         | 92.16           | 89.01           | 91.35           | 86.89           | 89.80           |
| {ESGify}                         | 109M         | 67.72           | 30.20           | 50.76           | 43.44           | 48.33           |
| {EnvironmentBERT}                | 82M          | 92.15           | -               | -               | 92.76           | -               |
| {SocialBERT}                     | 82M          | -               | 76.81           | -               | 81.23           | -               |
| {GovernanceBERT}                 | 82M          | -               | -               | 64.46           | 80.06           | -               |
| {BERT-base-multilingual-cased}   | 168M         | 93.76           | 94.53           | 94.98           | **94.15** | 94.75           |
| {BERT-base-multilingual-uncased} | 168M         | 94.62           | 93.81           | 94.26           | 92.13           | 93.83           |
| {RoBERTa-base}                   | 124M         | 95.43           | 94.06           | 95.01           | 91.32           | 94.11           |
| {XLMRoBERTa-base}                | 278M         | 95.00           | 95.00           | **95.47** | 92.19           | **94.83** |
| {DeBERTa-base}                   | 184M         | **95.50** | 94.49           | 94.81           | 91.48           | 94.70           |
| {DeBERTa-small}                  | 141M         | 94.55           | 94.85           | 94.58           | 90.19           | 93.72           |
| {DistilBERT-multilingual-cased}  | 135M         | 95.15           | **95.19** | 94.33           | 91.75           | 94.60           |
| {FinBERT}                        | 109M         | 94.62           | 93.16           | 94.10           | 92.13           | 93.50           |

Bởi vì các mô hình ESG hiện tại chủ yếu được thiết kế cho tiếng Anh và không hỗ trợ đầu vào tiếng Việt, các mô hình của chúng tôi được tinh chỉnh đồng thời trên cả các mẫu tiếng Anh và tiếng Việt từ bộ dữ liệu ViEn-ESG. Thiết lập huấn luyện song ngữ này cho phép các mô hình tổng quát hóa tốt hơn giữa các ngôn ngữ và hưởng lợi từ không gian ngữ cảnh chung của các khái niệm liên quan đến ESG. Chúng tôi đánh giá các mô hình đã tinh chỉnh của mình trên cả hai tập kiểm thử tiếng Anh và tiếng Việt.

Bảng trên tóm tắt hiệu suất của các mô hình ESG dựa trên tiếng Anh hiện tại cùng với các mô hình tinh chỉnh song ngữ của chúng tôi trên phần tiếng Anh của bộ dữ liệu ViEn-ESG. Trong số các mô hình cơ sở, `FinBERT-ESG` và biến thể 9 lớp của nó thể hiện hiệu suất mạnh mẽ, với điểm số F1 tổng thể lần lượt là 87,51% và 89,80%, phản ánh quá trình tiền huấn luyện chuyên biệt theo miền trên văn bản tài chính. Tuy nhiên, các mô hình như `SEC-BERT-ft` và `ESGify` cho thấy điểm số thấp hơn đáng kể (lần lượt là 68,12% và 48,33%), chỉ ra rằng các sơ đồ phân loại chi tiết hoặc độ mịn nhãn quá mức có thể làm giảm hiệu quả khi các nhãn được ánh xạ vào một định dạng 4 lớp thống nhất (E/S/G/N). Tương tự, các mô hình nhị phân (`EnvironmentBERT`, `SocialBERT`, và `GovernanceBERT`) hoạt động tốt trên các miền tương ứng của chúng nhưng thiếu độ bao phủ toàn diện trên tất cả các danh mục ESG.

Ngược lại, các mô hình tinh chỉnh song ngữ của chúng tôi nhất quán vượt trội so với các mô hình cơ sở hiện tại trên tất cả các khía cạnh ESG. Đáng chú ý, `XLMRoBERTa-ESG-base` đạt điểm số F1 tổng thể cao nhất (94,83%), bám sát ngay sau là `DeBERTa-ESG-base` (94,70%) và `BERT-multilingual-cased-ESG` (94,75%). Những kết quả này khẳng định các lợi thế của việc tận dụng kiến trúc đa ngôn ngữ và tinh chỉnh song ngữ đồng thời, giúp tăng cường khả năng tổng quát hóa và giảm thiểu sự dịch chuyển miền giữa dữ liệu tiếng Anh và tiếng Việt. Thú vị là, trong khi `DeBERTa-ESG-base` vượt trội hơn một chút so với các mô hình khác ở danh mục Môi trường (95,50%), `DistilBERT-multilingual-cased-ESG` đạt điểm số tốt nhất ở danh mục Xã hội (95,19%), gợi ý rằng một số kiến trúc nhất định có thể nắm bắt các khía cạnh ESG khác nhau một cách hiệu quả hơn.

**Điểm số F1 của các mô hình trên từng danh mục ESG trong bộ dữ liệu ViEn-ESG tiếng Việt.**

| Mô hình                        | Số tham số | Env             | Soc             | Gov             | Neu             | Tổng thể      |
| -------------------------------- | ------------ | --------------- | --------------- | --------------- | --------------- | --------------- |
| {BERT-base-multilingual-cased}   | 168M         | 93.50           | 89.73           | 91.77           | **91.78** | 91.80           |
| {BERT-base-multilingual-uncased} | 168M         | 80.18           | 58.36           | 68.66           | 57.44           | 66.54           |
| {RoBERTa}                        | 124M         | 93.41           | 91.49           | 89.93           | 84.32           | 89.96           |
| {XLMRoBERTa}                     | 278M         | 93.45           | 91.02           | 91.69           | 90.41           | **91.94** |
| {DeBERTa-base}                   | 184M         | **95.24** | 89.36           | **93.18** | 85.23           | 90.89           |
| {DeBERTa-small}                  | 141M         | 92.90           | 87.79           | 90.63           | 81.48           | 88.70           |
| {DistilBERT-multilingual-cased}  | 135M         | 93.87           | **91.98** | 90.63           | 87.17           | 91.02           |
| {FinBERT}                        | 109M         | 75.28           | 54.02           | 68.21           | 56.91           | 63.70           |

Chuyển sang các kết quả tiếng Việt trong Bảng trên, chúng tôi quan sát thấy một sự sụt giảm hiệu suất nhẹ so với tiếng Anh, điều này đã được dự đoán trước do tính sẵn có thấp hơn của các tài nguyên tiền huấn luyện cho tiếng Việt. Tuy nhiên, tất cả các mô hình song ngữ đều duy trì điểm số F1 tổng thể cao trên 88%, chứng minh khả năng chuyển giao xuyên ngôn ngữ mạnh mẽ. `BERT-base-multilingual-cased` và `XLMRoBERTa` đạt điểm số tổng thể cao nhất (lần lượt là 91,80% và 91,94%), xác nhận năng lực đa ngôn ngữ mạnh mẽ của chúng. `DeBERTa-base` cho thấy hiệu suất vượt trội trên các danh mục Môi trường (95,24%) và Quản trị (93,18%), trong khi `DistilBERT-multilingual-cased` xuất sắc ở danh mục Xã hội (91,98%), một lần nữa làm nổi bật sự biến động về thế mạnh của mạng xương sống trên các khía cạnh ESG khác nhau. Chúng tôi ghi nhận một sự sụt giảm hiệu suất đáng kể ở các mô hình `BERT-base-multilingual-uncased` và `FinBERT` vốn sẽ được thảo luận trong phần tiếp theo.

Nhìn chung, các kết quả này xác thực tính hiệu quả của việc huấn luyện song ngữ đồng thời và việc sử dụng các mô hình tiền huấn luyện đa ngôn ngữ lớn cho phân loại ESG trong các ngôn ngữ ít tài nguyên. Khoảng cách tương đối nhỏ giữa hiệu suất tiếng Anh và tiếng Việt chứng minh thêm rằng phương pháp tiếp cận của chúng tôi đã thu hẹp thành công sự bất bình đẳng ngôn ngữ trong phân tích phân tích ESG. Các mô hình này thiết lập một điểm chuẩn đa ngôn ngữ mới cho phân loại ESG trong cả bối cảnh tiếng Anh và tiếng Việt.

### Tác động của các mô hình Không phân biệt hoa thường (`uncased`) đối với Hiệu suất tiếng Việt (The Impact of `uncased` Models on Vietnamese Performance)

Các kết quả trình bày trong Bảng trên tiết lộ một sự suy giảm hiệu suất đáng chú ý đối với các mô hình uncased như `BERT-base-multilingual-uncased` và `FinBERT` khi áp dụng vào bộ dữ liệu tiếng Việt. Quan sát này được minh họa thêm trong Hình dưới, cho thấy các đường cong hàm mất mát huấn luyện của ba mô hình đại diện. Cả hai mô hình uncased đều thể hiện hàm mất mát cao hơn đáng kể và sự hội tụ chậm hơn so với các đối chiếu cased của chúng, nhấn mạnh việc chúng không thể nắm bắt hiệu quả các đặc điểm ngôn ngữ tiếng Việt.

[Hình ảnh đồ thị So sánh hàm mất mát huấn luyện giữa các mô hình cased và uncased (loss_vs.pdf)]

Sự cách biệt về hiệu suất này có thể được giải thích do chiến lược tiền xử lý được áp dụng bởi các mô hình uncased. Cụ thể, các mô hình này chuyển đổi toàn bộ văn bản thành chữ thường và, nghiêm trọng hơn đối với các ngôn ngữ có dấu thanh như tiếng Việt, loại bỏ các dấu diacritic (dấu tiếng Việt). Trong khi việc chuyển chữ thường có thể có tác động ngữ nghĩa tối thiểu trong tiếng Anh, nó lại tạo ra những biến dạng nghiêm trọng trong tiếng Việt, nơi các dấu đóng vai trò thiết yếu để phân biệt giữa các từ và truyền tải ý nghĩa. Việc loại bỏ các dấu này đã vô tình đưa vào các nhiễu hệ thống, dẫn đến mất mát lớn thông tin ngữ nghĩa.

Để minh họa hiệu ứng này, Hình dưới trình bày các ví dụ về các từ tiếng Việt trước và sau khi xử lý uncased, làm nổi bật sự mơ hồ và sự sụp đổ ý nghĩa do việc loại bỏ dấu gây ra. Ví dụ, từ tiếng Việt có thể dẫn đến việc phân tách token sai và phân loại nhầm trong các ngữ cảnh ESG khi các dấu bị loại bỏ. Do đó, những phát hiện này nhấn mạnh tầm quan trọng của việc bảo tồn chữ hoa chữ thường và các dấu diacritic trong các mô hình đa ngôn ngữ dành cho các ngôn ngữ ít tài nguyên, phong phú về hình thái học, hoặc có dấu thanh như tiếng Việt.

Phân tích này chứng minh rằng chỉ riêng kiến trúc mô hình là không đủ để đảm bảo hiệu suất xuyên ngôn ngữ mạnh mẽ; các chiến lược tiền xử lý phải tính đến các đặc điểm chính tả và ngữ âm đặc thù của ngôn ngữ. Những phát hiện này nhấn mạnh nhu cầu cần cân nhắc cẩn thận khi lựa chọn các mô hình đa ngôn ngữ cho các ngôn ngữ như tiếng Việt. Những người thực hành nên ưu tiên các mô hình cased hoặc những mô hình bảo tồn dấu diacritic, vì các mô hình uncased có thể gây ra những biến dạng ngữ nghĩa nghiêm trọng và làm suy giảm hiệu suất đáng kể.

### Đánh giá điểm số ESG (ESG Score Evaluate)

**Hiệu suất phân loại cảm xúc cho khía cạnh Môi trường**

| Mô hình               | Độ chính xác tổng thể | F1 Tiêu cực (Negative) | F1 Trung tính (Neutral) | F1 Tích cực (Positive) |
| ----------------------- | --------------------------- | ------------------------ | ------------------------ | ------------------------ |
| PhoBERT                 | 93.31                       | 95.00                    | 92.12                    | 92.23                    |
| Vi-Electra              | **93.87**             | 94.85                    | **93.21**          | **93.33**          |
| Visobert                | 92.47                       | 94.12                    | 91.02                    | 91.23                    |
| DistilBERT-multilingual | 92.20                       | 93.85                    | 90.52                    | 91.01                    |
| DeBERTa                 | 91.36                       | 92.15                    | 92.30                    | 89.12                    |
| ViBERT                  | 91.08                       | 91.56                    | 90.12                    | 90.01                    |
| BERT-base               | 89.13                       | 90.01                    | 87.52                    | 88.31                    |
| RoBERTa                 | 87.46                       | 88.23                    | 85.12                    | 86.50                    |

Từ góc nhìn môi trường, các mô hình ngôn ngữ tiền huấn luyện như Vi-Electra, PhoBERT, và Visobert chứng minh hiệu suất vượt trội. Vi-Electra đạt độ chính xác cao nhất ở mức 93,87%, cùng với điểm số F1 vượt trội trên cả ba lớp (Tiêu cực, Trung tính, Tích cực), cho thấy khả năng phân loại cân bằng rất tốt. PhoBERT cũng ghi nhận một độ chính xác ấn tượng (93,31%) và đạt điểm F1 cao nhất cho lớp “Tiêu cực” (95,00%), thể hiện năng lực mạnh mẽ trong việc phát hiện nội dung tiêu cực về môi trường. DistilBERT-multilingual và Visobert theo sát phía sau với độ chính xác lần lượt là 92,2% và 92,47%, trong khi duy trì điểm số F1 ổn định giữa các lớp. Mặc dù DeBERTa đạt điểm số F1 rất cao cho lớp Trung tính (92,30%), nó lại cho thấy một sự sụt giảm đáng kể về độ chính xác (91,36%), khiến nó chỉ nằm trong nhóm có hiệu suất trung bình. Trong khi đó, BERT-base và đặc biệt là RoBERTa, vốn không được huấn luyện đa ngôn ngữ, thể hiện hiệu suất tương đối thấp, khiến chúng không phù hợp cho các tác vụ phân loại môi trường phức tạp.

**Hiệu suất phân loại cảm xúc cho khía cạnh Quản trị**

| Mô hình               | Độ chính xác tổng thể | F1 Tiêu cực (Negative) | F1 Trung tính (Neutral) | F1 Tích cực (Positive) |
| ----------------------- | --------------------------- | ------------------------ | ------------------------ | ------------------------ |
| PhoBERT                 | **92.04**             | **95.32**          | **92.56**          | **93.31**          |
| Vi-Electra              | 88.99                       | 91.20                    | 87.45                    | 87.65                    |
| Visobert                | 88.68                       | 91.15                    | 87.12                    | 87.01                    |
| DistilBERT-multilingual | 86.85                       | 89.52                    | 84.32                    | 85.12                    |
| DeBERTa                 | 86.23                       | 88.12                    | 84.56                    | 85.01                    |
| ViBERT                  | 85.93                       | 87.56                    | 83.12                    | 84.23                    |
| BERT-base               | 79.20                       | 88.11                    | 73.63                    | 76.72                    |
| RoBERTa                 | 65.74                       | 68.32                    | 62.15                    | 64.23                    |

Trong miền quản trị, PhoBERT tiếp tục dẫn đầu với độ chính xác 92,04% và điểm F1 rất cao trên cả ba lớp (Tiêu cực: 95,32, Trung tính: 92,56, Tích cực: 93,31). Mô hình này chứng minh tính hiệu quả cao trong việc nắm bắt ngữ nghĩa liên quan đến quản trị và phân loại chính xác các ý kiến. Vi-Electra và Visobert cũng cho thấy hiệu suất mạnh mẽ, với độ chính xác lần lượt là 88,99% và 88,68%, đặc biệt xuất sắc ở lớp "Tiêu cực" với điểm F1 trên 91. DistilBERT-multilingual và DeBERTa mang lại kết quả khá tốt (độ chính xác khoảng 86%) và vẫn là các lựa chọn khả thi khi cần một mô hình nhẹ hoặc hỗ trợ đa ngôn ngữ. ViBERT hoạt động ở mức trung bình (85,93%) và kém cạnh tranh hơn một chút so với các mô hình mới hơn. Mặc dù BERT-base đạt điểm F1 cao cho lớp Tiêu cực (88,11), nó lại chịu sự sụt giảm nghiêm trọng ở các lớp Trung tính (73,63) và Tích cực (76,72), dẫn đến độ chính xác tổng thể chỉ ở mức 79,2%. Cuối cùng, RoBERTa tiếp tục có hiệu suất thấp nhất với độ chính xác chỉ 65,74%, phản ánh rõ ràng sự không phù hợp của nó đối với các tác vụ phân loại quản trị.

**Hiệu suất phân loại cảm xúc cho khía cạnh Xã hội**

| Mô hình               | Độ chính xác tổng thể | F1 Tiêu cực (Negative) | F1 Trung tính (Neutral) | F1 Tích cực (Positive) |
| ----------------------- | --------------------------- | ------------------------ | ------------------------ | ------------------------ |
| PhoBERT                 | **92.75**             | 95.23                    | **91.23**          | **91.12**          |
| Vi-Electra              | 91.72                       | **96.25**          | 89.21                    | 89.15                    |
| Visobert                | 88.58                       | 91.12                    | 86.45                    | 87.02                    |
| DistilBERT-multilingual | 86.55                       | 89.12                    | 84.12                    | 85.31                    |
| DeBERTa                 | 86.55                       | 88.56                    | 85.12                    | 84.95                    |
| ViBERT                  | 83.79                       | 86.45                    | 81.23                    | 82.12                    |
| BERT-base               | 75.86                       | 78.12                    | 72.15                    | 74.32                    |
| RoBERTa                 | 73.79                       | 75.32                    | 70.12                    | 72.15                    |

Trong miền xã hội, nơi thường liên quan đến nội dung đa dạng hơn và các sắc thái tinh tế hơn, PhoBERT tiếp tục khẳng định vị thế của mình bằng cách đạt độ chính xác cao nhất (92,75%) cùng với điểm số F1 nổi bật trên tất cả các lớp, đặc biệt là lớp Tiêu cực (95,23). Vi-Electra bám sát ngay sau với độ chính xác 91,72%, nổi bật với khả năng phát hiện nội dung tiêu cực (96,25 F1), mức cao nhất trong số tất cả các mô hình trên tất cả các miền. Visobert, DeBERTa, và DistilBERT-multilingual cho thấy hiệu suất ổn định (độ chính xác trên 86%) và chứng minh năng lực phân loại mạnh mẽ trong bối cảnh ngôn ngữ hết sức linh hoạt của các thảo luận xã hội. ViBERT duy trì vị trí trung bình với độ chính xác 83,79%, thấp hơn nhóm dẫn đầu. Các mô hình cũ hơn như BERT-base và RoBERTa, vốn không được tiền huấn luyện bằng tiếng Việt hoặc trong một thiết lập đa ngôn ngữ, tiếp tục hoạt động kém, với độ chính xác tương ứng chỉ đạt 75,86% và 73,79%. Điểm số F1 của chúng cho lớp Trung tính đặc biệt thấp, cho thấy khó khăn trong việc phân biệt giữa các sắc thái xã hội trung tính và tích cực.

---

## Phần mềm (Software)

Quy trình tạo ra các kết quả phân tích ESG bắt đầu bằng việc tải lên một tài liệu PDF thông qua trình tải tệp nằm ở cột bên trái của giao diện. Sau khi tệp PDF được tải lên, người dùng có thể tiến hành trích xuất văn bản bằng một trong hai phương pháp có sẵn. Phương pháp thứ nhất bao gồm việc lựa chọn thủ công các phần văn bản cụ thể trong trình xem PDF bằng cách bôi đen nội dung liên quan, hành động này sẽ tự động lưu văn bản được chọn vào các tệp tạm thời. Phương pháp thứ hai sử dụng nút "Lấy toàn bộ văn bản PDF" để tự động trích xuất toàn bộ nội dung tài liệu và chuẩn hóa nó cho quá trình phân tích. Sau khi chuẩn bị văn bản, người dùng phải chọn công ty phù hợp từ danh mục thả xuống (dropdown menu) hoặc nhập tên công ty mới, vì lựa chọn này quyết định các yếu tố trọng số ESG đặc thù theo ngành sẽ được áp dụng trong quá trình tính toán điểm số theo các tiêu chuẩn Bản đồ tính trọng yếu của SASB. Giao diện công cụ của chúng tôi được minh họa trong Hình dưới đây.

[Hình ảnh minh họa giao diện cho hệ thống phân loại và tính điểm ESG (hinh_1.png)]

Sau khi chuẩn bị văn bản, người dùng rà soát nội dung được trích xuất trong vùng phân tích để đảm bảo nội dung đáp ứng yêu cầu tối thiểu 10 ký tự cho việc phân tích. Hệ thống tự động hiển thị các số liệu thống kê văn bản bao gồm số từ, số dòng và số câu, đồng thời cung cấp một chỉ báo trạng thái hiển thị khi văn bản đã sẵn sàng để phân tích. Khi quá trình xác thực hoàn tất, người dùng bắt đầu phân tích ESG bằng cách nhấp vào nút "Phân tích ESG", hành động này kích hoạt hệ thống xử lý tự động để phân loại văn bản vào các danh mục Môi trường, Xã hội, Quản trị và Không liên quan, đồng thời thực hiện phân tích cảm xúc cho từng khía cạnh ESG.

[Hình ảnh minh họa kết quả đầu ra cho hệ thống phân loại và tính điểm ESG (hinh_2.png)]

Bước cuối cùng bao gồm việc rà soát các kết quả phân tích toàn diện, vốn được trình bày thông qua nhiều định dạng trực quan hóa bao gồm các biểu đồ thanh hiển thị số lượng câu trên mỗi danh mục, biểu đồ tròn hiển thị phân bổ phần trăm, và biểu đồ phân bổ cảm xúc minh họa sự phân tách Tích cực/Trung tính/Tiêu cực trên các danh mục ESG. Hệ thống tự động tính toán điểm số ESG có trọng số dựa trên phân tích cảm xúc và các yếu tố trọng số đặc thù theo ngành, trình bày các kết quả trong một định dạng bảng chi tiết hiển thị các giá trị trung bình cảm xúc và các đóng góp có trọng số cho từng khía cạnh ESG, cuối cùng cung cấp một đánh giá hiệu quả ESG hoàn chỉnh. Tất cả các phân tích đầu vào được thể hiện trong Hình trên.

---

## Kết luận và Hướng đi tương lai (Conclusion and Future Work)

Luận văn này giải quyết khoảng trống nghiêm trọng trong các tài nguyên và công cụ NLP dành cho phân tích Môi trường, Xã hội và Quản trị (ESG) bằng tiếng Việt, một ngôn ngữ ít tài nguyên vốn phần lớn bị bỏ qua trong các nghiên cứu trước đây. Để thu hẹp khoảng trống này, chúng tôi đã giới thiệu bộ dữ liệu **ViEn-ESG**, một tài nguyên song ngữ (Việt – Anh) quy mô lớn bao gồm 130.798 mẫu ở cấp độ câu được gắn nhãn trên bốn lớp (Môi trường, Xã hội, Quản trị và Trung tính). Theo hiểu biết của chúng tôi, đây là bộ dữ liệu công khai đầu tiên được thiết kế cho phân loại văn bản ESG bằng tiếng Việt, cung cấp một nền tảng có giá trị cho các nghiên cứu tương lai về phân tích tính bền vững cho các thị trường mới nổi.

Xây dựng trên bộ dữ liệu này, chúng tôi đã tinh chỉnh một loạt các mô hình dựa trên BERT cho nhiệm vụ phân loại ESG, chứng minh tính hiệu quả của học chuyển giao đối với các thiết lập chuyên biệt theo miền và ít tài nguyên. Mô hình song ngữ đạt hiệu suất tốt nhất của chúng tôi đã đạt điểm số F1 là 94,83% trên tiếng Anh và 91,94% trên tiếng Việt, trong khi mô hình chỉ sử dụng tiếng Việt đạt độ chính xác 94,66%. Những kết quả này thiết lập một điểm chuẩn đa ngôn ngữ mạnh mẽ cho phân loại ESG và nhấn mạnh khả năng của các mô hình ngôn ngữ tiền huấn luyện lớn trong việc mang lại hiệu suất chuyển giao xuyên ngôn ngữ mạnh mẽ.

Bên cạnh việc phân loại, chúng tôi đã giới thiệu một cơ chế tính điểm ESG tổng hợp các tín hiệu cảm xúc trên các khía cạnh Môi trường, Xã hội và Quản trị. Phương pháp tiếp cận này cung cấp các đánh giá định lượng, có thể giải thích được về tính bền vững của doanh nghiệp, mang lại giá trị thực tiễn cho các nhà nghiên cứu, các tổ chức xếp hạng và các bên liên quan trong ngành. Nhìn chung, các đóng góp của chúng tôi thúc đẩy cả bối cảnh phương pháp luận và thực tiễn cho phân tích ESG trong các ngôn ngữ ít tài nguyên.

Dựa trên các phát hiện và đóng góp của luận văn này, chúng tôi xác định một số hướng đi cho các nghiên cứu tương lai để thúc đẩy phân loại ESG trong bối cảnh tiếng Việt và đa ngôn ngữ:

* **Làm phong phú và mở rộng bộ dữ liệu:** Với bộ dữ liệu ViEn-ESG được phát hành trong công trình này, các nỗ lực tương lai có thể mở rộng bộ dữ liệu với các nguồn ESG bổ sung như các công bố CSR và báo cáo bền vững. Các kỹ thuật tăng cường dữ liệu và tích hợp dữ liệu có cấu trúc (ví dụ: lượng khí thải, chỉ số lực lượng lao động) có thể nâng cao hơn nữa hiệu suất mô hình và khả năng áp dụng.
* **Mở rộng sang các tác vụ ESG rộng hơn:** Vượt ra ngoài việc phân loại, nghiên cứu tương lai có thể khám phá các tác vụ như nhận dạng thực thể ESG (ESG entity recognition), phát hiện loại tác động và thời hạn tác động, và mô hình hóa chủ đề phân cấp để trích xuất thông tin sâu sắc hơn từ các báo cáo bền vững.
* **Mở rộng xuyên ngôn ngữ và đa ngôn ngữ:** Mở rộng sang các ngôn ngữ bổ sung và tận dụng các kỹ thuật học chuyển giao xuyên ngôn ngữ tiên tiến có thể cho phép phân tích ESG có khả năng mở rộng trong các bối cảnh ngôn ngữ đa dạng, hỗ trợ các đánh giá bền vững toàn cầu.
* **Các ứng dụng trong thế giới thực:** Thông tin ESG được phân loại có thể được sử dụng để theo dõi hiệu quả phi tài chính của các công ty trong thời gian gần như thực tế hoặc để nâng cao các hệ thống xếp hạng ESG với các thông tin chi tiết kịp thời và có thể giải thích được.

Bằng cách giải quyết các hướng đi này, nghiên cứu tương lai có thể củng cố hơn nữa các phân tích ESG đa ngôn ngữ có khả năng mở rộng và đóng góp vào các khung đánh giá tính bền vững minh bạch và định hướng bằng dữ liệu hơn.

---

## Tài liệu tham khảo (References)

*(Mục này trống trong văn bản gốc)*

---

## Phụ lục: Gợi ý dịch thuật cho EraX-Translator-V1.0 (Translate Prompt for EraX-Translator-V1.0)

Để làm phong phú thêm phần tiếng Việt của bộ dữ liệu của chúng tôi, chúng tôi đã áp dụng một chiến lược gắn nhãn dựa trên dịch thuật giúp chuyển đổi các câu tiếng Anh chất lượng cao có nhãn ESG tiêu chuẩn vàng sang tiếng Việt. Phương pháp tiếp cận này cung cấp một phương pháp có thể mở rộng để tạo dữ liệu được gắn nhãn trong một ngôn ngữ ít tài nguyên, đảm bảo tính liên kết ngữ nghĩa giữa cả hai ngôn ngữ.

Đối với quy trình này, chúng tôi đã sử dụng gợi ý hệ thống (system prompt) chính thức được khuyến nghị bởi các tác giả của mô hình `erax-ai/EraX-Translator-V1.0` để đảm bảo các bản dịch chính xác và bảo tồn được miền chuyên biệt:

[Hình ảnh của Gợi ý dành cho các mô hình EraX-Translator-V1.0. (prompt.png)]

---
