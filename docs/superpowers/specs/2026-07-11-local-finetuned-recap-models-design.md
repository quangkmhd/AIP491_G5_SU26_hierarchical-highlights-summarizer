# Local Fine-Tuned Recap Models — Design Spec

**Date:** 2026-07-11  
**Status:** Approved  
**Area:** `repo`, `service`, `runtime`, tests, operations  
**Layer position:** `Types -> Config -> Repo -> Service -> Runtime -> UI`

## 1. Context

The recap pipeline currently sends both chunk-summary and topic-title tasks to
one Gemma/GGUF-style backbone. It formats long instruction prompts, expects
JSON-shaped output, and creates a topic title from every raw utterance in the
segment.

Two local sequence-to-sequence checkpoints have now been fine-tuned for the
actual task shapes:

- `vit5-chunk-summarizer-v1`: an 8-utterance Vietnamese chunk to a short
  Vietnamese summary.
- `bartpho-topic-titler-v2`: all ordered chunk summaries in one topic to a
  Vietnamese topic title.

Their training and evaluation code is under
`../16-dts-tsl/src/train/{chunk_summarizer,topic_titler}`. Runtime inference
must reproduce that preprocessing rather than retain the former LLM prompt and
JSON contract.

## 2. Goals

- Replace Gemma/GGUF recap generation with the two local fine-tuned models.
- Always use real local models in runtime; remove `MODEL_LOAD_LLM` and mock
  selection from the production loader path.
- Run inference on CUDA and fail clearly if CUDA or required local artifacts
  are unavailable.
- Generate every chunk summary before generating its topic title.
- Give the title model only the ordered summaries belonging to that topic; do
  not give it raw utterances or chunk objects.
- Match the prefixes, formatting, truncation, token limits, and generation
  settings used by the training/evaluation code.
- Preserve the public recap schema and streaming event contract.
- Keep unit tests lightweight through injected inference interfaces, while
  providing a separate CUDA real-model smoke test.

## 3. Non-goals

- Retraining or evaluating new model weights.
- Changing topic segmentation or chunk size.
- Changing `HierarchicalRecap`, `SegmentResult`, `Chunk`, SSE, or NDJSON wire
  schemas.
- Adding remote model downloads, CPU fallback, quantization, batching across
  meetings, or model eviction.
- Copying training state such as optimizers, schedulers, RNG state, trainer
  state, or intermediate checkpoints.

## 4. Artifact Layout

Inference artifacts are copied into the current repository under:

```text
models/
├── vit5-chunk-summarizer-v1/
│   ├── config.json
│   ├── generation_config.json
│   ├── model.safetensors
│   ├── tokenizer.json
│   └── tokenizer_config.json
└── bartpho-topic-titler-v2/
    ├── config.json
    ├── generation_config.json
    ├── model.safetensors
    ├── dict.txt
    ├── sentencepiece.bpe.model
    └── tokenizer_config.json
```

The ViT5 files come from
`../16-dts-tsl/models/vit5-chunk-summarizer-v1`. The BARTpho inference files
come from its loadable `checkpoint-184` directory and are flattened into the
destination model root. Files used only to resume training are excluded.

The `models/` tree is local runtime data and must be git-ignored. Model loading
must use `local_files_only=True` where supported and must never silently fetch
missing artifacts from the network.

## 5. Architecture

### 5.1 Model loader

Replace the single `LLM_BACKBONE` model kind with two explicit cached kinds:

- `CHUNK_SUMMARIZER`
- `TOPIC_TITLER`

Each cached handle contains its model, tokenizer, CUDA device, and local
checkpoint path. The loader validates the directory and required files,
constructs the appropriate tokenizer and `AutoModelForSeq2SeqLM`, moves the
model to CUDA, calls `eval()`, and caches the handle once per process.

The ViT5 tokenizer must follow the working local-tokenizer path established by
the training code. The BARTpho tokenizer must load from the flattened local
artifact directory. Loading errors must identify the model and include a
concrete `fix` instruction.

### 5.2 Task-specific inference adapters

The Repo layer exposes two small interfaces rather than a generic
`generate(prompt, task)` API:

- A chunk summarizer accepts formatted utterance text and returns summary
  text.
- A topic titler accepts ordered summary text and returns title text.

Their implementations own tokenization, CUDA tensor transfer,
`torch.inference_mode()`, generation, decoding, and output trimming. This keeps
model-specific limits out of the Service layer and permits fake adapters in
unit tests.

### 5.3 Hierarchical summarization service

`HierarchicalSummarizationService` retains the domain-facing operations
`abstractive(chunk)` and `title(segment)`. It formats domain values into the
two trained task shapes and delegates inference to the corresponding adapter.
It no longer parses JSON or defines Pydantic response models.

An empty chunk returns `Đoạn trống`. A segment with no non-empty generated
summaries returns `Chương trống`. A model that returns only whitespace is a
generation failure rather than a successful `none` value.

## 6. Exact Input and Generation Contracts

### 6.1 Chunk summary

Utterances retain their chronological order and are formatted one per line:

```text
speaker: text
speaker: text
```

No chunk ID, chapter number, JSON instruction, markdown, or extra system prompt
is added. The exact model input is:

```text
Tóm tắt: {formatted_utterances}
```

Inference settings mirror `evaluate_chunk_summarizer.py`:

- input maximum: 512 tokens, with tokenizer truncation
- `num_beams=4`
- `max_new_tokens=128`
- `no_repeat_ngram_size=3`
- `length_penalty=1.0`
- `early_stopping=True`
- deterministic generation (`do_sample=False`)

The decoded summary is stripped but is not JSON-parsed or arbitrarily cut at
256 characters.

### 6.2 Topic title

After every chunk in a topic has a generated summary, the service:

1. preserves chunk order;
2. discards empty/whitespace summaries;
3. joins them with ` / `;
4. if the joined text exceeds 1,500 characters, keeps the final 1,500
   characters, matching training preprocessing; and
5. prepends the exact task prefix.

The exact model input is:

```text
Tạo tiêu đề: {summary_1} / {summary_2} / ...
```

Raw utterances, speaker labels from the original chunks, chunk IDs, and other
segments must never be included. Inference settings mirror
`evaluate_topic_titler.py`:

- input maximum: 1,024 tokens, with tokenizer truncation
- `num_beams=4`
- `max_new_tokens=200`
- `no_repeat_ngram_size=3`
- `length_penalty=1.0`
- `early_stopping=True`
- deterministic generation (`do_sample=False`)

The decoded title is stripped and used directly. The former one-line-summary
secondary output is removed.

### 6.3 Prompt registry

The long Gemma-oriented prompt templates and `SYSTEM_PROMPT_VI` are removed.
If prompt constants remain centralized, they contain only the two exact
fine-tuning prefixes:

- `Tóm tắt: `
- `Tạo tiêu đề: `

Adding natural-language instructions not seen in fine-tuning is prohibited
because it changes the trained input distribution.

## 7. Pipeline and Event Ordering

For each detected topic segment, the orchestrator continues to:

1. create chunks in chronological order;
2. generate and store each chunk summary;
3. emit `chunk-closed` for each summarized chunk;
4. emit `segment-closed` after all topic chunks are complete;
5. generate the title from the now-complete ordered summary list;
6. store the title and emit `title-emitted`;
7. include the completed segment in the final recap.

This ensures title inference sees all and only the summaries of its own topic.
The existing public event payloads and `meeting-completed` final-event
guarantee do not change.

## 8. Failure Handling

- Missing model directory/file: fail during model initialization with the
  missing path and a `fix` telling the operator where to place the artifacts.
- CUDA unavailable: fail before loading weights with a `fix` to run on the
  CUDA-capable environment.
- Tokenizer/model incompatibility: identify which checkpoint failed and advise
  checking its complete inference artifact set.
- CUDA OOM: preserve the original exception context and advise freeing VRAM;
  do not silently fall back to CPU or another model.
- Empty decoded output: raise an actionable generation error identifying the
  task; do not store a misleading successful value.
- No remote download or mock fallback is allowed.

## 9. Testing and Verification

### 9.1 Unit tests

- Model loader caches the summary and title models independently.
- Missing artifacts and missing CUDA produce actionable errors.
- Summary formatting exactly matches `Tóm tắt: speaker: text` with newline
  ordering and no legacy JSON/chunk metadata.
- Summary output flows through without the former 256-character cut.
- Title input contains ordered chunk summaries separated by ` / `.
- Title input keeps the final 1,500 characters when over the character cap.
- Title input contains no raw utterance text when summaries are present.
- Empty chunks/segments follow the documented behavior.

Unit tests inject fake task-specific adapters and must not load real weights.

### 9.2 Integration tests

- The orchestrator generates all summaries for a segment before calling the
  titler.
- A title call receives only summaries from its segment.
- Event ordering and final recap schema remain unchanged.
- API and CLI tests inject lightweight model doubles at their approved
  construction boundary rather than depending on `MODEL_LOAD_LLM=0`.

### 9.3 CUDA smoke test

A separately marked real-model smoke test loads both copied checkpoints on
CUDA, summarizes a small Vietnamese chunk, generates a title from one or more
summaries, and asserts non-empty decoded strings. It is excluded from the
fast default unit suite and documented as a required local release check.

### 9.4 Standard verification

The standard repository bootstrap and full test suite must run after the
dependency lock is restored. At design time, baseline verification was blocked
because `uv.lock` was already deleted in the incoming worktree. Implementation
must preserve unrelated user changes while restoring a reproducible dependency
state before behavior changes are declared complete.

## 10. Dependencies and Cleanup

- Retain `torch` and `transformers` and include tokenizer runtime dependencies
  required by the copied ViT5 and BARTpho artifacts.
- Remove the Gemma/GGUF runtime path, Hugging Face Hub download path,
  `llama-cpp-python`, generic LLM backbone adapter, mock selection, legacy JSON
  response models, and obsolete long prompt tests when no remaining consumer
  needs them.
- Remove `MODEL_LOAD_LLM` from runtime docs, tests, and examples.
- Do not perform unrelated topic-segmentation or UI refactors.

## 11. Documentation Updates

The implementation session updates the current system of record wherever the
old Gemma/mock behavior or raw-utterance title input is described:

- `ARCHITECTURE.md`
- relevant OpenWiki workflow, model/data, and operations pages
- the onboarding product spec
- active execution plan and plan index
- `docs/QUALITY_SCORE.md`
- reliability/security documentation if their operational statements change

Verification evidence and the real-model smoke command are recorded in the
active plan or quality document. The repository must be restartable from the
documented bootstrap path before the plan is completed.

