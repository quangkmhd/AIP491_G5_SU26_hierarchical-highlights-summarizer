# Lexical Normalization Evaluation Report

## Run Configuration

- sherpa_dir: `/home/quangnhvn34/dev/me/AIP491/data/processed/output_sherpa`
- soniox_dir: `/home/quangnhvn34/dev/me/AIP491/data/processed/output_soniox`
- ollama_model: `gemma4:12b-it-qat`
- ollama_base_url: `http://127.0.0.1:11434`
- mode: `ollama`
- limit: `all`
- max_workers: `1`
- pair_count: `239`
- wall_seconds: `0.001`

## Overall Metrics

| Metric | Raw | Corrected | Delta | Better? |
| :--- | ---: | ---: | ---: | :---: |
| WER | 0.138886 | 0.135636 | -0.003250 | yes |
| CER | 0.111628 | 0.108856 | -0.002772 | yes |

## Confusion Matrix

| Category | Count | Meaning |
| :--- | ---: | :--- |
| TP | 11 | ASR wrong, corrector fixed correctly |
| FN | 125 | ASR wrong, corrector left wrong |
| FP1 | 3 | ASR correct, corrector broke it |
| FP2 | 100 | ASR wrong, corrector changed to a different wrong value |

Total utterances: 239, total latency: 3823443 ms, mean latency: 15997 ms

## Representative Examples

### TP Examples (top 11)

- video_id=01_tsKMxDpZV68 seg=4
  - raw: `NHƯNG MÀ VẤN ĐỀ ĐẶT RA LÀ MÌNH NHÌN VÀO ĐÂU ĐỂ MÌNH KẾT LUẬN LÀ NGƯỜI NÀY CÓ NHỮNG CÁI KỸ NĂNG ĐÁP ỨNG ĐÚNG YÊU CẦU THÌ BÂY GIỜ CÁC BẠN XEM THỬ CÁI ĐỊNH NGHĨA BÊN CẠNH CÁC BẠN NHÌN THẤY CÁI VÍ DỤ BÊN CẠNH`
  - corrected: `Nhưng mà vấn đề đặt ra là mình nhìn vào đâu để mình kết luận là người này có những cái kỹ năng đáp ứng đúng yêu cầu thì bây giờ các bạn xem thử cái định nghĩa bên cạnh các bạn nhìn thấy cái ví dụ bên cạnh`
  - truth: `Nhưng mà vấn đề đặt ra là: mình nhìn vào đâu để mình kết luận là người này có những cái kỹ năng đáp ứng đúng yêu cầu? Thì bây giờ các bạn xem thử cái định nghĩa bên cạnh. Các bạn nhìn thấy cái ví dụ bên cạnh.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=5
  - raw: `VỪA TẬP TRUNG VÀO ĐIỀU MÀ ỨNG VIÊN ĐANG NÓI VỪA QUAN SÁT NGÔN NGỮ CƠ THỂ CỦA ỨNG VIÊN ĐẶT CÂU HỎI THEO CẤU TRÚC PHỄU VÀ HIỆU QUẢ NHẰM THĂM DÒ PHÁN ĐOÁN VÀ CHO KẾT LUẬN ĐẦY ĐỦ VỀ KHẢ NĂNG THẬT CỦA ỨNG VIÊN SO VỚI YÊU CẦU CÔNG VIỆC BÂY GIỜ CÁC BẠN NHÌN VÀO CÁI B CÁC BẠN THẤY CÁI B`
  - corrected: `Vừa tập trung vào điều mà ứng viên đang nói vừa quan sát ngôn ngữ cơ thể của ứng viên đặt câu hỏi theo cấu trúc phễu và hiệu quả nhằm thăm dò phán đoán và cho kết luận đầy đủ về khả năng thật của ứng viên so với yêu cầu công việc. Bây giờ các bạn nhìn vào cái B, các bạn thấy cái B.`
  - truth: `Vừa tập trung vào điều mà ứng viên đang nói, vừa quan sát ngôn ngữ cơ thể của ứng viên, đặt câu hỏi theo cấu trúc phễu và hiệu quả nhằm thăm dò, phán đoán và cho kết luận đầy đủ về khả năng thật của ứng viên so với yêu cầu công việc. Bây giờ các bạn nhìn vào cái B, các bạn thấy cái B.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=10
  - raw: `VỪA QUAN SÁT NGÔN NGỮ CƠ THỂ CỦA ỨNG VIÊN VẬY LÀ MÌNH THẤY QUAN SÁT NGÔN NGỮ CƠ THỂ LÀ QUAN SÁT CÁI GÌ RỒI ĐẶT CÂU HỎI THEO CẤU TRÚC PHẺO NHƯ VẬY THÌ ĐẶT CÂU HỎI THEO CẤU TRÚC PHẺO LÀ NÓ TỪ TO ĐẾN NHỎ VÀ HIỆU QUẢ`
  - corrected: `Vừa quan sát ngôn ngữ cơ thể của ứng viên vậy là mình thấy quan sát ngôn ngữ cơ thể là quan sát cái gì rồi đặt câu hỏi theo cấu trúc phễu như vậy thì đặt câu hỏi theo cấu trúc phễu là nó từ to đến nhỏ và hiệu quả`
  - truth: `Vừa quan sát ngôn ngữ cơ thể của ứng viên, vậy là mình thấy quan sát ngôn ngữ cơ thể là quan sát cái gì rồi. Đặt câu hỏi theo cấu trúc phễu, như vậy thì đặt câu hỏi theo cấu trúc phễu là nó từ to đến nhỏ, và hiệu quả.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=18
  - raw: `ĐÓ LÀ DÙNG KHOA HỌC ĐỂ TẠO NÊN GIẢI PHÁP CHO CẢ CUỘC ĐỜI CỦA CON NGƯỜI DO ĐÓ CÁI SẢN PHẨM CỦA HÌNH HỌ TẠO THÀNH LÀ CÁC BẠN THẤY LÀ SẢN PHẨM CỦA HỌ ĐỀU ĐÁP ỨNG TỪ LÚC CÒN TRONG BÀO THAI CỦA MẸ CHO ĐẾN CẢ KHI VỀ GIÀ`
  - corrected: `Đó là dùng khoa học để tạo nên giải pháp cho cả cuộc đời của con người, do đó cái sản phẩm của họ tạo thành là các bạn thấy là sản phẩm của họ đều đáp ứng từ lúc còn trong bào thai của mẹ cho đến cả khi về già`
  - truth: `Đó là: dùng khoa học để tạo nên giải pháp cho cả cuộc đời của con người. Do đó cái sản phẩm của họ tạo thành là, các bạn thấy là sản phẩm của họ đều đáp ứng từ lúc còn trong bào thai của mẹ cho đến cả khi về già.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=19
  - raw: `THÌ ĐÓ LÀ MỘT HÌNH ẢNH VƯƠN TỚI RỒI CÁC GIÁ TRỊ MỖI MỘT CÔNG TY ĐI THEO ĐỀU CÓ CÁI GIÁ TRỊ CỐT LÕI THÌ ĐÓ LÀ CÁI NỀN TẢNG MÀ PHẢI DỰA VÀO ĐÓ ĐỂ XÂY DỰNG DỰA TRÊN NỀN TẢNG ĐÓ THÌ TRONG CÁI KIẾN TRÚC KHUNG NĂNG LỰC LÀ ĐẦU TIÊN NÓ SẼ CÓ NĂNG LỰC CỐT LÕI`
  - corrected: `Thì đó là một hình ảnh vươn tới rồi các giá trị mỗi một công ty đi theo đều có cái giá trị cốt lõi thì đó là cái nền tảng mà phải dựa vào đó để xây dựng dựa trên nền tảng đó thì trong cái kiến trúc khung năng lực là đầu tiên nó sẽ có năng lực cốt lõi`
  - truth: `Thì đó là một hình ảnh vươn tới, rồi các giá trị mỗi một công ty đi theo đều có cái giá trị cốt lõi. Thì đó là cái nền tảng mà phải dựa vào đó để xây dựng. Dựa trên nền tảng đó, thì trong cái kiến trúc khung năng lực là đầu tiên nó sẽ có năng lực cốt lõi.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=26
  - raw: `ĐÓ LÀ NĂM MỘT NGÀN CHÍN TRĂM CHÍN MƯƠI HAI NHƯNG SAU NÀY TRONG QUÁ TRÌNH PHÁT TRIỂN THÌ NGƯỜI TA NHẬN THẤY CÓ MỘT ĐIỀU BẤT HỢP LÝ LÀ NHƯ THẾ NÀY ĐIỀU BẤT HỢP LÝ THỨ NHẤT ĐÓ LÀ NGƯỜI TA THẤY LÀ GIẢ SỬ NHƯ TÔI CÓ`
  - corrected: `Đó là năm 1992 nhưng sau này trong quá trình phát triển thì người ta nhận thấy có một điều bất hợp lý là như thế này: điều bất hợp lý thứ nhất đó là người ta thấy là giả sử như tôi có`
  - truth: `Đó là năm 1992, nhưng sau này, trong quá trình phát triển, thì người ta nhận thấy có một điều bất hợp lý là như thế này. Điều bất hợp lý thứ nhất, đó là người ta thấy là giả sử như tôi có...`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=37
  - raw: `CẤP CAO THÌ PHẢI LÀM GƯƠNG VÀ PHẢI THỂ HIỆN CHO NGƯỜI TA THẤY CÁI CÁCH TÔI GIẢI THÍCH LÀM SAO ĐỂ NGƯỜI TA NGHE VÀ NGƯỜI TA CHỊU ĐI THEO THÌ ĐÓ LÀ CÁI NĂNG LỰC LÃNH ĐẠO VÀ KIẾN TRÚC CỦA CUNG NĂNG LỰC LÃNH ĐẠO CÒN BÂY GIỜ CÁI MÀ KIM ANH CHIA SẺ LÀ`
  - corrected: `Cấp cao thì phải làm gương và phải thể hiện cho người ta thấy cái cách tôi giải thích làm sao để người ta nghe và người ta chịu đi theo thì đó là cái năng lực lãnh đạo và kiến trúc của khung năng lực lãnh đạo còn bây giờ cái mà Kim Anh chia sẻ là`
  - truth: `Cấp cao thì phải làm gương và phải thể hiện cho người ta thấy cái cách tôi giải thích làm sao để người ta nghe, và người ta chịu đi theo, thì đó là cái năng lực lãnh đạo và kiến trúc của khung năng lực lãnh đạo. Còn bây giờ cái mà Kim Anh chia sẻ là.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=62
  - raw: ``
  - corrected: ``
  - truth: ``
  - reason: ``
- video_id=02_Wu9lugM9SRQ seg=44
  - raw: ``
  - corrected: ``
  - truth: ``
  - reason: ``
- video_id=03_oKBGl5IxRgM seg=48
  - raw: ``
  - corrected: ``
  - truth: ``
  - reason: ``
- video_id=04_ZILLE80oY8g seg=48
  - raw: `CHO CHÍNH MÌNH VÀ DOANH NGHIỆP CỦA MÌNH TĂNG TRƯỞNG BỀN VỮNG TRONG KỶ NGUYÊN SỐ`
  - corrected: `Cho chính mình và doanh nghiệp của mình tăng trưởng bền vững trong kỷ nguyên số`
  - truth: `Cho chính mình và doanh nghiệp của mình tăng trưởng bền vững trong kỷ nguyên số.`
  - reason: ``

### FN Examples (top 20)

- video_id=01_tsKMxDpZV68 seg=0
  - raw: `CHÚNG TA SẼ NÓI QUA CÁI PHẦN NĂNG LỰC`
  - corrected: `Chúng ta sẽ nói qua cái phần năng lực`
  - truth: `Chúng ta sẽ nói qua cái phần năng lực. Ờ.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=1
  - raw: `KIM ANH MƯỢN CÁI ĐỊNH NGHĨA CỦA TỔ CHỨC GỌI LÀ QUẢN LÝ NĂNG LỰC TRÊN THẾ GIỚI THÌ NGƯỜI TA ĐỊNH NGHĨA NHƯ THẾ NÀY NĂNG LỰC LÀ MỘT BỘ HÀNH VI CÁC BẠN NHỚ CÁI CHỮ GIÙM KIM ANH MỘT BỘ HÀNH VI CÓ NGHĨA NÓ KHÔNG PHẢI LÀ BỘ HÀNH VI MÀ NÓ LÀ BỘ HÀNH VI NÓ MÔ TẢ GÌ MÔ TẢ KHẢ NĂNG MÔ TẢ KIẾN THỨC MÔ TẢ KỸ NĂNG CÁC ĐẶC ĐIỂM HAY LÀ ĐỘNG LỰC CẦN CÓ ĐỂ THỰC HIỆN CÔNG VIỆC ĐÓ THÀNH CÔNG`
  - corrected: `KIM ANH MƯỢN CÁI ĐỊNH NGHĨA CỦA TỔ CHỨC GỌI LÀ QUẢN LÝ NĂNG LỰC TRÊN THẾ GIỚI THÌ NGƯỜI TA ĐỊNH NGHĨA NHƯ THẾ NÀY NĂNG LỰC LÀ MỘT BỘ HÀNH VI CÁC BẠN NHỚ CÁI CHỮ GIÙM KIM ANH MỘT BỘ HÀNH VI CÓ NGHĨA NÓ KHÔNG PHẢI LÀ BỘ HÀNH VI MÀ NÓ LÀ BỘ HÀNH VI NÓ MÔ TẢ GÌ MÔ TẢ KHẢ NĂNG MÔ TẢ KIẾN THỨC MÔ TẢ KỸ NĂNG CÁC ĐẶC ĐIỂM HAY LÀ ĐỘNG LỰC CẦN CÓ ĐỂ THỰC HIỆN CÔNG VIỆC ĐÓ THÀNH CÔNG`
  - truth: `Kim Anh mượn cái định nghĩa của tổ chức, ờm, gọi là "quản lý năng lực" trên thế giới thì người ta định nghĩa như thế này: năng lực là một bộ hành vi, các bạn nhớ cái chữ dùng Kim Anh, một bộ hành vi, có nghĩa nó không phải là một hành vi mà nó là một bộ hành vi. Nó mô tả gì? Mô tả khả năng, mô tả kiến thức, mô tả kỹ năng, các đặc điểm hay là động lực cần có để thực hiện công- công việc đó thành công.`
  - reason: `validation_error:1 validation error for CorrectionResponse
  Invalid JSON: EOF while parsing a string at line 10 column 230 [type=json_invalid, input_value='{\n  "llm_corrected": "K... năng, mô tả kiến', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/json_invalid`
- video_id=01_tsKMxDpZV68 seg=2
  - raw: `THÌ ĐỂ CHO CÁC BẠN DỄ HIỂU THÌ KIM ANH MƯỢN MỘT CÁI CÔNG VIỆC HẾT SỨC ĐƠN GIẢN MÀ TRÁCH TẤT CẢ MỌI NGƯỜI TRONG KHÁN PHÒNG NÀY CÓ LẼ CŨNG ĐÃ TỪNG QUEN THUỘC ĐÓ LÀ KỸ NĂNG PHỎNG VẤN THÌ CÁC BẠN THẤY THƯỜNG THƯỜNG MỘT NGƯỜI PHỎNG VẤN TUYỂN CHỌN`
  - corrected: `Thì để cho các bạn dễ hiểu thì Kim Anh mượn một cái công việc hết sức đơn giản mà trách tất cả mọi người trong khán phòng này có lẽ cũng đã từng quen thuộc đó là kỹ năng phỏng vấn thì các bạn thấy thường thường một người phỏng vấn tuyển chọn`
  - truth: `Thì để cho các bạn dễ hiểu, thì Kim Anh mượn một cái công việc hết sức đơn giản mà tất- tất cả mọi người trong khán phòng này có lẽ cũng đã từng quen thuộc, đó là... kỹ năng phỏng vấn. Thì các bạn thấy, thường thường á, một cái người phỏng vấn tuyển chọn.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=7
  - raw: `EM QUAN SÁT RẤT LÀ CHÍNH XÁC TỨC LÀ NHƯNG MÀ CHỊ MUỐN THẬT SỰ CHỊ MUỐN CÓ MỘT CÁI TRAO ĐỔI NGẮN Ở ĐÂY ĐỂ LÀM CHO NÓ RÕ VÍ DỤ NHƯ HÀ MY NÓI LÀ HÀ MY THẤY CÁI MÔ TẢ BÊN BẢN B LÀ NÓ MÔ TẢ ĐƯỢC CÁI KỸ NĂNG NGHE RỒI VẬY THÌ CÁI CÂU NÀO CHO THẤY LÀ`
  - corrected: `Em quan sát rất là chính xác tức là nhưng mà chị muốn thật sự chị muốn có một cái trao đổi ngắn ở đây để làm cho nó rõ ví dụ như Hà My nói là Hà My thấy cái mô tả bên bản B là nó mô tả được cái kỹ năng nghe rồi vậy thì cái câu nào cho thấy là`
  - truth: `Em quan sát rất là chính xác, tức là... ờ, nhưng mà chị muốn, thật sự chị muốn nghe có một cái trao đổi ngắn ở đây để làm cho nó rõ. Ví dụ như Hà My nói là Hà My thấy cái mô tả bên bảng B là nó mô tả được cái kỹ năng nghe, rồi vậy thì cái câu nào cho thấy là...`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=9
  - raw: `THÌ CÁC BẠN THẤY LÀ NHÌN ĐÂY SƠ NÉT THÌ MÌNH THẤY LÀ HAI CHUYỆN BẢN B LÀ VÍ DỤ VỀ NĂNG LỰC CÒN BẢN A LÀ LIỆT KÊ CÁC DANH MỤC CÁC KỸ NĂNG THÌ NHƯ VẬY CÁC BẠN THẤY LÀ B MÔ TẢ VỀ HÀNH VI MÀ HÀNH VI LÀ PHẢI QUAN SÁT ĐƯỢC CÁC BẠN THẤY NÓI VỀ VỪA TẬP TRUNG VÀO ĐIỀU MÀ ỨNG VIÊN ĐANG NÓI MÌNH QUAN SÁT ĐƯỢC`
  - corrected: `Thì các bạn thấy là nhìn đây sơ nét thì mình thấy là hai chuyện bản B là ví dụ về năng lực còn bản A là liệt kê các danh mục các kỹ năng thì như vậy các bạn thấy là B mô tả về hành vi mà hành vi là phải quan sát được các bạn thấy nói về vừa tập trung vào điều mà ứng viên đang nói mình quan sát được`
  - truth: `Thì các bạn thấy là nhìn đây sơ nét thì mình thấy là 2 chuyện: bản B là ví dụ về năng lực, còn bản A là liệt kê các danh mục các kỹ năng. Thì như vậy các bạn thấy là B mô tả về hành vi, mà hành vi là phải quan sát được. Các bạn thấy nói về vừa tập trung vào điều mà ứng viên đang nói, mình quan sát được.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=12
  - raw: `RỒI BÂY GIỜ CHÚNG TA SẼ ĐI TIẾP LÀ CHÚNG TA XEM THỬ COI VỀ NĂNG LỰC LÀ BIẾT RỒI NHƯNG CÒN VỀ KIẾN TRÚC KHUNG NĂNG LỰC VÀ KHUNG NĂNG LỰC NHƯ THẾ NÀO LÀ ĐẠT YÊU CẦU THÌ CHÚNG TA CÙNG NHAU KHÁM PHÁ TIẾP NHÉ`
  - corrected: `Rồi bây giờ chúng ta sẽ đi tiếp là chúng ta xem thử coi về năng lực là biết rồi nhưng còn về kiến trúc khung năng lực và khung năng lực như thế nào là đạt yêu cầu thì chúng ta cùng nhau khám phá tiếp nhé`
  - truth: `Rồi, bây giờ chúng ta sẽ đi tiếp là chúng ta xem thử coi, à, về năng lực là biết rồi, nhưng còn về kiến trúc khung năng lực và khung năng lực như thế nào là đạt yêu cầu thì chúng ta cùng nhau khám phá tiếp nhé.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=13
  - raw: `RỒI BÂY GIỜ NÓI VỀ KIẾN TRÚC CỦA KHUNG NĂNG LỰC THÌ NÓ CŨNG GIỐNG NHƯ TRONG MỘT CĂN NHÀ THÌ NÓ SẼ CÓ TẦNG THẤP TẦNG CAO NHƯNG MÀ KIẾN TRÚC KHUNG NĂNG LỰC NÓ BAO GỒM CÓ CÁI GÌ THỨ NHẤT LÀ CÁC BẠN THẤY LÀ ĐIỀU ĐẦU TIÊN KHUNG NĂNG LỰC BAO GIỜ NÓ CŨNG ĐƯỢC XÂY DỰNG TỪ CÁI NỀN TẢNG`
  - corrected: `Rồi bây giờ nói về kiến trúc của khung năng lực thì nó cũng giống như trong một căn nhà thì nó sẽ có tầng thấp tầng cao nhưng mà kiến trúc khung năng lực nó bao gồm có cái gì thứ nhất là các bạn thấy là điều đầu tiên khung năng lực bao giờ nó cũng được xây dựng từ cái nền tảng`
  - truth: `Rồi, bây giờ nói về kiến trúc của khung năng lực thì nó cũng giống như trong một căn nhà, thì nó sẽ có tầng thấp tầng cao, nhưng mà kiến trúc khung năng lực nó bao gồm có cái gì? Thứ nhất là các bạn thấy là điều đầu tiên á, khung năng lực bao giờ nó cũng được xây dựng từ cái nền tảng.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=14
  - raw: `GỌI LÀ CÁI NỀN MÓNG ĐÓ LÀ CÁI VIỄN CẢNH VÀ CÁC GIÁ TRỊ VÀ KIM ANH MUỐN DỪNG ĐÂY MÌNH KHÔNG ĐỦ THỜI GIAN NHƯNG MÀ KIM ANH NÓI SƠ QUA VỀ TRONG QUÁ TRÌNH ĐI TƯ VẤN CHO CÁC DOANH NGHIỆP THÌ KIM ANH THẤY CÁC DOANH NGHIỆP NƯỚC NGOÀI THÌ CÁI VIỄN CẢNH CỦA HỌ HỌ MÔ TẢ RẤT RỘNG`
  - corrected: `Gọi là cái nền móng đó là cái viễn cảnh và các giá trị và Kim Anh muốn dừng đây mình không đủ thời gian nhưng mà Kim Anh nói sơ qua về trong quá trình đi tư vấn cho các doanh nghiệp thì Kim Anh thấy các doanh nghiệp nước ngoài thì cái viễn cảnh của họ họ mô tả rất rộng`
  - truth: `Gọi là cái nền móng, đó là cái viễn cảnh và các giá trị. Và Kim Anh muốn dừng đây, mình không đủ thời gian, nhưng mà Kim Anh nói sơ qua về trong quá trình đi tư vấn cho các doanh nghiệp, thì Kim Anh thấy các doanh nghiệp nước ngoài á, thì cái viễn cảnh của họ, họ mô tả rất rộng.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=15
  - raw: `VÀ RẤT LÀ BAO QUÁT TRONG KHI CÁI VIỄN CẢNH CỦA MÌNH KIM ANH XIN LỖI LÀ CÁI CHỮ VISION Ở BÊN VIỆT NAM MÌNH THƯỜNG HAY DỊCH LÀ TẦM NHÌN NHƯNG KIM ANH KHÔNG THÍCH DÙNG CÁI CHỮ ĐÓ LẮM KIM ANH CHỈ THÍCH DÙNG CÁI CHỮ VIỄN CẢNH VÀ HOÀI BÃO TẠI VÌ CHỮ TẦM NHÌN LÀ MÌNH CHỈ NHÌN NHƯNG MÀ MÌNH`
  - corrected: `Và rất là bao quát trong khi cái viễn cảnh của mình Kim Anh xin lỗi là cái chữ vision ở bên Việt Nam mình thường hay dịch là tầm nhìn nhưng Kim Anh không thích dùng cái chữ đó lắm Kim Anh chỉ thích dùng cái chữ viễn cảnh và hoài bão tại vì chữ tầm nhìn là mình chỉ nhìn nhưng mà mình`
  - truth: `Và rất là bao quát, trong khi cái viễn cảnh của mình... ờ, xin lỗi, Kim Anh xin lỗi là cái chữ "vision" á ở bên Việt Nam mình thường hay dịch là "tầm nhìn", nhưng Kim Anh không thích dùng cái chữ đó lắm. Kim Anh chỉ thích dùng cái chữ "viễn cảnh" và "hoài bão", tại vì chữ "tầm nhìn" là mình chỉ nhìn, nhưng mà mình...`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=16
  - raw: `KHÔNG NÓI KHÁI QUÁT LÊN ĐƯỢC CÁI VISION ĐÓ LÀ HÌNH ẢNH RẤT XA MÀ TÔI MUỐN ĐƯỢC TẠO TÔI MUỐN CÔNG TY TÔI TRỞ THÀNH THÌ ĐÓ LÀ VIỄN CẢNH VÀ CÁC GIÁ TRỊ THÌ KHI KIM ANH ĐI TƯ VẤN CHO CÁC CÔNG TY VIỆT NAM THÌ KIM ANH THẤY RỒI NÀY`
  - corrected: `Không nói khái quát lên được cái vision đó là hình ảnh rất xa mà tôi muốn được tạo tôi muốn công ty tôi trở thành thì đó là viễn cảnh và các giá trị thì khi Kim Anh đi tư vấn cho các công ty Việt Nam thì Kim Anh thấy rồi này`
  - truth: `Không nói khái quát lên được, cái vision đó là hình ảnh rất xa mà tôi muốn được tạo, tôi muốn... tôi muốn công ty tôi trở thành, thì đó là viễn cảnh và các giá trị. Thì khi Kim Anh đi tư vấn cho các công ty Việt Nam thì Kim Anh thấy vậy nè.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=17
  - raw: `MỘT SỐ DOANH NGHIỆP VIỆT NAM CÓ KHUYNH HƯỚNG NÀY NÈ EM MUỐN TRỞ THÀNH HẠNG NHẤT ĐÔNG NAM Á THÌ CÁI HẠNG NHẤT ĐÔNG NAM Á NÓ CHỈ LÀ MỘT TRONG NHỮNG CÁI MỐC QUAN TRỌNG CỦA DOANH NGHIỆP ĐÓ TRONG KHI CÁI VIỄN CẢNH ĐÓ LÀ NHƯ THẾ NÀY NÈ VÍ DỤ NHA KIM ANH LẤY CÁI VIỄN CẢNH CỦA ABO`
  - corrected: `Một số doanh nghiệp Việt Nam có khuynh hướng này nè em muốn trở thành hạng nhất Đông Nam Á thì cái hạng nhất Đông Nam Á nó chỉ là một trong những cái mốc quan trọng của doanh nghiệp đó trong khi cái viễn cảnh đó là như thế này nè ví dụ nha Kim Anh lấy cái viễn cảnh của ABO`
  - truth: `Một số doanh nghiệp Việt Nam có khuynh hướng vậy nè: "Em muốn trở thành hạng nhất Đông Nam Á." Thì cái hạng nhất Đông Nam Á nó nó chỉ là một trong những cái móc quan trọng của doanh nghiệp đó, trong khi cái viễn cảnh nó là như thế này nè, ví dụ nha, Kim Anh lấy cái viễn cảnh của Abbott.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=20
  - raw: `RỒI SAU ĐÓ NÓ CÓ NĂNG LỰC CỦA TỪNG NHÓM CÔNG VIỆC VÍ DỤ NHƯ TRONG CÔNG TY THÌ SẼ CÓ PHÒNG SALE PHÒNG MARKETING PHÒNG KẾ TOÁN RỒI PHÒNG NHÂN SỰ VÀ PHÍA TRÊN CÙNG TRONG TỪNG CÁI PHÒNG NÓ SẼ CÓ NHỮNG CÁI NĂNG LỰC CỦA TỪNG BỘ PHẬN CỤ THỂ VÍ DỤ NHƯ`
  - corrected: `Rồi sau đó nó có năng lực của từng nhóm công việc ví dụ như trong công ty thì sẽ có phòng sale, phòng marketing, phòng kế toán rồi phòng nhân sự và phía trên cùng trong từng cái phòng nó sẽ có những cái năng lực của từng bộ phận cụ thể ví dụ như`
  - truth: `Rồi sau đó nó có năng lực của từng nhóm công việc, ví dụ như trong công ty thì sẽ có phòng Sales, phòng Marketing, phòng Kế toán, rồi phòng Nhân sự. Và phía trên cùng, trong từng cái phòng á, nó sẽ có những cái năng lực của từng bộ phận cụ thể, ví dụ như.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=23
  - raw: `CÁI CÔNG VIỆC NHỎ ĐÓ GỌI LÀ NĂNG LỰC CỦA TỪNG CÔNG VIỆC CỤ THỂ HOẶC LÀ TRONG SA KIM ANH Ở TRONG SA RA THÌ KIM ANH MÔ TẢ RẤT DỄ VÍ DỤ NHƯ LÀ TRONG SA THÌ CÓ CNB RỒI NÓ CÓ TỨC LÀ VỀ THÙ LAO LƯƠNG BỔNG PHÚC LỢI RỒI NÓ CÓ TUYỂN DỤNG THÌ TỪNG NĂNG LỰC NHƯ VẬY NÓ SẼ`
  - corrected: `Cái công việc nhỏ đó gọi là năng lực của từng công việc cụ thể hoặc là trong SA Kim Anh ở trong SA ra thì Kim Anh mô tả rất dễ ví dụ như là trong SA thì có CNB rồi nó có tức là về thù lao lương bổng phúc lợi rồi nó có tuyển dụng thì từng năng lực như vậy nó sẽ`
  - truth: `Cái cái công việc nhỏ đó nó gọi là năng lực của từng công việc cụ thể, hoặc là trong HR khi mà nó trong HR ra thì Khanh mô tả rất dễ. Ví dụ như là trong HR thì có C&B, rồi nó có tức là về thù lao, lương bổng, phúc lợi, rồi nó có tuyển dụng, thì từng năng lực như vậy nó sẽ...`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=27
  - raw: `NĂM NĂNG LỰC CỐT LÕI TÔI CÓ NĂM NĂNG LỰC VỀ CHUYÊN MÔN VÀ TÔI CÓ NĂM NĂNG LỰC LÃNH ĐẠO NHƯ VẬY TÔI TUYỂN MỘT ANH QUẢN LÝ BÁN HÀNG CHỈ TRONG VÒNG MỘT TIẾNG TÔI PHẢI NGÓ TỚI MƯỜI LĂM CÁI NĂNG LỰC LIỆU RẰNG TÔI NGÓ KỊP KHÔNG`
  - corrected: `Năm năng lực cốt lõi tôi có năm năng lực về chuyên môn và tôi có năm năng lực lãnh đạo như vậy tôi tuyển một anh quản lý bán hàng chỉ trong vòng một tiếng tôi phải ngó tới mười lăm cái năng lực liệu rằng tôi ngó kịp không`
  - truth: `5 năng lực cốt lõi. Tôi có 5 năng lực về chuyên môn và tôi có 5 năng lực lãnh đạo, như vậy tôi tuyển 1 anh quản lý bán hàng, chỉ trong vòng 1 tiếng tôi phải ngó tới 15 cái năng lực, liệu rằng tôi ngó kịp không.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=29
  - raw: `VÀ CÁI NĂNG LỰC CỐT LÕI VỚI NĂNG LỰC LÃNH ĐẠO NÊN NÓ GỘP RA THÌ DO ĐÓ HỌ CHỈ CÒN NĂM NĂNG LỰC CHÍNH VÀ CÓ THỂ CÓ NHỮNG CÁI NĂNG LỰC CON ĐÓ VÀ CÁI CON SỐ NĂNG LỰC CON NÓ TỔNG CỘNG NÓ CHỈ CÓ MƯỜI THÔI CÒN CÁI NĂNG LỰC CHUYÊN MÔN LÀ NGƯỜI TA CHỈ HỎI VÀ TRONG QUÁ TRÌNH PHỎNG VẤN THÌ CÁI SỐ LƯỢNG MÀ HỎI VỀ`
  - corrected: `Và cái năng lực cốt lõi với năng lực lãnh đạo nên nó gộp ra thì do đó họ chỉ còn năm năng lực chính và có thể có những cái năng lực con đó và cái con số năng lực con nó tổng cộng nó chỉ có mười thôi còn cái năng lực chuyên môn là người ta chỉ hỏi và trong quá trình phỏng vấn thì cái số lượng mà hỏi về`
  - truth: `Và cái năng lực cốt lõi với năng lực lãnh đạo này nó gộp ra, thì do đó họ chỉ còn 5 năng lực chính, và có thể có những cái năng lực con đó, và cái con số năng lực con nó tổng cộng nó chỉ có 10 thôi, còn cái năng lực chuyên môn là người ta chỉ hỏi, và trong quá trình phỏng vấn thì cái số lượng mà hỏi về.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=30
  - raw: `VỀ CÁI NĂNG LỰC CHUYÊN MÔN THÌ ÍT NHƯNG NGƯỜI TA HỎI VỀ NĂNG LỰC LÃNH ĐẠO LÀ NHIỀU BỞI VÌ SAO NÓ QUAY TRỞ LẠI CÁI ĐỊNH NGHĨA LÚC BAN ĐẦU CỦA ÔNG NASA MANILA HỌ COI THỬ CÁI ÔNG QUẢN LÝ BÁN HÀNG NÀY NÈ TRONG ĐIỀU KIỆN KHÔNG CÓ GÌ HẾT ANH TA ĐÃ VƯỢT QUA NHƯ THẾ NÀO ANH TA ĐÃ DẪN DẮT ĐỘI NGŨ NHƯ THẾ NÀO THÌ ĐÓ LÀ`
  - corrected: `Về cái năng lực chuyên môn thì ít nhưng người ta hỏi về năng lực lãnh đạo là nhiều bởi vì sao nó quay trở lại cái định nghĩa lúc ban đầu của ông NASA Manila họ coi thử cái ông quản lý bán hàng này nè trong điều kiện không có gì hết anh ta đã vượt qua như thế nào anh ta đã dẫn dắt đội ngũ như thế nào thì đó là`
  - truth: `Về cái năng lực chuyên môn thì ít nhưng người ta hỏi về năng lực lãnh đạo là nhiều, bởi vì sao? Nó quay trở lại cái cái cái định nghĩa lúc ban đầu của ông Nelson Mandela. Họ coi thử cái ông quản lý bán hàng này nè, trong điều kiện không có gì hết, anh ta đã vượt qua như thế nào, anh ta đã dẫn dắt đội ngũ như thế nào, thì đó là—`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=31
  - raw: `CÁI ĐIỀU MÀ NGƯỜI TA CẦN XEM XÉT VÀ KIM ANH CHIA SẺ LUÔN LÀ VÍ DỤ NHƯ TRONG CÁC CÔNG TY MÀ KIM ANH ĐANG LÀM VIỆC VỚI HỌ TỪ HAI NGÀN MƯỜI BỐN TRỞ LẠI ĐÂY THÌ HỌ ĐỀU SỬ DỤNG CÁI NĂNG LỰC LÃNH ĐẠO LÀ CHÍNH CÒN CÁI NĂNG LỰC CHUYÊN MÔN THÌ NÓ CHỈ ĐƯỢC SỬ DỤNG`
  - corrected: `Cái điều mà người ta cần xem xét và Kim Anh chia sẻ luôn là ví dụ như trong các công ty mà Kim Anh đang làm việc với họ từ hai ngàn mười bốn trở lại đây thì họ đều sử dụng cái năng lực lãnh đạo là chính còn cái năng lực chuyên môn thì nó chỉ được sử dụng`
  - truth: `Cái điều mà người ta cần xem xét. Và Kim Anh chia sẻ luôn là, ví dụ như trong các cái công ty mà Kim Anh đang làm á, đang đang đang làm việc với họ từ 2014 trở lại đây á, thì họ đều sử dụng cái năng lực lãnh đạo là chính, còn cái năng lực chuyên môn thì nó để chỉ được sử dụng.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=32
  - raw: `TRONG QUÁ TRÌNH PHỎNG VẤN VÀ TRONG CÁI QUÁ TRÌNH MÀ ĐÁNH GIÁ NĂM ĐỂ HỌ XEM XÉT ĐỂ HỌ PHÁT TRIỂN CÁI NĂNG LỰC CHUYÊN MÔN CÒN NĂNG LỰC LÃNH ĐẠO LÀ CÁI MÀ BAO TRÙM ĐÁNH GIÁ TỪ CẤP THẤP CHO ĐẾN CẢ CẤP CAO THÌ`
  - corrected: `Trong quá trình phỏng vấn và trong cái quá trình mà đánh giá năm để họ xem xét để họ phát triển cái năng lực chuyên môn còn năng lực lãnh đạo là cái mà bao trùm đánh giá từ cấp thấp cho đến cả cấp cao thì`
  - truth: `Trong quá trình phỏng vấn và trong cái quá trình mà, ờ, đánh giá với Nam để họ xem xét, để họ phát triển cái năng lực chuyên môn. Còn năng lực lãnh đạo là cái mà bao trùm nó, đánh giá từ cấp thấp cho đến cả cấp cao, thì—`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=34
  - raw: `KHẢ NĂNG HUY ĐỘNG NGUỒN LỰC MỘT CÁCH THÍCH HỢP VẬY THÌ CÁI CHUYỆN KHẢ NĂNG NHÌN RA ĐƯỢC BẢN CHẤT THẬT CỦA SỰ VIỆC NÓ CẦN NGAY CẢ NGƯỜI NHÂN VIÊN CHỨ KHÔNG CỨ GÌ CÁI NGƯỜI Ở CẤP TRÊN VÍ DỤ NHÂN VIÊN BÁN HÀNG ĐÂY NGÀY MAI KIM ANH DẠY MỘT CÁI LỚP CHO MỘT CÁI ĐỘI NGŨ BÁN HÀNG`
  - corrected: `Khả năng huy động nguồn lực một cách thích hợp, vậy thì cái chuyện khả năng nhìn ra được bản chất thật của sự việc nó cần ngay cả người nhân viên chứ không cứ gì cái người ở cấp trên. Ví dụ nhân viên bán hàng đây, ngày mai Kim Anh dạy một cái lớp cho một cái đội ngũ bán hàng.`
  - truth: `Khả năng huy động nguồn lực một cách thích hợp. Vậy thì cái chuyện khả năng nhìn ra được bản chất thật của sự việc, nó cần ngay cả người nhân viên chứ không, không cứ gì cái người ở cấp trên. Ví dụ nhân viên bán hàng, đây, ngày mai Kim Anh dạy một cái lớp cho cho một cái đội ngũ bán hàng.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=35
  - raw: `THÌ MỘT TRONG NHỮNG THÁCH THỨC CỦA BẠN LÀ BẠN NÓI LÀ THEO CHỈ TIÊU BÁN HÀNG LÚC NÀO CŨNG CAO VÀ RẤT KHÓ ĐỂ ĐẠT THẾ THÌ CẬU NÀY ĐÃ NHÌN RA ĐƯỢC BẢN CHẤT THẬT CỦA SỰ VIỆC CHƯA CAO LÀ SO VỚI CÁI GÌ`
  - corrected: `Thì một trong những thách thức của bạn là bạn nói là theo chỉ tiêu bán hàng lúc nào cũng cao và rất khó để đạt thế thì cậu này đã nhìn ra được bản chất thật của sự việc chưa? Cao là so với cái gì?`
  - truth: `Thì một trong những thách thức của bạn là bạn nói là sale, chỉ tiêu bán hàng, lúc nào cũng cao và rất khó để đạt. Thế thì cậu này đã nhìn ra được bản chất thật của sự việc chưa, cao là so với cái gì?`
  - reason: ``

### FP1 Examples (top 3)

- video_id=01_tsKMxDpZV68 seg=28
  - raw: `LIỆU RẰNG TÔI NGÓ CÓ ỔN KHÔNG CHO NÊN DO ĐÓ MỘT SỐ CÔNG TY NGƯỜI TA ĐÃ TÍCH HỢP CÁI NĂNG LỰC CỐT LÕI NÀY VÀO TRONG CÁI NĂNG LỰC LÃNH ĐẠO NHƯ VẬY THÌ TỔNG SỐ NĂNG LỰC CỐT LÕI VỚI NĂNG LỰC LÃNH ĐẠO NÀY NÓ GỘP CHUNG LẠI`
  - corrected: `Liệu rằng tôi ngó kịp không cho nên do đó một số công ty người ta đã tích hợp cái năng lực cốt lõi này vào trong cái năng lực lãnh đạo như vậy thì tổng số năng lực cốt lõi với năng lực lãnh đạo này nó gộp chung lại`
  - truth: `Liệu rằng tôi ngó có ổn không, cho nên do đó một số công ty người ta đã tích hợp cái năng lực cốt lõi này vào trong cái năng lực lãnh đạo, như vậy thì tổng số năng lực cốt lõi với năng lực lãnh đạo này nó gộp chung lại.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=38
  - raw: `HỒI NÃY KIM ANH CÓ NÓI LÀ HỒI XƯA NGƯỜI TA NÓI KHUNG NĂNG LỰC LÀ TỪ ĐIỂN NĂNG LỰC VẬY THÌ TỪ ĐIỂN THÌ THƯỜNG THƯỜNG CHÚNG TA TRA LÀ CHÚNG TA ĐỀU THẤY CÁI TỪ Ý LÀ CÁI GÌ GIỐNG NHƯ HÔM QUA HÔM KIA CÓ MỘT BẠN NÓI THIỆT VỚI CÁC BẠN LÀ KIM ANH CŨNG ĐA ĐOAN NGOÀI CÁI CHUYỆN LÀ LÀM PHÓ CHỦ TỊCH CỦA CÂU LẠC BỘ NHÂN SỰ RA`
  - corrected: `Hồi nãy Kim Anh có nói là hồi xưa người ta nói khung năng lực là từ điển năng lực vậy thì từ điển thì thường chúng ta tra là chúng ta đều thấy cái từ ý là cái gì giống như hôm qua hôm kia có một bạn nói thiệt với các bạn là Kim Anh cũng đã đoan ngoài cái chuyện là làm phó chủ tịch của câu lạc bộ nhân sự ra`
  - truth: `Hồi nãy Kim Anh có nói là hồi xưa người ta nói khung năng lực là từ điển năng lực. Vậy thì từ điển, thì thường thường chúng ta tra là chúng ta đều thấy cái từ ý là cái gì, giống như hôm qua hôm kia có một bạn nói thiệt với các bạn là Kim Anh cũng đa đoan ngoài cái chuyện là làm Phó Chủ tịch của Câu lạc bộ Nhân sự ra.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=50
  - raw: `VÀ CÁI CÔNG TY ĐÓ ĐANG XÂY DỰNG NHỮNG NGƯỜI MÀ GỌI LÀ PHỤC VỤ CHO CÁI QUẦY BÁN THỊT BÁN CÁ ĐÓ THÌ CÁC BẠN MÔ TẢ NÓ QUÁ TỦNG MỦNG ĐI VÀ NÓ THIẾU CÁI BỨC TRANH TỔNG QUAN CỦA CÁI VỊ TRÍ ĐÓ CÓ NGHĨA LÀ GÌ`
  - corrected: `Và cái công ty đó đang xây dựng những người mà gọi là phục vụ cho cái quầy bán thịt bán cá đó thì các bạn mô tả nó quá tủi mủn đi và nó thiếu cái bức tranh tổng quan của cái vị trí đó có nghĩa là gì`
  - truth: `Và cái công ty đó đang xây dựng những người mà gọi là phục vụ cho cái quầy bán thịt bán cá đó, thì các bạn mô tả nó quá tủng mủng đi và nó thiếu cái bức tranh tổng quan của cái vị trí đó, có nghĩa là gì?`
  - reason: ``

### FP2 Examples (top 20)

- video_id=01_tsKMxDpZV68 seg=3
  - raw: `THƯỜNG SẼ CÓ NHỮNG KỸ NĂNG SAU ĐÂY MỘT PHÂN TÍCH SƠ Ý LÝ LỊCH CỦA ỨNG VIÊN HAI LÀ LẮNG NGHE CHỦ ĐỘNG BA LÀ ĐẶT CÂU HỎI BỐN LÀ GHI CHÉP VÀ NĂM LÀ PHÂN TÍCH VÀ ĐÁNH GIÁ ỨNG VIÊN THẾ THÌ ĐÂY LÀ DANH MỤC CỦA CÁC KỸ NĂNG CẦN CÓ CHO MỘT NGƯỜI PHỎNG VẤN TUYỂN CHỌN`
  - corrected: `Thường sẽ có những kỹ năng sau đây: một là phân tích sơ yếu lý lịch của ứng viên; hai là lắng nghe chủ động; ba là đặt câu hỏi; bốn là ghi chép; và năm là phân tích và đánh giá ứng viên. Thế thì đây là danh mục của các kỹ năng cần có cho một người phỏng vấn tuyển chọn.`
  - truth: `Thường sẽ có những kỹ năng sau đây: 1) phân tích sơ ý lý lịch của ứng viên, 2) là lắng nghe chủ động, 3) là đặt câu hỏi, 4) là ghi chép, và 5) là phân tích và đánh giá ứng viên. Vậy thì đây là danh mục của các kỹ năng cần có cho một người phỏng vấn tuyển chọn.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=6
  - raw: `NÓ MÔ TẢ HÀNH VI CỦA NHỮNG KỸ NĂNG NÀO Ở ĐÂY Ạ XIN MỜI CÁC BẠN CHIA SẺ QUA TRẮC BÓC CÁC BẠN NHÌN CÁI B LÀ CÁI MÔ TẢ HÀNH VI MÌNH ĐỐI CHIẾU LẠI BÊN CÁI BẢNG A THÌ CÁC BẠN THẤY NÓ ĐANG MÔ TẢ HÀNH VI CỦA NHỮNG KỸ NĂNG NÀO XIN MỜI CÁC BẠN CHỊ THẤY HÀ MY SPA`
  - corrected: `Nó mô tả hành vi của những kỹ năng nào ở đây ạ? Xin mời các bạn chia sẻ qua trắc böc. Các bạn nhìn cái B là cái mô tả hành vi mình đối chiếu lại bên cái bảng A thì các bạn thấy nó đang mô tả hành vi của những kỹ năng nào? Xin mời các bạn chị thấy Hà My spa.`
  - truth: `Nó mô tả hành vi của những kỹ năng nào ở đây ạ? Xin mời các bạn chia sẻ qua chat box ạ. Các bạn nhìn cái B là cái mô tả hành vi, mình nối chiếu lại bên cái bảng A thì các bạn thấy nó đang mô tả hành vi của những kỹ năng nào, xin mời các bạn. Ờ, chị thấy Hà Mi Spa.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=8
  - raw: `MÌNH ĐANG MÔ TẢ HÀNH VI CỦA NGƯỜI NÀY VỀ KỸ NĂNG NGHE RỒI BẠN CAM TRẦN HAY LÀ CẨM TRẦN KIM ANH SORRY LÀ KHÔNG CÓ BIẾT LÀ ĐỌC ĐƯỢC CÁI TÊN CÁC BẠN CÓ ĐÚNG KHÔNG THÌ BẠN CÓ MÔ TẢ LÀ MÔ TẢ ĐƯỢC LẮNG NGHE CHỦ ĐỘNG PHÂN TÍCH VÀ ĐÁNH GIÁ ỨNG VIÊN`
  - corrected: `Mình đang mô tả hành vi của người này về kỹ năng nghe rồi bạn cam kết hay là cấm trần Kim Anh sorry là không có biết là đọc được cái tên các bạn có đúng không thì bạn có mô tả là mô tả được lắng nghe chủ động phân tích và đánh giá ứng viên`
  - truth: `Mình đang mô tả hành vi của người này về kỹ năng nghe, rồi à bạn à... Cam Trần hay là Cảnh Trần, cái— nhưng mà anh sorry là cái không, không có biết là đọc được cái tên các bạn có đúng không. Thì bạn có mô tả là mô tả được lắng nghe chủ động phân tích và đánh giá ứng viên.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=11
  - raw: `RỒI NHẰM NHẰM ĐỂ LÀM GÌ NHẰM ĐỂ THĂM DÒ PHÁN ĐOÁN NHƯ VẬY LÀ NẾU MÀ ĐẶT CÂU HỎI THEO CỐT TRÚC PHỄU MÀ LẠI KHÔNG THĂM DÒ ĐƯỢC KHÔNG PHÁN ĐOÁN ĐƯỢC THÌ NHƯ VẬY NÓ CHƯA CÓ ĐẠT YÊU CẦU MỘT NGƯỜI CÓ NĂNG LỰC PHỎNG VẤN TUYỂN CHỌN THÌ ĐÓ LÀ MỘT CÁI VÍ DỤ ĐỂ CÁC BẠN CÓ THỂ HÌNH DUNG ĐƯỢC THẾ NÀO LÀ NĂNG LỰC`
  - corrected: `Rồi nhằm nhằm để làm gì? Nhằm để thăm dò phán đoán như vậy là nếu mà đặt câu hỏi theo cấu trúc phễu mà lại không thăm dò được, không phán đoán được thì như vậy nó chưa có đạt yêu cầu một người có năng lực phỏng vấn tuyển chọn thì đó là một cái ví dụ để các bạn có thể hình dung được thế nào là năng lực`
  - truth: `Rồi nhầm, nhầm để làm cái gì? Nhầm để thăm dò, phán đoán. Như vậy là nếu mà đặt câu hỏi theo cấu trúc phễu mà lại không thăm dò được, không phán đoán được, thì như vậy nó chưa có đạt yêu cầu chỗ một người có năng lực phỏng vấn tuyển chọn. Thì đó là một cái ví dụ để các bạn có thể, ờ, hình dung được thế nào là năng lực.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=21
  - raw: `PHÒNG SALE THÌ SẼ CÓ CELL APPIN RỒI CŨNG CÓ NGƯỜI LÀ SALE VÍ DỤ NHƯ BÊN DƯỢC THÌ NÓ CÓ LÀ SALE BÁN CHO ETICAL TỨC LÀ BÁN CHO BỆNH VIỆN RỒI CÁI NGƯỜI MÀ BÁN SALE CHO BÊN`
  - corrected: `Phòng sale thì sẽ có cell appin rồi cũng có người là sale ví dụ như bên dược thì nó có là sale bán cho ethical tức là bán cho bệnh viện rồi cái người mà bán sale cho bên`
  - truth: `Phòng sale thì sẽ có, ờ, sale admin, rồi cũng có người là sale. Ví dụ như bên dược á thì nó có là sale bán cho ethical, tức là bán cho bệnh viện, rồi cái người mà bán sale cho bên—`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=22
  - raw: `CÔNG TY BÊN GÌ ĐÓ BÊN CÁC NHÀ THUỐC THÌ KỸ NĂNG ĐÓ SẼ KHÁC NĂNG LỰC NÓ SẼ KHÁC NÓ MÔ TẢ HOẶC LÀ TRONG KẾ TOÁN THÌ SẼ CÓ NGƯỜI KẾ TOÁN TỔNG HỢP CÓ KẾ TOÁN THU CÓ KẾ TOÁN CHI RỒI THỦ QUỸ THÌ TỪNG CÁI`
  - corrected: `Công ty bên dược phẩm hay bên các nhà thuốc thì kỹ năng đó sẽ khác năng lực nó sẽ khác nó mô tả hoặc là trong kế toán thì sẽ có người kế toán tổng hợp có kế toán thu có kế toán chi rồi thủ quỹ thì từng cái`
  - truth: `Công ty bên gì đó, bên các cái nhà thuốc, thì kỹ năng của nó sẽ khác, năng lực nó sẽ khác, nó mô tả. Hoặc là trong kế toán thì sẽ có người kế toán tổng hợp, có kế toán thu, có kế toán chi, rồi thủ quỹ, thì từng cái...`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=24
  - raw: `CỤ THỂ QUY ĐỊNH CỤ THỂ HƠN NHƯNG BAO TRÙM CỦA TẤT CẢ CÁI NÀY QUAN TRỌNG NHẤT ĐÓ LÀ NĂNG LỰC LÃNH ĐẠO THÌ KIM ANH DỪNG Ở ĐÂY ĐỂ KIM ANH CHIA SẺ VỀ CÁI LỊCH SỬ CỦA KHUNG NĂNG LỰC TÍ XÍU NGÀY XƯA ĐÓ THÌ NĂM MỘT NGÀN CHÍN TRĂM CHÍN MƯƠI HAI LÀ CÁI NĂM MÀ`
  - corrected: `Cụ thể quy định cụ thể hơn nhưng bao trùm của tất cả cái này quan trọng nhất đó là năng lực lãnh đạo thì Kim Anh dừng ở đây để Kim Anh chia sẻ về cái lịch sử của khung năng lực tí xíu ngày xưa đó thì là năm một ngàn chín trăm chín mươi hai là cái năm mà`
  - truth: `Cụ thể, quy định cụ thể hơn. Nhưng bao trùm của tất cả cái này quan trọng nhất đó là năng lực lãnh đạo. Thì Kim Anh dừng ở đây để Kim Anh chia sẻ về cái lịch sử của khung năng lực một tí xíu. Ngày xưa đó, thì năm 1992 là cái năm mà.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=25
  - raw: `CÁI TÁC GIẢ MÀ XÂY DỰNG KHUNG NĂNG LỰC LÀ ỔNG ĐƯA RA LÀ CÓ BA NHÓM NĂNG LỰC NĂNG LỰC THỨ NHẤT LÀ NĂNG LỰC CỐT LÕI LÀ CÁI NÀY ĐÂY LÀ ÁP DỤNG CHO TẤT CẢ NHÂN VIÊN NĂNG LỰC THỨ HAI LÀ NĂNG LỰC CHUYÊN MÔN LÀ ÁP DỤNG CHO TỪNG NHÓM CÔNG VIỆC VÀ TỪNG CÔNG VIỆC CỤ THỂ VÀ NĂNG LỰC THỨ BA ỔNG GỌI LÀ NĂNG LỰC QUẢN LÝ`
  - corrected: `Cái tác giả mà xây dựng khung năng lực là ông đưa ra là có ba nhóm năng lực: năng lực thứ nhất là năng lực cốt lõi là cái này đây là áp dụng cho tất cả nhân viên; năng lực thứ hai là năng lực chuyên môn là áp dụng cho từng nhóm công việc và từng công việc cụ thể; và năng lực thứ ba ông gọi là năng lực quản lý.`
  - truth: `Cái tác giả mà xây dựng cung năng lực là ổng đưa ra là có 3 nhóm năng lực. Năng lực thứ nhất là năng lực cốt lõi, là cái này đây là áp dụng cho tất cả nhân viên. Năng lực thứ hai là năng lực chuyên môn, là áp dụng cho từng nhóm công việc và từng công việc cụ thể. Và năng lực thứ ba ổng gọi là năng lực quản lý.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=33
  - raw: `KIM ANH DỪNG Ở ĐÂY ĐỂ GIẢI THÍCH TẠI SAO LÀ NĂNG LỰC LÃNH ĐẠO LẠI ĐƯỢC SỬ DỤNG CHO TẤT CẢ CÁC CẤP BỞI VÌ CÁC BẠN NGÓ THEO ĐỊNH NGHĨA CỦA ÔNG NOEL MTG ỔNG NÓI LÀ NĂNG LỰC KHẢ NĂNG LÃNH ĐẠO LÀ KHẢ NĂNG NHÌN RA ĐƯỢC BẢN CHẤT THẬT CỦA SỰ VIỆC VÀ`
  - corrected: `Kim Anh dừng ở đây để giải thích tại sao là năng lực lãnh đạo lại được sử dụng cho tất cả các cấp bởi vì các bạn ngỏ theo định nghĩa của ông Noel MTG ông nói là năng lực khả năng lãnh đạo là khả năng nhìn ra được bản chất thật của sự việc và`
  - truth: `Ờ, Kim Anh dừng ở đây để giải thích tại sao năng lực lãnh đạo lại được sử dụng cho tất cả các cấp, bởi vì các bạn ngó theo định nghĩa của ông Noel MTC, ổng nói là: năng lực, khả năng lãnh đạo là khả năng nhìn ra được bản chất thật của sự việc, và—`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=36
  - raw: `BẠN CHỈ SO LÀ CAO SO VỚI CHỈ TIÊU NĂM TRƯỚC CÒN SO TIỀM NĂNG CỦA THỊ TRƯỜNG THÌ BẠN CHƯA THẤY CHO NÊN BẠN KHÔNG THẤY RA ĐƯỢC BẢN CHẤT THẬT CỦA SỰ VIỆC VÀ ĐÓ LÀ CÁI ĐIỀU MÀ MÌNH ĐANG NÓI ĐÂY LÀ NĂNG LỰC CHỦ ĐẠO PHẢI CHÚ TRỌNG TỪ CẤP THẤP ĐẾN CẢ CẤP CAO NHƯNG`
  - corrected: `Bạn chỉ số là cao so với chỉ tiêu năm trước còn số tiềm năng của thị trường thì bạn chưa thấy cho nên bạn không thấy ra được bản chất thật của sự việc và đó là cái điều mà mình đang nói đây là năng lực chủ đạo phải chú trọng từ cấp thấp đến cả cấp cao nhưng`
  - truth: `Bạn chỉ so là cao so với chỉ tiêu năm trước, còn so tiềm năng của thị trường thì bạn chưa thấy, cho nên bạn không thấy ra được cái bản chất thật của sự việc. Và đó là cái điệu, cái điều mà mình đang nói đây là năng lực lãnh đạo phải chú trọng từ cấp thấp đến cả cấp cao, nhưng—`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=39
  - raw: `THÌ KIM ANH CÒN HỖ TRỢ CHO CÁC BẠN KHUYẾT TẬT TRONG ĐÓ CÓ MỘT CÔ BÉ LÀ BỊ KHIẾM THỊ VÀ NÓ LÀ LÚC ĐẦU NÓ SỬ DỤNG KIM ANH LÀ MENTOR NHƯNG NHƯNG BÂY GIỜ LÀ KIM ANH RẤT LÀ THÍCH NÓI CHUYỆN VỚI NÓ TẠI VÌ NÓ GIÚP CHO MÌNH GỢI MỞ RA NHÌN THÊM NHIỀU CÁI THÌ HÔM QUA BẠN CÓ HỎI TÔI MỘT CÂU LÀ CHỊ ƠI NGƯỜI TA NÓI NẮM THỚP`
  - corrected: `Thì Kim Anh còn hỗ trợ cho các bạn khuyết tật trong đó có một cô bé là bị khiếm thị và nó là lúc đầu nó sử dụng Kim Anh là mentor nhưng nhưng bây giờ là Kim Anh rất là thích nói chuyện với nó tại vì nó giúp cho mình gợi mở ra nhìn thêm nhiều cái thì hôm qua bạn có hỏi tôi một câu là chị ơi người ta nói nắm thóp`
  - truth: `Thì Kim Anh còn hỗ trợ cho các bạn khuyết tật, trong đó có một cô bé là bị khiếm thị, và nó là lúc đầu á nó nó sử dụng Kim Anh là mentor, nhưng nhưng bây giờ á là Kim Anh rất là thích nói chuyện với nó tại vì nó giúp cho mình gợi mở ra nhìn thêm nhiều cái. Thì hôm qua bạn có hỏi tôi một câu là: "Chị ơi, người ta nói nắm thóp."`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=45
  - raw: `ĐƯỢC VÀ THỨ HAI CỤ THỂ LÀ GÌ HÀNH VI MÔ TẢ LÀ HÀNH VI THẤY ĐƯỢC CÒN NẾU MÔ TẢ THEO KIỂU LÀ BẠN PHẢI HIỂU CÁI CHỮ HIỂU NÀY NÓ KHÔNG PHẢI LÀ ĐỘNG TỪ CHỈ HÀNH ĐỘNG CHO NÊN DO ĐÓ ĐÓ LÀ ĐIỂM CHƯA CÓ RÕ`
  - corrected: `Được và thứ hai cụ thể là gì? Hành vi mô tả là hành vi thấy được, còn nếu mô tả theo kiểu là bạn phải hiểu cái chữ hiểu này nó không phải là động từ chỉ hành động cho nên do đó là điểm chưa rõ.`
  - truth: `Không sale được. Và thứ hai, cụ thể là gì? Hành vi mô tả là hành vi thấy được, còn nếu mô tả theo kiểu là "bạn phải hiểu", cái chữ "hiểu" này nó không phải là động từ chỉ hành động, cho nên do đó đó là điểm chưa có rõ.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=46
  - raw: `RỒI THỨ BA LÀ MÌNH BIẾT HÀNH VI NÓ PHẢI RÕ VÀ DỄ HIỂU VÍ DỤ NHƯ CHÚNG TA THƯỜNG HAY CÓ THÓI QUEN LÀ VÍ DỤ NHƯ VẦY MỘT TRONG NHỮNG YÊU CẦU CỦA NGƯỜI LÀM QUẢN LÝ LÀ MÌNH NÓI LÀ PHẢI BIẾT ẤN ĐỊNH MỤC TIÊU MARX`
  - corrected: `Rồi thứ ba là mình biết hành vi nó phải rõ và dễ hiểu ví dụ như chúng ta thường hay có thói quen là ví dụ như vầy một trong những yêu cầu của người làm quản lý là mình nói là phải biết ấn định mục tiêu SMART`
  - truth: `Rồi, thứ ba là mình viết hành vi nó phải rõ và dễ hiểu. Ví dụ như chúng ta thường hay có thói quen là, ví dụ như vầy, ờ, một trong những yêu cầu của người làm quản lý là mình nói là phải biết ấn định mục tiêu SMART.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=48
  - raw: `NGƯỜI CẤP TRƯỞNG NGƯỜI CẤP QUẢN LÝ XÁC ĐỊNH ĐƯỢC MỤC TIÊU CÓ THỂ ĐO LƯỜNG ĐƯỢC VÀ XÁC ĐỊNH ĐƯỢC CÁI TẠO ĐIỀU KIỆN ĐỂ CHO NGƯỜI NHÂN VIÊN NÀY NÓ THÁCH THỨC ĐỂ NÓ VƯƠN LÊN VÀ NÓ PHẤN ĐẤU VÍ DỤ NHƯ VẬY THÌ ĐÓ LÀ CÁI ĐIỂM THỨ BA ĐIỂM THỨ TƯ NÓ MANG TÍNH TOÀN DIỆN TOÀN DIỆN NGHĨA LÀ SAO`
  - corrected: `Người cấp trên người cấp quản lý xác định được mục tiêu có thể đo lường được và xác định được cái tạo điều kiện để cho người nhân viên này nó thách thức để nó vươn lên và nó phấn đấu ví dụ như vậy thì đó là cái điểm thứ ba điểm thứ tư nó mang tính toàn diện toàn diện nghĩa là sao`
  - truth: `Ờ, cái người cấp trưởng, người cấp quản lý xác định được mục tiêu, có thể đo lường được, và xác định được cái tạo điều kiện để cho người nhân viên này nó thách thức, để nó vươn lên và nó phấn đấu, ví dụ như vậy. Thì đó là cái điểm thứ ba. Điểm thứ tư nó mang tính toàn diện, toàn diện nghĩa là sao?`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=49
  - raw: `CÓ RẤT NHIỀU CÔNG TY KIM ANH VÀO THÌ KIM ANH THẤY LÀ CÁC BẠN BỊ VƯỚNG VÀO CÁI CHỖ LÀ CÓ XÂY NĂNG LỰC ĐÓ NHƯNG MÀ NÓ HƠI BỊ TỦNG MỦN LẤY VÍ DỤ CÓ MỘT LẦN KIM ANH VÔ MỘT CÁI CÔNG TY ĐÓ LÀ CÔNG TY VỀ SIÊU THỊ`
  - corrected: `CÓ RẤT NHIỀU CÔNG TY Kim Anh vào thì Kim Anh thấy là các bạn bị vướng vào cái chỗ là có xây năng lực đó nhưng mà nó hơi bị vụn vặt lấy ví dụ có một lần Kim Anh vô một cái công ty đó là công ty về siêu thị`
  - truth: `Ờ, có rất nhiều công ty Kim Anh vào thì Kim Anh thấy là các bạn bị vướng vào cái chỗ là có xây năng lực đó nhưng mà nó hơi bị tủng mủng. Lấy ví dụ, có một lần Kim Anh vô một cái, a, cái công ty đó là cái công ty về, à, về siêu thị.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=51
  - raw: `NGƯỜI TA THƯỜNG MÔ TẢ CÁI KHUNG NĂNG LỰC VÀ NGƯỜI TA NHẮM TỚI CÁI KẾT QUẢ CUỐI CÙNG CỦA VỊ TRÍ ĐÓ CẦN TẠO RA LÀ CÁI GÌ CŨNG GIỐNG NHƯ HỒI NÃY KIM ANH CHIẾU CHO CÁC BẠN LÀ CHUYỆN PHỎNG VẤN LÀ NHẮM ĐẾN CHUYỆN LÀ TÔI TÌM RA ĐƯỢC ỨNG VIÊN NÀY NÓ CÓ ĐẠT VỚI YÊU CẦU CỦA MÌNH HAY KHÔNG ĐÓ LÀ KẾT QUẢ CUỐI CÙNG NHƯNG`
  - corrected: `Người ta thường mô tả cái khung năng lực và người ta nhắm tới cái kết quả cuối cùng của vị trí đó cần tạo ra là cái gì cũng giống như hồi nãy Kim Anh chiếu cho các bạn là chuyện phỏng vấn là nhằm đến chuyện là tôi tìm ra được ứng viên này nó có đạt với yêu cầu của mình hay không đó là kết quả cuối cùng nhưng`
  - truth: `Người ta thường mô tả cái khung năng lực là người ta nhắm tới cái kết quả cuối cùng của vị trí đó cần tạo ra là cái gì. Cũng giống như hồi nãy Kim Anh chiếu cho các bạn, là chuyện phỏng vấn là nhắm đến chuyện là "tôi tìm ra được ứng viên này nó có đạt với yêu cầu của mình hay không". Đó là kết quả cuối cùng, nhưng—`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=53
  - raw: `ĐIỂM KẾ TIẾP LÀ NÓ PHẢI TÍCH HỢP ĐƯỢC CÁC TIẾN TRÌNH QUẢN TRỊ NGUỒN NHÂN LỰC CÓ NGHĨA LÀ GÌ KHUNG NĂNG LỰC CÁC BẠN CÓ ĐÓ KHI KÊNH ĐI VÀO TƯ VẤN CÁC BẠN NÓI CÁC BẠN CO NĂNG LỰC PHẢI KHÔNG RỒI OK CHO TÔI XEM ĐIỂM THỨ NHẤT LÀ KHUNG NĂNG LỰC NÀY CÓ MÔ TẢ ĐƯỢC LÀ NẾU NGƯỜI NHÂN VIÊN NÀY`
  - corrected: `Điểm tiếp theo là nó phải tích hợp được các tiến trình quản trị nguồn nhân lực, có nghĩa là gì? Khung năng lực các bạn có đó khi kênh đi vào tư vấn, các bạn nói các bạn có năng lực phải không? Rồi ok cho tôi xem điểm thứ nhất là khung năng lực này có mô tả được là nếu người nhân viên này`
  - truth: `Điểm kế tiếp là nó phải tích hợp được các tiến trình quản trị nguồn nhân lực, có nghĩa là gì? Khung năng lực các bạn có đó, khi cái ban đầu đi vào tư vấn á, các bạn nói các bạn có có khung năng lực phải không? Rồi ok cho tôi xem, điểm thứ nhất là khung năng lực này có mô tả được là nếu người nhân viên này.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=54
  - raw: `CHUẨN BỊ ĐƯỢC CẤT NHẮC LÊN MỘT VỊ TRÍ CAO HƠN THÌ CÁI THANG NẤC CAO HƠN LÀ CAO HƠN Ở CHỖ NÀO CHỈ CHO TÔI XEM RỒI ĐỂ KẾ TIẾP BÂY GIỜ BẠN NÀY`
  - corrected: `Chuẩn bị được cất nhắc lên một vị trí cao hơn thì cái thang năng lực cao hơn là cao hơn ở chỗ nào? Chỉ cho tôi xem rồi để kế tiếp bây giờ bạn này`
  - truth: `Và chuẩn bị được cất nhắc lên một cái cái vị trí cao hơn thì cái thang nất cao hơn là cao hơn ở chỗ nào chỉ cho tôi xem, rồi là thấy thấy bị lúng túng, rồi để kế tiếp. Bây giờ bạn này á.`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=55
  - raw: `TRONG CÁC BẠN NÀY CÙNG MỘT NĂM RA TRƯỜNG CÙNG LÀM VỊ TRÍ SELF NÀY NHƯNG TẠI SAO CÁI NGƯỜI NÀY ĐƯỢC CAO HƠN CHỈ CHO TÔI COI CÁI NĂNG LỰC CỦA NGƯỜI NÀY NÓ CAO HƠN NGƯỜI KIA Ở CHỖ NÀO THÌ LẠI THIẾU CÁI CHUYỆN MÀ`
  - corrected: `Trong các bạn này cùng một năm ra trường cùng làm vị trí sale này nhưng tại sao cái người này được cao hơn chỉ cho tôi coi cái năng lực của người này nó cao hơn người kia ở chỗ nào thì lại thiếu cái chuyện mà`
  - truth: `Trong, trong các bạn này cùng một năm ra trường nè, cùng làm vị trí sales hết nè, nhưng tại sao cái người này được cao hơn, chỉ giùm cho tôi coi cái năng lực của người này nó cao hơn người kia ở chỗ nào, thì lại thiếu cái chuyện mà...`
  - reason: ``
- video_id=01_tsKMxDpZV68 seg=57
  - raw: `RỒI MỘT ĐIỂM NỮA ĐÓ LÀ MỘT SỐ CÔNG TY XÂY DỰNG KHUNG NĂNG LỰC LÃNH ĐẠO NHƯNG MÀ CÁC TRƯỞNG VÍ DỤ NHƯ CEO RẤT LÀ BẬN VÍ DỤ NHƯ LÀ CÁC TRƯỞNG KHỐI PHÒNG BAN ĐỀU BẬN VÀ KHÔNG AI PHỎNG VẤN ĐƯỢC HỌ HẾT VÀ KHÔNG AI ĐƯỢC PHỎNG VẤN THÌ RỐT CUỘC CÁI KHUNG NĂNG LỰC HÌNH THÀNH RA LÀ TỰ CÁC BẠN NGHĨ TỰ CÁC BẠN ĐỌC TRÊN INTERNET VÀ NÓ RA CÁI KHUNG NĂNG LỰC ĐÓ NHƯNG MÀ LIỆU RẰNG CÓ ÁP DỤNG ĐƯỢC HAY KHÔNG NÓ CÓ SÁT SƯỜN VỚI CÁI NGƯỜI KIA THÌ KHÔNG CÓ THÌ ĐÓ LÀ ĐIỂM THỨ SÁU MÀ THƯỜNG HAY BỊ HỎNG`
  - corrected: `Rồi một điểm nữa đó là một số công ty xây dựng khung năng lực lãnh đạo nhưng mà các trưởng ví dụ như CEO rất là bận ví dụ như là các trưởng khối phòng ban đều bận và không ai phỏng vấn được họ hết và không ai được phỏng vấn thì rốt cuộc cái khung năng lực hình thành ra là tự các bạn nghĩ tự các bạn đọc trên internet và nó ra cái khung năng lực đó nhưng mà liệu rằng có áp dụng được hay không nó có sát sườn với cái người kia thì không có thì đó là điểm thứ sáu mà thường hay bị hổng`
  - truth: `Rồi, một điểm nữa đó là: một số công ty á xây dựng khung năng lực lãnh đạo, nhưng mà cấp trưởng, ví dụ như CEO, rất là bận, ví dụ như là... cấp trưởng khối phòng ban đều bận, và không ai phỏng vấn được họ hết. Và không ai được phỏng vấn thì rốt cuộc cái khung năng lực hình thành ra là tự các bạn nghĩ, tự các bạn đọc trên internet, và nó ra cái khung năng lực đó nhưng mà liệu rằng có áp dụng được hay không, nó có sát sườn với cái người kia thì không có. Thì đó là điểm thứ 6 mà thường hay bị hỏng.`
  - reason: ``

## Conclusion

- WER improved: yes.
- CER improved: yes.
- Go/no-go for summary eval phase 2: GO.