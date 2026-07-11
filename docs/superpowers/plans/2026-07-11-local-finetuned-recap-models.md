# Local Fine-Tuned Recap Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic Gemma recap backbone with a local ViT5 chunk summarizer and a local BARTpho topic titler whose title input contains only the completed summaries from its topic.

**Architecture:** The Repo layer will cache two independent Hugging Face seq2seq handles and expose task-specific CUDA inference adapters. `HierarchicalSummarizationService` will translate domain objects into the exact fine-tuning input shapes, while the orchestrator retains its public event and recap contracts.

**Tech Stack:** Python 3.11+, PyTorch, Hugging Face Transformers, ViT5/T5 tokenizer, BARTpho/MBART tokenizer, Pydantic, unittest/pytest runner, uv.

## Global Constraints

- Runtime always uses real local models; there is no `MODEL_LOAD_LLM`, mock, remote-download, CPU, or alternative-model fallback.
- CUDA is required; missing CUDA must fail with an actionable `fix` message.
- ViT5 input is exactly `Tóm tắt: ` plus chronological `speaker: text` lines; maximum input is 512 tokens.
- BARTpho input is exactly `Tạo tiêu đề: ` plus ordered non-empty summaries joined by ` / `; only the final 1,500 characters are retained before prefixing; maximum input is 1,024 tokens.
- Both tasks use deterministic beam generation with `num_beams=4`, `no_repeat_ngram_size=3`, `length_penalty=1.0`, and `early_stopping=True`.
- ViT5 uses `max_new_tokens=128`; BARTpho uses `max_new_tokens=200`.
- Public recap schemas and streaming event payloads do not change.
- Copy inference artifacts only. Never copy optimizer, scheduler, scaler, RNG, trainer state, training arguments, or intermediate checkpoint state.
- Preserve the incoming deletion of `uv.lock` until the dependency task intentionally regenerates it; do not disturb unrelated user changes.

---

## File Structure

### New files

- `src/repo/seq2seq_inference.py`: task-specific inference protocols and CUDA implementations.
- `tests/unit/test_seq2seq_inference.py`: adapter tokenization, generation, decoding, and failure tests using model/tokenizer doubles.
- `tests/manual/test_local_recap_models_smoke.py`: opt-in CUDA smoke test for both copied checkpoints.
- `docs/exec-plans/active/local-finetuned-recap-models.md`: repository-system execution record and verification evidence.

### Modified files

- `.gitignore`: ignore local `models/` artifacts.
- `pyproject.toml`, `uv.lock`: remove GGUF dependencies, ensure local tokenizer dependencies, and restore reproducible bootstrap.
- `src/repo/model_loader.py`: define two model kinds, local paths, validation, CUDA-only loading, and independent caching.
- `src/repo/prompts_vi.py`: retain only exact fine-tuning prefixes.
- `src/repo/__init__.py`: export the new loader/adapters/constants and remove legacy exports.
- `src/service/hierarchical_summarization.py`: inject two adapters, format exact task inputs, and remove JSON parsing/character clipping.
- `src/service/meeting_recap_orchestrator.py`: preserve behavior and document/enforce summary-before-title ordering.
- `tests/unit/test_model_loader.py`: replace Gemma/mock tests with local dual-handle tests.
- `tests/unit/test_prompts_vi.py`: assert exact prefixes and absence of legacy prompt instructions.
- `tests/unit/test_hierarchical_summarization.py`: use fakes and verify exact summary/title inputs.
- `tests/unit/test_streaming_orchestrator.py`: inject a recording summarizer and verify per-topic ordering/isolation.
- `tests/integration/test_api_streaming.py`, `tests/unit/test_cli.py`: remove environment mock selection and inject lightweight service construction.
- `ARCHITECTURE.md`, `openwiki/quickstart.md`, `openwiki/workflows.md`, `openwiki/models_and_data.md`, `openwiki/operations.md`, `docs/product-specs/new-user-onboarding.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md`, `docs/QUALITY_SCORE.md`, `docs/PLANS.md`, and `docs/exec-plans/active/index.md`: make operational and architectural documentation current.

---

### Task 1: Restore Bootstrap and Vendor Inference Artifacts

**Files:**
- Modify: `.gitignore`
- Modify: `pyproject.toml`
- Create: `uv.lock`
- Create locally, ignored: `models/vit5-chunk-summarizer-v1/*`
- Create locally, ignored: `models/bartpho-topic-titler-v2/*`
- Create: `docs/exec-plans/active/local-finetuned-recap-models.md`
- Modify: `docs/exec-plans/active/index.md`

**Interfaces:**
- Consumes: source checkpoint directories under `../16-dts-tsl/models/`.
- Produces: two loadable local model roots and a reproducible Python environment for later tasks.

- [ ] **Step 1: Record the incoming worktree and artifact manifests**

Run:

```bash
pwd
git status --short
find ../16-dts-tsl/models/vit5-chunk-summarizer-v1 -maxdepth 1 -type f -printf '%f\n' | sort
find ../16-dts-tsl/models/bartpho-topic-titler-v2/checkpoint-184 -maxdepth 1 -type f -printf '%f\n' | sort
```

Expected: repository root is `15-Meeting-summary`; `uv.lock` is shown as deleted; ViT5 has a root inference checkpoint and BARTpho has a loadable `checkpoint-184`.

- [ ] **Step 2: Add a failing artifact-layout check before copying**

Run:

```bash
test -f models/vit5-chunk-summarizer-v1/model.safetensors \
  && test -f models/bartpho-topic-titler-v2/model.safetensors \
  && test -f models/bartpho-topic-titler-v2/sentencepiece.bpe.model
```

Expected: FAIL because the destination model roots do not exist yet.

- [ ] **Step 3: Ignore local model artifacts and update dependencies**

Add to `.gitignore`:

```gitignore
# Local inference checkpoints (copied by the operator; never committed)
models/
```

Change the dependency list in `pyproject.toml` so the model-related portion is:

```toml
dependencies = [
    "torch>=2.6.0",
    "transformers>=5.12.0",
    "sentencepiece>=0.2.0",
    "protobuf>=5.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0,<3.0",
    "stopwordsiso>=0.7.1",
    "fastapi>=0.139.0",
    "uvicorn>=0.51.0",
    "sse-starlette>=3.4.5",
]
```

This removes unused `bitsandbytes` and `llama-cpp-python`; no quantization or GGUF code remains in scope.

- [ ] **Step 4: Copy only inference files**

Run these explicit, non-destructive commands:

```bash
mkdir -p models/vit5-chunk-summarizer-v1 models/bartpho-topic-titler-v2
cp ../16-dts-tsl/models/vit5-chunk-summarizer-v1/config.json models/vit5-chunk-summarizer-v1/
cp ../16-dts-tsl/models/vit5-chunk-summarizer-v1/generation_config.json models/vit5-chunk-summarizer-v1/
cp ../16-dts-tsl/models/vit5-chunk-summarizer-v1/model.safetensors models/vit5-chunk-summarizer-v1/
cp ../16-dts-tsl/models/vit5-chunk-summarizer-v1/tokenizer.json models/vit5-chunk-summarizer-v1/
cp ../16-dts-tsl/models/vit5-chunk-summarizer-v1/tokenizer_config.json models/vit5-chunk-summarizer-v1/
cp ../16-dts-tsl/models/bartpho-topic-titler-v2/checkpoint-184/config.json models/bartpho-topic-titler-v2/
cp ../16-dts-tsl/models/bartpho-topic-titler-v2/checkpoint-184/generation_config.json models/bartpho-topic-titler-v2/
cp ../16-dts-tsl/models/bartpho-topic-titler-v2/checkpoint-184/model.safetensors models/bartpho-topic-titler-v2/
cp ../16-dts-tsl/models/bartpho-topic-titler-v2/checkpoint-184/dict.txt models/bartpho-topic-titler-v2/
cp ../16-dts-tsl/models/bartpho-topic-titler-v2/checkpoint-184/sentencepiece.bpe.model models/bartpho-topic-titler-v2/
cp ../16-dts-tsl/models/bartpho-topic-titler-v2/checkpoint-184/tokenizer_config.json models/bartpho-topic-titler-v2/
```

Expected: no `optimizer.pt`, `scheduler.pt`, `scaler.pt`, `rng_state.pth`, `trainer_state.json`, or `training_args.bin` exists below the destination `models/` tree.

- [ ] **Step 5: Verify the copied manifests and local ignore rule**

Run:

```bash
test -f models/vit5-chunk-summarizer-v1/model.safetensors
test -f models/bartpho-topic-titler-v2/model.safetensors
test -f models/bartpho-topic-titler-v2/sentencepiece.bpe.model
! find models -type f \( -name 'optimizer.pt' -o -name 'scheduler.pt' -o -name 'scaler.pt' -o -name 'rng_state.pth' -o -name 'trainer_state.json' -o -name 'training_args.bin' \) | grep -q .
git check-ignore models/vit5-chunk-summarizer-v1/model.safetensors
```

Expected: all commands PASS and `git status --short` does not list model files.

- [ ] **Step 6: Regenerate the lock and run the pre-change baseline**

Run:

```bash
uv lock
uv sync --extra dev
uv run pytest tests/ -q
```

Expected: `uv.lock` is recreated. If the suite exposes failures caused by the prior deleted lock/environment, repair the baseline without changing recap behavior and record exact evidence before continuing.

- [ ] **Step 7: Create the active execution record**

Create `docs/exec-plans/active/local-finetuned-recap-models.md` with:

```markdown
# Local Fine-Tuned Recap Models

## Objective
Replace Gemma recap generation with local ViT5 chunk summaries and BARTpho titles generated only from completed topic summaries.

## Scope
Repo model loading, task adapters, hierarchical summarization input contracts, orchestrator ordering verification, local artifacts, runtime tests, and matching documentation.

## Out of Scope
Retraining, segmentation changes, schema changes, CPU fallback, quantization, and remote downloads.

## Verification Path
- `uv run pytest tests/ -q`
- `uv run pytest tests/manual/test_local_recap_models_smoke.py -v -m real_model`
- `uv run python -m src.runtime.cli process <fixture> -o <output>`

## Risks and Blockers
- Both float32 models must fit available CUDA VRAM.
- Local artifacts are ignored and must be provisioned before runtime startup.

## Progress Log
- 2026-07-11: plan opened; incoming `uv.lock` deletion recorded and bootstrap restored.

## Open Decisions
None.
```

Add it to `docs/exec-plans/active/index.md` with owner step `Task 1: artifact/bootstrap verification` and status `In progress`.

- [ ] **Step 8: Commit bootstrap metadata without model binaries**

Run:

```bash
git add .gitignore pyproject.toml uv.lock docs/exec-plans/active/local-finetuned-recap-models.md docs/exec-plans/active/index.md
git commit -m "chore: prepare local recap model runtime"
```

Expected: commit succeeds and `git show --stat --oneline HEAD` contains no file under `models/`.

---

### Task 2: Dual CUDA Model Loader

**Files:**
- Modify: `src/repo/model_loader.py`
- Modify: `src/repo/__init__.py`
- Modify: `tests/unit/test_model_loader.py`

**Interfaces:**
- Produces: `ModelKind.CHUNK_SUMMARIZER`, `ModelKind.TOPIC_TITLER`; `ModelLoader.load_chunk_summarizer() -> ModelHandle`; `ModelLoader.load_topic_titler() -> ModelHandle`.
- Produces constants: `CHUNK_SUMMARIZER_PATH: Path`, `TOPIC_TITLER_PATH: Path`.

- [ ] **Step 1: Replace legacy loader tests with failing dual-model tests**

Write tests equivalent to:

```python
def test_model_kinds_are_task_specific(self) -> None:
    self.assertEqual(
        {kind.name for kind in ModelKind},
        {"CHUNK_SUMMARIZER", "TOPIC_TITLER"},
    )

@mock.patch("src.repo.model_loader._load_seq2seq_handle")
def test_handles_cache_independently(self, load: mock.Mock) -> None:
    load.side_effect = lambda kind, path: ModelHandle(
        kind=kind, model=object(), tokenizer=object(), device="cuda", checkpoint_path=str(path)
    )
    loader = ModelLoader()
    self.assertIs(loader.load_chunk_summarizer(), loader.load_chunk_summarizer())
    self.assertIs(loader.load_topic_titler(), loader.load_topic_titler())
    self.assertEqual(load.call_count, 2)

@mock.patch("torch.cuda.is_available", return_value=False)
def test_cuda_is_required(self, _: mock.Mock) -> None:
    with self.assertRaisesRegex(ModelLoadError, "fix.*CUDA"):
        ModelLoader().load_chunk_summarizer()
```

Also test that a missing required file names its checkpoint and includes `fix`.

- [ ] **Step 2: Run loader tests to verify failure**

Run:

```bash
uv run pytest tests/unit/test_model_loader.py -q
```

Expected: FAIL because the task-specific kinds, methods, paths, and error type do not exist.

- [ ] **Step 3: Implement the CUDA-only loader and independent cache**

Implement these public shapes in `src/repo/model_loader.py`:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNK_SUMMARIZER_PATH = PROJECT_ROOT / "models" / "vit5-chunk-summarizer-v1"
TOPIC_TITLER_PATH = PROJECT_ROOT / "models" / "bartpho-topic-titler-v2"

class ModelKind(str, Enum):
    CHUNK_SUMMARIZER = "chunk_summarizer"
    TOPIC_TITLER = "topic_titler"

class ModelLoadError(RuntimeError):
    pass

@dataclass(frozen=True)
class ModelHandle:
    kind: ModelKind
    model: Any
    tokenizer: Any
    device: str
    checkpoint_path: str

REQUIRED_FILES = {
    ModelKind.CHUNK_SUMMARIZER: {"config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json"},
    ModelKind.TOPIC_TITLER: {"config.json", "model.safetensors", "dict.txt", "sentencepiece.bpe.model", "tokenizer_config.json"},
}

def _load_seq2seq_handle(kind: ModelKind, path: Path) -> ModelHandle:
    if not torch.cuda.is_available():
        raise ModelLoadError("CUDA is unavailable; fix: run the recap service on the configured CUDA host")
    missing = sorted(name for name in REQUIRED_FILES[kind] if not (path / name).is_file())
    if missing:
        raise ModelLoadError(f"{kind.value} checkpoint is incomplete at {path}; missing={missing}; fix: copy the complete inference artifact set")
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, use_fast=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(path, local_files_only=True)
    model.to("cuda")
    model.eval()
    return ModelHandle(kind=kind, model=model, tokenizer=tokenizer, device="cuda", checkpoint_path=str(path))
```

Keep the existing singleton/cache locking pattern, with a private `_load(kind, path)` method and the two public load methods. Remove GGUF constants, Hugging Face Hub download code, `MockLLMBackbone`, `GGUFLLMBackbone`, and environment branching. Update `src/repo/__init__.py` exports to exactly match the new public API.

- [ ] **Step 4: Run focused and layer-rule tests**

Run:

```bash
uv run pytest tests/unit/test_model_loader.py tests/unit/test_repo_layer_rules.py -q
```

Expected: PASS; tests patch `_load_seq2seq_handle`, so no real checkpoint is loaded.

- [ ] **Step 5: Commit the loader**

Run:

```bash
git add src/repo/model_loader.py src/repo/__init__.py tests/unit/test_model_loader.py
git commit -m "feat: load local recap models independently"
```

---

### Task 3: Task-Specific Seq2Seq Inference Adapters

**Files:**
- Create: `src/repo/seq2seq_inference.py`
- Create: `tests/unit/test_seq2seq_inference.py`
- Modify: `src/repo/__init__.py`

**Interfaces:**
- Consumes: `ModelHandle` from Task 2.
- Produces: `ChunkSummarizer` protocol with `summarize(formatted_utterances: str) -> str`.
- Produces: `TopicTitler` protocol with `generate_title(joined_summaries: str) -> str`.
- Produces: `ViT5ChunkSummarizer(handle: ModelHandle)` and `BARTphoTopicTitler(handle: ModelHandle)`.

- [ ] **Step 1: Write failing adapter contract tests**

Use tokenizer/model doubles that record calls. Assert:

```python
summary = ViT5ChunkSummarizer(handle).summarize("S1: Nội dung")
self.assertEqual(tokenizer.inputs, ["Tóm tắt: S1: Nội dung"])
self.assertEqual(tokenizer.kwargs["max_length"], 512)
self.assertEqual(model.generate_kwargs, {
    "num_beams": 4,
    "max_new_tokens": 128,
    "no_repeat_ngram_size": 3,
    "length_penalty": 1.0,
    "early_stopping": True,
    "do_sample": False,
})

title = BARTphoTopicTitler(handle).generate_title("Tóm tắt một / Tóm tắt hai")
self.assertEqual(tokenizer.inputs, ["Tạo tiêu đề: Tóm tắt một / Tóm tắt hai"])
self.assertEqual(tokenizer.kwargs["max_length"], 1024)
self.assertEqual(model.generate_kwargs["max_new_tokens"], 200)
```

Also assert decoding uses `skip_special_tokens=True`, output is stripped, `torch.inference_mode()` is active during `generate`, and whitespace-only output raises `GenerationError` containing `fix` and the task name.

- [ ] **Step 2: Run adapter tests to verify failure**

Run:

```bash
uv run pytest tests/unit/test_seq2seq_inference.py -q
```

Expected: FAIL because the adapter module does not exist.

- [ ] **Step 3: Implement focused adapter classes**

Implement a shared private base only for mechanical inference:

```python
class GenerationError(RuntimeError):
    pass

class _Seq2SeqGenerator:
    prefix: str
    max_input_tokens: int
    max_new_tokens: int

    def __init__(self, handle: ModelHandle) -> None:
        self._model = handle.model
        self._tokenizer = handle.tokenizer
        self._device = handle.device

    def _generate(self, body: str, task_name: str) -> str:
        encoded = self._tokenizer(
            self.prefix + body,
            max_length=self.max_input_tokens,
            truncation=True,
            return_tensors="pt",
        ).to(self._device)
        with torch.inference_mode():
            token_ids = self._model.generate(
                **encoded,
                num_beams=4,
                max_new_tokens=self.max_new_tokens,
                no_repeat_ngram_size=3,
                length_penalty=1.0,
                early_stopping=True,
                do_sample=False,
            )
        output = self._tokenizer.batch_decode(token_ids, skip_special_tokens=True)[0].strip()
        if not output:
            raise GenerationError(f"{task_name} returned empty output; fix: verify the local checkpoint and input text")
        return output

class ViT5ChunkSummarizer(_Seq2SeqGenerator):
    prefix = "Tóm tắt: "
    max_input_tokens = 512
    max_new_tokens = 128
    def summarize(self, formatted_utterances: str) -> str:
        return self._generate(formatted_utterances, "chunk_summarizer")

class BARTphoTopicTitler(_Seq2SeqGenerator):
    prefix = "Tạo tiêu đề: "
    max_input_tokens = 1024
    max_new_tokens = 200
    def generate_title(self, joined_summaries: str) -> str:
        return self._generate(joined_summaries, "topic_titler")
```

Define both protocols with `typing.Protocol` and export them from `src/repo/__init__.py`.

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest tests/unit/test_seq2seq_inference.py tests/unit/test_model_loader.py -q
```

Expected: PASS without loading CUDA weights.

- [ ] **Step 5: Commit the adapters**

Run:

```bash
git add src/repo/seq2seq_inference.py src/repo/__init__.py tests/unit/test_seq2seq_inference.py
git commit -m "feat: add fine-tuned recap inference adapters"
```

---

### Task 4: Exact Summary and Title Service Inputs

**Files:**
- Modify: `src/repo/prompts_vi.py`
- Modify: `src/service/hierarchical_summarization.py`
- Modify: `tests/unit/test_prompts_vi.py`
- Modify: `tests/unit/test_hierarchical_summarization.py`

**Interfaces:**
- Consumes: `ChunkSummarizer.summarize(str) -> str` and `TopicTitler.generate_title(str) -> str`.
- Produces: `HierarchicalSummarizationService(chunk_summarizer: ChunkSummarizer | None = None, topic_titler: TopicTitler | None = None)`.
- Preserves: `abstractive(chunk, chapter_number=1, chunk_index=0) -> str`, `title(segment, chapter_number=1) -> str`, and `abstractive_utterances(utterances) -> str`.

- [ ] **Step 1: Rewrite service tests with recording fakes**

Define test doubles:

```python
class RecordingSummarizer:
    def __init__(self, output: str = "summary") -> None:
        self.inputs: list[str] = []
        self.output = output
    def summarize(self, text: str) -> str:
        self.inputs.append(text)
        return self.output

class RecordingTitler:
    def __init__(self, output: str = "title") -> None:
        self.inputs: list[str] = []
        self.output = output
    def generate_title(self, text: str) -> str:
        self.inputs.append(text)
        return self.output
```

Add failing assertions for these exact behaviors:

```python
service.abstractive(Chunk(utterances=[_u(0, "Xin chào"), _u(1, "Kế hoạch")]))
self.assertEqual(summarizer.inputs, ["S1: Xin chào\nS1: Kế hoạch"])

segment = SegmentResult(title="placeholder", chunks=[
    Chunk(utterances=[_u(0, "RAW_SECRET")], rolling_summary="Tóm tắt một"),
    Chunk(utterances=[_u(1, "RAW_OTHER")], rolling_summary="Tóm tắt hai"),
], utterances_start=0, utterances_end=1)
service.title(segment)
self.assertEqual(titler.inputs, ["Tóm tắt một / Tóm tắt hai"])
self.assertNotIn("RAW_SECRET", titler.inputs[0])
```

Add tests for skipping empty summaries, returning `Chương trống` when none remain, retaining the final 1,500 characters, and returning a 1,000-character generated summary unchanged.

- [ ] **Step 2: Run service/prompt tests to verify failure**

Run:

```bash
uv run pytest tests/unit/test_hierarchical_summarization.py tests/unit/test_prompts_vi.py -q
```

Expected: FAIL because the service still loads a generic backbone, uses raw utterances for titles, parses JSON, and clips summaries.

- [ ] **Step 3: Reduce the prompt registry to exact prefixes**

Replace `src/repo/prompts_vi.py` public content with:

```python
SUMMARY_PREFIX_VI = "Tóm tắt: "
TITLE_PREFIX_VI = "Tạo tiêu đề: "

__all__ = ["SUMMARY_PREFIX_VI", "TITLE_PREFIX_VI"]
```

Tests must assert exact equality and assert neither constant contains JSON, chapter IDs, system instructions, or newline text.

- [ ] **Step 4: Implement the service using completed summaries only**

Use this construction and core logic:

```python
TITLE_INPUT_MAX_CHARS = 1500

def __init__(self, chunk_summarizer=None, topic_titler=None, loader=None) -> None:
    model_loader = loader or ModelLoader.instance()
    self._chunk_summarizer = chunk_summarizer or ViT5ChunkSummarizer(model_loader.load_chunk_summarizer())
    self._topic_titler = topic_titler or BARTphoTopicTitler(model_loader.load_topic_titler())

def _format_utterances(self, utterances: list[Utterance]) -> str:
    return "\n".join(f"{u.speaker}: {u.text}" for u in utterances)

def abstractive(self, chunk: Chunk, chapter_number: int = 1, chunk_index: int = 0) -> str:
    if not chunk.utterances:
        return "Đoạn trống"
    return self._chunk_summarizer.summarize(self._format_utterances(chunk.utterances))

def title(self, segment: SegmentResult, chapter_number: int = 1) -> str:
    summaries = [
        chunk.rolling_summary.strip()
        for chunk in segment.chunks
        if chunk.rolling_summary and chunk.rolling_summary.strip()
    ]
    if not summaries:
        return "Chương trống"
    joined = " / ".join(summaries)
    return self._topic_titler.generate_title(joined[-TITLE_INPUT_MAX_CHARS:])
```

Remove JSON/Pydantic response classes, legacy prompt formatting, `LLMTask`, and `ABSTRACTIVE_MAX_CHARS`. Preserve the convenience helper by wrapping utterances in a `Chunk`.

- [ ] **Step 5: Run focused service tests**

Run:

```bash
uv run pytest tests/unit/test_hierarchical_summarization.py tests/unit/test_prompts_vi.py tests/unit/test_seq2seq_inference.py -q
```

Expected: PASS; fake adapters receive the exact unprefixed bodies while adapter tests separately prove the exact prefixes.

- [ ] **Step 6: Commit the service change**

Run:

```bash
git add src/repo/prompts_vi.py src/service/hierarchical_summarization.py tests/unit/test_prompts_vi.py tests/unit/test_hierarchical_summarization.py
git commit -m "feat: title topics from completed chunk summaries"
```

---

### Task 5: Orchestrator Ordering and Runtime Test Injection

**Files:**
- Modify: `src/service/meeting_recap_orchestrator.py`
- Modify: `tests/unit/test_streaming_orchestrator.py`
- Modify: `tests/integration/test_api_streaming.py`
- Modify: `tests/unit/test_cli.py`

**Interfaces:**
- Consumes: existing `StreamingOrchestrator(..., summarizer=...)` injection seam.
- Preserves: all five `RecapEventType` values and payload structures.
- Guarantees: every topic title call occurs after every chunk summary call for that same topic.

- [ ] **Step 1: Add a failing per-topic ordering/isolation test**

Add a recording fake summarizer whose `abstractive` records and returns
`summary-{chunk-first-index}`, and whose `title` asserts all chunks already
have `rolling_summary`, records their values, and returns `title`. Process a
fixture with at least two forced segments and assert:

```python
self.assertEqual(recorder.calls, [
    ("summary", 0), ("summary", 8), ("title", ("summary-0", "summary-8")),
    ("summary", 16), ("title", ("summary-16",)),
])
self.assertLess(event_types.index("segment-closed"), event_types.index("title-emitted"))
self.assertEqual(event_types[-1], "meeting-completed")
```

Use a deterministic tiler double so the test is about orchestration, not TextTiling thresholds.

- [ ] **Step 2: Run the orchestrator test to verify behavior or expose drift**

Run:

```bash
uv run pytest tests/unit/test_streaming_orchestrator.py -q
```

Expected: the new assertion either fails on an ordering/input mismatch or passes because current control flow already satisfies the requirement. A first-pass success is acceptable evidence; do not make a behavior-only edit when none is needed.

- [ ] **Step 3: Remove stale mock assumptions and inject lightweight summarizers**

In API/CLI tests, remove all `MODEL_LOAD_LLM` environment setup. Patch the runtime construction boundary to return `StreamingOrchestrator(summarizer=FakeHierarchicalSummarizer())`, where the fake implements:

```python
def abstractive(self, chunk, chapter_number=1, chunk_index=0):
    return f"Tóm tắt {chunk.utterances[0].index}"

def title(self, segment, chapter_number=1):
    return f"Chủ đề {chapter_number}"
```

Update stale orchestrator comments/docstrings from “deferred via mock” to “title generated after all topic chunk summaries.” Do not change event payload code.

- [ ] **Step 4: Run runtime-focused tests**

Run:

```bash
uv run pytest tests/unit/test_streaming_orchestrator.py tests/integration/test_api_streaming.py tests/unit/test_cli.py -q
```

Expected: PASS without loading either real checkpoint.

- [ ] **Step 5: Commit orchestration verification**

Run:

```bash
git add src/service/meeting_recap_orchestrator.py tests/unit/test_streaming_orchestrator.py tests/integration/test_api_streaming.py tests/unit/test_cli.py
git commit -m "test: enforce summary-before-title pipeline"
```

---

### Task 6: Real CUDA Smoke Test

**Files:**
- Create: `tests/manual/test_local_recap_models_smoke.py`
- Modify: `pyproject.toml` or `pytest.ini` section in the existing project config to register `real_model` marker.

**Interfaces:**
- Consumes: copied model roots, `ModelLoader`, `ViT5ChunkSummarizer`, and `BARTphoTopicTitler`.
- Produces: an explicit release check proving both real checkpoints load and generate on CUDA.

- [ ] **Step 1: Write the opt-in smoke test**

Create:

```python
import pytest
import torch

from src.repo.model_loader import ModelLoader
from src.repo.seq2seq_inference import BARTphoTopicTitler, ViT5ChunkSummarizer

@pytest.mark.real_model
def test_local_recap_models_generate_on_cuda() -> None:
    assert torch.cuda.is_available(), "CUDA is required for the local recap model smoke test"
    loader = ModelLoader()
    summarizer = ViT5ChunkSummarizer(loader.load_chunk_summarizer())
    titler = BARTphoTopicTitler(loader.load_topic_titler())
    summary = summarizer.summarize(
        "Lan: Nhóm thống nhất hoàn thiện API trước thứ Sáu.\n"
        "Minh: Minh sẽ phụ trách kiểm thử tích hợp."
    )
    title = titler.generate_title(summary)
    assert summary.strip()
    assert title.strip()
```

Register the marker:

```toml
[tool.pytest.ini_options]
markers = ["real_model: loads local CUDA checkpoints and performs inference"]
```

- [ ] **Step 2: Run the real smoke test**

Run:

```bash
uv run pytest tests/manual/test_local_recap_models_smoke.py -v -m real_model
```

Expected: PASS with one non-empty ViT5 summary and one non-empty BARTpho title. If CUDA OOM occurs, record actual free/peak VRAM and stop; do not add CPU fallback or silently weaken the model contract.

- [ ] **Step 3: Verify the fast suite does not require model loading**

Run:

```bash
uv run pytest tests/ -q -m 'not real_model'
```

Expected: PASS without constructing a real `HierarchicalSummarizationService` at import time.

- [ ] **Step 4: Commit the smoke harness**

Run:

```bash
git add tests/manual/test_local_recap_models_smoke.py pyproject.toml uv.lock
git commit -m "test: add CUDA recap model smoke check"
```

---

### Task 7: Remove Legacy Surface and Update System-of-Record Docs

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `openwiki/quickstart.md`
- Modify: `openwiki/workflows.md`
- Modify: `openwiki/models_and_data.md`
- Modify: `openwiki/operations.md`
- Modify: `docs/product-specs/new-user-onboarding.md`
- Modify: `docs/RELIABILITY.md`
- Modify: `docs/SECURITY.md`
- Modify: `docs/QUALITY_SCORE.md`
- Modify: `docs/PLANS.md`
- Modify: `docs/exec-plans/active/local-finetuned-recap-models.md`
- Modify: `docs/exec-plans/active/index.md`
- Modify or delete legacy tests/files found by search only when they have no consumer.

**Interfaces:**
- Consumes: verified implementation and test evidence from Tasks 1–6.
- Produces: current architecture/operations documentation and a restartable repository.

- [ ] **Step 1: Run a legacy-surface search and capture every stale reference**

Run:

```bash
rg -n "MODEL_LOAD_LLM|MockLLMBackbone|GGUF|Gemma|gemma|llama_cpp|LLM_BACKBONE|SYSTEM_PROMPT_VI|HIERARCHIC_.*PROMPT|segment_utterances|deBERTa" src tests ARCHITECTURE.md openwiki docs pyproject.toml
```

Expected: remaining matches are documentation or dead legacy code requiring deletion/update; the approved design spec may retain historical mentions.

- [ ] **Step 2: Update architecture and workflow documentation**

Make these statements explicit across the listed docs:

```markdown
- Chunk summary model: local `models/vit5-chunk-summarizer-v1`, CUDA-only.
- Topic title model: local `models/bartpho-topic-titler-v2`, CUDA-only.
- Summary input: chronological `speaker: text` lines.
- Title input: only ordered completed summaries from the current topic, joined by ` / `.
- Model artifacts are provisioned locally and ignored by git; runtime never downloads them.
- Fast tests inject model doubles; the opt-in real-model release check is
  `uv run pytest tests/manual/test_local_recap_models_smoke.py -v -m real_model`.
```

Remove claims that mock/Gemma/deBERTa is the current summarization path or that the title model consumes segment utterances.

- [ ] **Step 3: Update reliability, security, quality, and active-plan evidence**

In `docs/RELIABILITY.md`, replace mock commands with the reproducible fast suite and CUDA smoke command. In `docs/SECURITY.md`, state that no remote checkpoint download occurs and model directories are local ignored artifacts. In `docs/QUALITY_SCORE.md`, update Hierarchical Recap and Repo/Services rows with actual test evidence and date `2026-07-11`.

Append exact commands, pass counts, smoke outputs, and any measured VRAM observations to the active plan progress log. Set the active index owner step to `Task 7: final verification` until all checks finish.

- [ ] **Step 4: Prove no live legacy runtime surface remains**

Run:

```bash
! rg -n "MODEL_LOAD_LLM|MockLLMBackbone|llama_cpp|LLM_BACKBONE_ID|GGUF_MODEL" src tests pyproject.toml
uv run pytest tests/ -q -m 'not real_model'
uv run pytest tests/manual/test_local_recap_models_smoke.py -v -m real_model
git diff --check
```

Expected: legacy search returns no matches; both test commands PASS; `git diff --check` is silent.

- [ ] **Step 5: Verify CLI restart path with a small local fixture**

Run the documented CLI process command against an existing small transcript fixture while CUDA is available:

```bash
uv run python -m src.runtime.cli process data/eval_vi/meeting_committee.json -o /tmp/meeting-recap-real-model.json
```

Expected: exit code 0; output JSON has non-empty `rolling_summary` on every chunk and a non-empty `title` on every segment. Inspect one segment to confirm the command completes under the documented runtime path.

- [ ] **Step 6: Finish and archive the execution record**

Add a final section:

```markdown
## Verification at archive time
- Fast suite: `<exact command and pass count>`
- CUDA smoke: `<exact command and pass count>`
- CLI restart: `<exact command and observed output path>`
- Legacy search: zero live runtime matches
```

Move the plan to `docs/exec-plans/completed/local-finetuned-recap-models.md` and remove its row from `docs/exec-plans/active/index.md` only after all evidence is green. Record any deliberately deferred issue in `docs/exec-plans/tech-debt-tracker.md` instead of hiding it.

- [ ] **Step 7: Commit documentation and completion evidence**

Run:

```bash
git add ARCHITECTURE.md openwiki docs pyproject.toml uv.lock src tests
git commit -m "docs: document fine-tuned recap model runtime"
git status --short
```

Expected: commit succeeds; status is clean except for explicitly preserved unrelated user changes; no model binary is tracked.

---

## Final Acceptance Checklist

- [ ] ViT5 and BARTpho inference artifacts exist locally, are loadable, and are ignored by git.
- [ ] Runtime requires CUDA and never downloads, mocks, or falls back to another execution mode.
- [ ] Chunk summary input and generation parameters match training/evaluation code.
- [ ] Topic title input consists only of ordered current-topic summaries and uses the 1,500-character tail rule.
- [ ] Legacy JSON prompt parsing and 256-character summary clipping are gone.
- [ ] Public event ordering, event payloads, and recap schemas remain compatible.
- [ ] Fast suite and real CUDA smoke test both pass.
- [ ] CLI restarts cleanly with real local models.
- [ ] Architecture, OpenWiki, product, reliability, security, quality, and plan documents are current.

