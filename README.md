# LLM-Powered Hierarchical Meeting Recap System with Topic Segmentation

This repository contains the implementation of a hierarchical meeting recap system that integrates CoherenceNet (NSP BERT) TextTiling for improved, unsupervised topic segmentation. 

The project strictly follows a layered architecture to ensure scalability, maintainability, and clean separation of concerns.

## Sự Kết Hợp Của 2 Paper (The Synergy of Two Papers)

Dự án này là sự kết hợp (synergy) mạnh mẽ giữa 2 nghiên cứu:
1. **Improving Unsupervised Dialogue Topic Segmentation with Utterance-Pair Coherence Scoring**: Cung cấp thuật toán cốt lõi `NSP BERT + TextTiling` để chấm điểm độ liền mạch (coherence) giữa các cặp câu, qua đó xác định chính xác ranh giới các chủ đề (topic boundaries) mà không cần giám sát.
2. **LLM-powered Meeting Recap System**: Thay vì dùng thuật toán chia đoạn trượt (sliding windows) cơ bản của paper này, chúng ta lấy ý tưởng về trải nghiệm người dùng (UX) và kiến trúc phân cấp (Hierarchical Minutes, Highlights). 

Sự kết hợp này tạo ra một 파ipeline hoàn chỉnh: dùng phương pháp **Topic Segmentation** xuất sắc của Paper 1 để cắt đoạn hội thoại, sau đó đưa vào hệ thống **Hierarchical Recap** của Paper 2 để tạo ra bản tóm tắt họp phân cấp cực kỳ chất lượng. Chi tiết xem tại `docs/design-docs/paper-integration.md`.

## Documentation

The `docs/` folder contains the source of truth for the project's setup, guidelines, and specifications:

- `ARCHITECTURE.md`: Overview of the domain map and strict layered architecture (`Types -> Config -> Repo -> Service -> Runtime -> UI`).
- `docs/papers/`: Reference papers for the implementation.
- `docs/PRODUCT_SENSE.md`: Explains the main user workflows and product goals.
- `docs/RELIABILITY.md`: Commands and expected behaviors for maintaining system health.

## Reference Code

The original un-refactored scripts and models from the topic segmentation paper can be found in `references_code/dialogue-topic-segmenter`.

## Setup

This project uses `uv` for dependency management.

```bash
uv sync
uv run src/runtime/cli.py --help
```
