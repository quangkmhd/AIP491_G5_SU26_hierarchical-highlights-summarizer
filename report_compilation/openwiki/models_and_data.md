# Models, Inputs, and Data Validation

## Topic Segmentation

Topic segmentation is network-free lexical Sliding TextTiling: bag-of-words
cosine similarity, multi-scale depth scoring, thresholding at
`mean + alpha * std`, and small-segment merging.

## Local Recap Models

- `models/vit5-chunk-summarizer-v1`: CUDA-only chunk summarizer. Input is
  exactly `Tóm tắt: ` followed by chronological `speaker: text` lines. Input
  is truncated to 512 tokens and generation uses four beams with at most 128
  new tokens.
- `models/bartpho-topic-titler-v2`: CUDA-only topic titler. After every chunk
  summary in a topic exists, summaries are joined in order with ` / `; only
  the final 1,500 characters are retained and prefixed with `Tạo tiêu đề: `.
  Raw utterances are never supplied to the title model. Input is limited to
  1,024 tokens and generation uses four beams with at most 200 new tokens.

Both checkpoints are local ignored artifacts. Runtime requires CUDA, loads
with `local_files_only=True`, and never downloads or falls back to mock/CPU.

## Validation Bounds

- Transcript utterance indices are contiguous from zero.
- `MAX_UTTERANCES = 5000` protects runtime memory.
- A chunk contains at most 8 utterances.
- Fast tests inject inference doubles to verify local model checkpoints.
