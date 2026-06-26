# QMSum SS-DST Evaluation Report

## Data source

- Dataset: HuggingFace `pszemraj/qmsum-cleaned`
- Original benchmark: QMSum meeting summarization
- Split: `train`
- Example id: `tr-gq-1006`
- Query: `Summarize the whole meeting.`
- Input token count from dataset: `1746`
- Gold output token count from dataset: `135`
- Parsed utterances: `105`

This is real QMSum data, not synthetic and not mocked. The selected example is a whole-meeting query, which best matches the generic recap behavior of the app.

## Fairness note

QMSum gold summaries are English. The app's production prompts ask for Vietnamese output, so ROUGE against QMSum would be invalid if we used production Vietnamese prompts. For this benchmark only, both `hierarchical` and `ssdst` are run with equivalent English prompts. The data and gold labels remain unchanged.

## ROUGE results (F1)

| Method | ROUGE-1 | ROUGE-2 | ROUGE-L |
|---|---:|---:|---:|
| hierarchical | 0.0273 | 0.0025 | 0.0149 |
| ssdst recap-only | 0.0347 | 0.0041 | 0.0184 |
| ssdst + structured state | 0.0378 | 0.004 | 0.0219 |

## Cost

| Method | LLM runs | Wall seconds | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| hierarchical | 16 | 43.96 | 21780 | 1300 |
| ssdst | 30 | 66.11 | 39487 | 2940 |

## Interpretation

- This benchmark is stricter and more standard than the earlier synthetic SS-DST proof-of-concept.
- Because QMSum is query-focused while the app methods are generic recap methods, ROUGE is informative but not a perfect task match.
- The `ssdst + structured state` row shows whether SS-DST's additional structured decisions/actions/entities help align with the gold summary when exposed as output text.
- Cost must be reported alongside quality because SS-DST adds state-update calls and usually increases latency/tokens.

## Gold summary

```text
The meeting was mainly about the exchange of the preliminary ideas about a new TV remote control project and subsequent task assignment. The project manager first set a target of making a fifty million Euros'profit from the project, with the unit price of twenty-five Euros. Afterwards, the team raised different opinions about features of the new remote controls and related questions about market potential. Among all the features, having a good look and size was unanimously considered to be the most essential. In the end, Marketing was assigned to investigate market competition and design, and User Interface thinking about shapes, colours and other attributes which would attract customers.
```

## Generated summaries

### hierarchical

```text
Thảo luận về thiết kế và định giá remote điều khiển
Đội ngũ thảo luận ý tưởng cho remote điều khiển độc đáo với chức năng whistle, màu sắc khác biệt và cân đối giữa kích thước gọn nhẹ lẫn khả năng cầm nắm dễ dàng.
Đoạn hội thoại thảo luận về lợi nhuận năm mươi triệu Euro và thiết kế điều khiển từ xa theo xu hướng thời trang.
Các bên thảo luận về việc bán sản phẩm dạng 'một cho tất cả' và nhận định rằng để đạt giá hai mươi lăm, cần có nhiều tính năng độc đáo.
Các bên thảo luận về chi phí và thiết kế của bộ điều khiển từ xa, với ý kiến ban đầu là màu xám hoặc đen nhưng có đề xuất cân nhắc thêm các màu sắc khác.
Đội ngũ đang thảo luận về ý tưởng thiết kế khóa hình tròn có thể phát âm để tránh thất lạc, đồng thời Marketing nhấn mạnh cần đánh giá tiềm năng thị trường và cạnh tranh trước khi xác định chi phí.
Đội Marketing nhấn mạnh yêu cầu về thiết kế và tính dễ sử dụng của remote control so với các sản phẩm thị trường, đặc biệt khi người dùng thao tác cùng TV hoặc máy chơi game. Các thành viên khác đồng ý.
Các bên đang thảo luận về kích thước phù hợp cho một sản phẩm cụ thể.
Thiết kế viên công nghiệp lo ngại việc thêm nhiều nút bấm vào remote sẽ khiến thiết bị trở nên cồng kềnh, trong khi giải pháp thu nhỏ lại có thể dẫn đến nguy cơ mất mát.
Các bên đang thảo luận về việc mất dữ liệu và đề xuất giải pháp dạng PDA cầm tay.
Thảo luận thiết kế remote điều khiển
Quản lý dự án yêu cầu nhóm nghiên cứu hình dáng, màu sắc và vật liệu làm từ cho remote điều khiển cạnh tranh.
Các bên đang thảo luận về chi phí và giao diện màn hình, đồng thời thông báo sẽ có cuộc họp tiếp theo trong vòng nửa giờ.
Quản lý dự án yêu cầu các thành viên nghiên cứu hình dáng, màu sắc và vật liệu để thiết kế sản phẩm hấp dẫn.
Các bên tham gia thảo luận về việc xem xét đối thủ cạnh tranh và thiết kế.
Không có nội dung rõ ràng trong các đoạn hội thoại của chunk này.
Các bên thảo luận về cảnh báo cho các cuộc họp tiếp theo, đánh giá lại tính hữu ích của dữ liệu và chuyển hướng sang lĩnh vực điện tử.
```

### ssdst recap-only

```text
Thảo luận về thiết kế và định giá remote điều khiển
Đội ngũ thảo luận ý tưởng cho remote điều khiển độc đáo với chức năng whistle, màu sắc khác biệt và cân đối giữa kích thước gọn nhẹ lẫn khả năng cầm nắm dễ dàng.
Dự án có mục tiêu lợi nhuận năm mươi triệu Euro và thiết kế phải rất thời thượng. Thiết bị điều khiển từ xa hiện tại khá cơ bản.
Đội ngũ thảo luận về việc sử dụng thiết bị điều khiển từ xa dạng 'một cho tất cả' (one for all) phù hợp với mục tiêu năm mươi triệu Euro và yêu cầu thiết kế thời thượng. Để bán sản phẩm ở mức giá hai mươi lăm, cần tích hợp nhiều tính năng độc đáo.
Người dùng giao diện đề xuất thiết bị điều khiển từ xa có thể sử dụng màu sắc thay vì chỉ xám hoặc đen, dựa trên giá hai mươi lăm Euro và tính năng đi kèm T_V.
Đề xuất thêm tính năng độc đáo như chuông báo khi mất thiết bị điều khiển từ xa để phân biệt với các sản phẩm khác. Marketing nhấn mạnh cần đánh giá tiềm năng thị trường và so sánh giá cả cạnh tranh trước khi quyết định chi phí.
Marketing đề cập đến việc cần so sánh tính năng độc đáo và độ phức tạp của thiết bị điều khiển từ xa với các sản phẩm khác trên thị trường trước khi quyết định dự án. Nhóm nhấn mạnh tầm quan trọng của giao diện người dùng đẹp mắt để thu hút sự tương tác, đặc biệt là trong bối cảnh giải trí như xem phim hoặc chơi game.
Các bên xác nhận việc so sánh tính năng độc đáo và độ phức tạp của thiết bị điều khiển từ xa với thị trường, đồng thời thảo luận về kích thước phù hợp cho giao diện người dùng.
Thiết bị điều khiển từ xa có thể trở nên cồng kềnh khi thêm nhiều nút bấm, hoặc quá nhỏ dễ thất lạc.
User Interface đề xuất thiết bị điều khiển từ xa có thể mang tính cầm tay (hand held) giống như P_D_A, trong khi Project Manager đồng ý.
Thảo luận thiết kế remote điều khiển
Quản lý dự án yêu cầu nhóm nghiên cứu hình dáng, màu sắc và vật liệu làm từ cho remote điều khiển cạnh tranh.
Quản lý dự án nhắc lại mục tiêu giá thành là mười hai euro năm mươi, trong khi giao diện người dùng đang phân vân về thiết kế màn hình P_D_A_. Họ thông báo sẽ có cuộc họp khác vào nửa giờ sau.
Quản lý dự án yêu cầu thiết kế viên xem xét hình dạng, màu sắc và vật liệu để tạo ra màn hình P_D_A_ hấp dẫn. Giao diện người dùng xác nhận sẽ thực hiện công việc này.
Các bên tham gia xác nhận việc xem xét đối thủ cạnh tranh và thiết kế màn hình P_D_A_.
Marketing và Industrial Designer đang chờ đợi email liên quan đến thiết kế màn hình P_D_A_.
Quản lý dự án cảnh báo các cuộc họp tiếp theo và đánh giá thiết kế màn hình P_D_A_ chưa đáng giá. Chủ đề chuyển sang sự kết hợp giữa thời trang và điện tử.
```

### ssdst final belief states

```json
[
  {
    "current_topic": "Thiết kế giao diện và kích thước thiết bị cầm tay giống P_D_A.",
    "entities": [
      "Project Manager",
      "User Interface"
    ],
    "decisions": [],
    "open_actions": [],
    "resolved_references": []
  },
  {
    "current_topic": "Cảnh báo cuộc họp tiếp theo và đánh giá thiết kế màn hình P_D_A_",
    "entities": [
      "Marketing",
      "Industrial Designer",
      "Project Manager"
    ],
    "decisions": [],
    "open_actions": [
      "Chờ đợi email liên quan đến thiết kế màn hình P_D_A_"
    ],
    "resolved_references": []
  }
]
```
