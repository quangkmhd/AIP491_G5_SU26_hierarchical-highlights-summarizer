# Custom 10h Topic Summary Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a resumable Custom_10h evaluation runner that executes Zipformer SSL 100h ASR, CAM++ speaker labeling, topic segmentation, ViT5 chunk summarization, BARTpho topic titling, and source-grounded AI judging while scoring only summary quality.

**Architecture:** A dedicated package under `training-eval-suite/src/evaluate/custom_10h_summary` owns stage contracts, content-addressed caches, and orchestration. Expensive integrations are adapters behind protocols: `sherpa-onnx` for ASR, pinned 3D-Speaker CAM++ for embeddings/clustering, local Transformers checkpoints for recap generation, and DeepSeek's JSON chat endpoint for judging. Each stage emits JSONL artifacts so aggregation and report generation can run without loading models or calling the API again.

**Tech Stack:** Python 3.11+, pytest, NumPy, PyTorch/torchaudio, sherpa-onnx, Transformers, 3D-Speaker at commit `065629c313eaf1a01c65c640c46d77e61e9607b4`, ModelScope CAM++ model `iic/speech_campplus_sv_zh-cn_16k-common`, DeepSeek Chat Completions over HTTPS.

## Global Constraints

- Every WAV in `training-eval-suite/data/Custom_10h/wavs` is exactly one utterance; do not run VAD or split it again.
- Only summary quality is scored. ASR, speaker labeling, and segmentation are upstream inputs and receive no evaluation score.
- Use root checkpoints `models/Zipformer-SSL-100h`, `models/vit5-chunk-summarizer-v1`, and `models/bartpho-topic-titler-v2/checkpoint-230`.
- ViT5 input must be byte-for-byte compatible with training: `speaker: text` lines, no bullet prefix, at most 8 utterances, prefix `Tóm tắt: `, 512 input tokens.
- ViT5 generation is deterministic: beams 4, max new tokens 128, no-repeat n-gram 3, length penalty 1.0, early stopping true, sampling false.
- BARTpho input joins chunk summaries with ` / ` and keeps the final 1,500 characters.
- Read only `DEEPSEEK_API_KEY` and `LLM_MODEL` from the root `.env`; never persist the key.
- Persist every completed unit and support resume without repeating valid ASR, CAM++, recap, or judge work.
- Do not overwrite or commit the existing user change in `training-eval-suite/src/train/topic_titler/finetune_topic_titler.py`.

---

### Task 1: Evaluation Contracts, Custom_10h Loader, and Content Cache

**Files:**
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/__init__.py`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/contracts.py`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/data.py`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/cache.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_data.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_cache.py`

**Interfaces:**
- Produces `WavUtterance(source_id, utterance_index, recording_id, wav_path, duration)` and `TranscriptUtterance(..., text, speaker)` dataclasses.
- Produces `load_custom_10h(data_dir: Path) -> dict[str, list[WavUtterance]]`.
- Produces `stable_hash(payload: object) -> str` and `JsonCache(root: Path).get/put(namespace, key, value)`.

- [ ] **Step 1: Write failing loader tests**

```python
def test_recording_id_uses_final_numeric_suffix(tmp_path):
    grouped = load_fixture(tmp_path, ["team_a_00012", "team_a_00004"])
    assert [u.utterance_index for u in grouped["team_a"]] == [4, 12]

def test_each_recording_is_one_utterance(tmp_path):
    grouped = load_fixture(tmp_path, ["meeting_00001", "meeting_00002"])
    assert len(grouped["meeting"]) == 2
```

- [ ] **Step 2: Run the loader tests and verify RED**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_data.py -q`

Expected: FAIL because the package and loader do not exist.

- [ ] **Step 3: Implement contracts and loader**

Parse identifiers with `recording_id.rsplit("_", 1)`, require a numeric suffix, resolve `sources[0].source` beneath `data_dir`, reject duplicate `(source_id, utterance_index)`, and return source groups sorted by numeric utterance index.

- [ ] **Step 4: Write failing cache tests**

```python
def test_stable_hash_ignores_mapping_order():
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})

def test_json_cache_round_trips_unicode_atomically(tmp_path):
    cache = JsonCache(tmp_path)
    cache.put("asr", "abc", {"text": "xin chào"})
    assert cache.get("asr", "abc") == {"text": "xin chào"}
```

- [ ] **Step 5: Run cache tests, implement atomic JSON cache, and rerun both files**

Write to a sibling temporary file, `flush`, `fsync`, and `os.replace`; canonicalize hash input using UTF-8 JSON with sorted keys and compact separators.

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_data.py tests/custom_10h_summary/test_cache.py -q`

Expected: PASS.

- [ ] **Step 6: Commit Task 1 in the nested repository**

```bash
git -C training-eval-suite add src/evaluate/custom_10h_summary tests/custom_10h_summary
git -C training-eval-suite commit -m "feat: add Custom 10h evaluation data contracts"
```

---

### Task 2: Zipformer SSL 100h ASR Adapter

**Files:**
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/audio.py`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/asr.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_asr.py`

**Interfaces:**
- Produces `load_mono_16k(path: Path) -> np.ndarray` with float32 samples.
- Produces protocol `AsrDecoder.decode(wav: WavUtterance) -> str`.
- Produces `SherpaZipformerDecoder(model_dir: Path, provider: str, num_threads: int)` using chunk-32/left-128 ONNX files.
- Produces `transcribe_source(items, decoder, cache, model_fingerprint) -> list[TranscriptUtterance]`.

- [ ] **Step 1: Write failing behavior tests with a fake decoder**

```python
def test_transcribe_source_preserves_one_result_per_wav(fake_items, tmp_path):
    decoder = CountingDecoder(["một", "hai"])
    result = transcribe_source(fake_items, decoder, JsonCache(tmp_path), "model-v1")
    assert [x.text for x in result] == ["một", "hai"]
    assert decoder.calls == 2

def test_transcribe_source_reuses_audio_hash_cache(fake_items, tmp_path):
    cache = JsonCache(tmp_path)
    decoder = CountingDecoder(["xin chào"])
    transcribe_source(fake_items[:1], decoder, cache, "model-v1")
    transcribe_source(fake_items[:1], decoder, cache, "model-v1")
    assert decoder.calls == 1
```

- [ ] **Step 2: Run ASR tests and verify RED**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_asr.py -q`

- [ ] **Step 3: Implement the adapter**

Instantiate `sherpa_onnx.OnlineRecognizer.from_transducer` once. For each WAV, accept the full waveform, append 0.4 seconds of zeros, call `input_finished`, decode until not ready, and normalize output with `.strip().lower()`. Cache key fields are WAV SHA-256, hashes of encoder/decoder/joiner/tokens, sherpa-onnx version, provider-independent decode settings, and sample rate.

- [ ] **Step 4: Run ASR tests and existing root ASR unit tests**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_asr.py -q`

Run: `python -m pytest tests/unit/test_asr_engine.py -q`

Expected: PASS without loading a real checkpoint.

- [ ] **Step 5: Commit Task 2 in the nested repository**

```bash
git -C training-eval-suite add src/evaluate/custom_10h_summary/audio.py src/evaluate/custom_10h_summary/asr.py tests/custom_10h_summary/test_asr.py
git -C training-eval-suite commit -m "feat: add cached Zipformer ASR adapter"
```

---

### Task 3: Pinned 3D-Speaker CAM++ Embedding and Speaker Clustering

**Files:**
- Create: `training-eval-suite/scripts/setup_campp.sh`
- Modify: `training-eval-suite/.gitignore`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/speaker.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_speaker.py`

**Interfaces:**
- Produces protocol `SpeakerEmbedder.extract(items: list[WavUtterance]) -> dict[str, np.ndarray]`.
- Produces `CamPlusBatchEmbedder(speakerlab_root, model_id, device, batch_size)` that invokes official `speakerlab/bin/infer_sv_batch.py` once per missing batch.
- Produces `cluster_speakers(items, embeddings, cluster_factory) -> SpeakerLabelResult` with stable labels and explicit fallback metadata.

- [ ] **Step 1: Write failing stable-label and fallback tests**

```python
def test_cluster_labels_follow_first_appearance(fake_items):
    labels = normalize_cluster_labels(fake_items, np.array([7, 3, 7, 3]))
    assert labels == ["Speaker 01", "Speaker 02", "Speaker 01", "Speaker 02"]

def test_single_item_source_records_fallback(fake_items):
    result = cluster_speakers(fake_items[:1], {fake_items[0].recording_id: np.ones(192)}, None)
    assert result.labels == ["Speaker 01"]
    assert result.fallback_reason == "insufficient_utterances"
```

- [ ] **Step 2: Run speaker tests and verify RED**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_speaker.py -q`

- [ ] **Step 3: Add the pinned toolkit setup script**

The script must clone `https://github.com/modelscope/3D-Speaker.git` into `training-eval-suite/.vendor/3d-speaker`, checkout `065629c313eaf1a01c65c640c46d77e61e9607b4`, install its requirements through the active Python interpreter, install ModelScope, and verify `speakerlab/bin/infer_sv_batch.py` exists. Add `.vendor/` to the nested `.gitignore`; do not commit the checkout or downloaded model weights.

- [ ] **Step 4: Implement batch extraction and clustering**

Use official model ID `iic/speech_campplus_sv_zh-cn_16k-common`. Build a WAV-list file, execute `infer_sv_batch.py`, load its NumPy embeddings, and then import `speakerlab.process.cluster.CommonClustering` from the pinned checkout. Default clustering parameters: spectral, `min_num_spks=1`, `max_num_spks=15`, `min_cluster_size=4`, `mer_cos=0.8`, `pval=0.012`. Reorder output labels by first appearance rather than raw cluster number.

- [ ] **Step 5: Add cache invalidation tests and implementation**

Assert embedding keys change with WAV/model revision and label keys change with embedding list/clustering parameters. Cache embeddings per WAV and labels per `source_id`.

- [ ] **Step 6: Run speaker tests**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_speaker.py -q`

Expected: PASS without downloading CAM++.

- [ ] **Step 7: Commit Task 3 in the nested repository**

```bash
git -C training-eval-suite add .gitignore scripts/setup_campp.sh src/evaluate/custom_10h_summary/speaker.py tests/custom_10h_summary/test_speaker.py
git -C training-eval-suite commit -m "feat: add CAM++ speaker labeling stage"
```

---

### Task 4: Training-Compatible ViT5 Input and Local Recap Models

**Files:**
- Modify: `src/service/hierarchical_summarization.py`
- Modify: `tests/unit/test_hierarchical_summarization.py`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/recap_models.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_recap_models.py`

**Interfaces:**
- Produces `format_chunk_input(items: Sequence[TranscriptUtterance]) -> str`.
- Produces `InputCompatibility` per chunk with `token_count`, `char_count`, `utterance_count`, and `was_truncated`.
- Produces `LocalRecapModels(...).summarize_chunks(chunks)` and `.title_topic(summaries)`.

- [ ] **Step 1: Add a failing root regression test for the production formatter**

```python
def test_format_utterances_matches_training_shape():
    utterances = [Utterance(speaker="Speaker 01", text="Xin chào", index=0)]
    assert HierarchicalSummarizationService._format_utterances(utterances) == "Speaker 01: Xin chào"
```

- [ ] **Step 2: Run the root test and verify it fails on the current bullet prefix**

Run: `python -m pytest tests/unit/test_hierarchical_summarization.py -q`

- [ ] **Step 3: Remove the runtime bullet prefix and verify the root test passes**

Change only the formatter from `- {speaker}: {text}` to `{speaker}: {text}`.

- [ ] **Step 4: Write failing nested tests for the exact training contract**

```python
def test_chunk_input_matches_training_formatter():
    items = [tx("Speaker 01", "a"), tx("Speaker 02", "b")]
    assert format_chunk_input(items) == "Speaker 01: a\nSpeaker 02: b"

def test_chunking_never_exceeds_eight_utterances():
    assert [len(x) for x in chunk_utterances(make_tx(17))] == [8, 8, 1]
```

- [ ] **Step 5: Implement model loading and deterministic generation**

Reuse `load_vit5_tokenizer` and `concat_summaries`. Load each checkpoint once, report token counts before truncation, use the exact generation settings in Global Constraints, and return plain serializable chunk/title outputs. Empty model generations are stage failures rather than placeholder summaries.

- [ ] **Step 6: Run nested and root tests**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_recap_models.py -q`

Run: `python -m pytest tests/unit/test_hierarchical_summarization.py tests/unit/test_seq2seq_inference.py -q`

- [ ] **Step 7: Commit root and nested changes separately**

```bash
git add src/service/hierarchical_summarization.py tests/unit/test_hierarchical_summarization.py
git commit -m "fix: align recap input with ViT5 training format"
git -C training-eval-suite add src/evaluate/custom_10h_summary/recap_models.py tests/custom_10h_summary/test_recap_models.py
git -C training-eval-suite commit -m "feat: add training-compatible recap inference"
```

---

### Task 5: Topic Segmentation, Topic Assembly, and Compatibility Audit

**Files:**
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/pipeline.py`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/compatibility.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_pipeline.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_compatibility.py`

**Interfaces:**
- Produces `build_topic_outputs(source_id, transcripts, segmenter, recap_models) -> list[TopicOutput]`.
- Produces `audit_inputs(custom_chunks, train_dev_paths, tokenizer) -> dict`.

- [ ] **Step 1: Write failing topic-assembly tests**

Use a fake segmenter returning lengths `[3, 9]`; assert two non-overlapping topics, the second topic chunks as `[8, 1]`, title input preserves chunk-summary order, and each `TopicOutput` includes full topic transcript plus each chunk's source transcript.

- [ ] **Step 2: Run pipeline tests and verify RED**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_pipeline.py -q`

- [ ] **Step 3: Implement topic assembly using the existing segmenter**

Default to `SlidingTextTilingSegmenter(block_size=2, radii=[3,5,10,15,20], alpha=1.2, min_segment_ratio=0.20)`. Validate returned segment lengths are positive and sum exactly to source utterance count.

- [ ] **Step 4: Write failing compatibility tests**

Test p50/p95/max for utterance count, characters and tokens; truncation rate; empty transcript rate; speaker fallback rate; one-speaker topic rate; and train/dev comparison fields.

- [ ] **Step 5: Implement compatibility audit and run both test files**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_pipeline.py tests/custom_10h_summary/test_compatibility.py -q`

- [ ] **Step 6: Commit Task 5 in the nested repository**

```bash
git -C training-eval-suite add src/evaluate/custom_10h_summary/pipeline.py src/evaluate/custom_10h_summary/compatibility.py tests/custom_10h_summary/test_pipeline.py tests/custom_10h_summary/test_compatibility.py
git -C training-eval-suite commit -m "feat: assemble topic recap evaluation inputs"
```

---

### Task 6: DeepSeek AI Judge, Schema Validation, and Deterministic Scoring

**Files:**
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/rubric.py`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/judge.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_judge.py`

**Interfaces:**
- Produces `RUBRIC_VERSION = "custom10h-topic-summary-v1"` and immutable prompt/schema builders.
- Produces protocol `JudgeTransport.complete(model, messages, temperature) -> str`.
- Produces `DeepSeekTransport(api_key, timeout_seconds)` with the key stored only in memory.
- Produces `judge_topic(topic, transport, model, cache) -> TopicJudgment`.

- [ ] **Step 1: Write failing schema and score tests**

```python
def test_total_is_recomputed_not_trusted(valid_response):
    valid_response["total_score"] = 100
    judgment = validate_and_score(valid_response, topic_fixture())
    assert judgment.total_score == expected_weighted_total(valid_response)

def test_positive_flag_requires_evidence(valid_response):
    valid_response["flags"]["hallucination"] = {"value": True, "evidence_utterance_ids": []}
    with pytest.raises(JudgeSchemaError):
        validate_and_score(valid_response, topic_fixture())
```

- [ ] **Step 2: Run judge tests and verify RED**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_judge.py -q`

- [ ] **Step 3: Implement the source-grounded prompt and validator**

Require one result per chunk; 0–5 component values; title and whole-topic components; four structured flags; short rationale; evidence IDs that exist in the topic. Weight chunk values by utterance count and compute the 60/15/25 total in Python.

- [ ] **Step 4: Implement HTTPS transport and retry behavior**

Load `.env` without printing it, require `DEEPSEEK_API_KEY` and `LLM_MODEL`, POST JSON to `https://api.deepseek.com/chat/completions`, request JSON output, and set temperature 0. Retry two times only for transient HTTP errors or schema failures; include the schema error in the repair prompt. Never include the API key in an exception message.

- [ ] **Step 5: Test retry, cache, and secret redaction**

Use a scripted fake transport: invalid JSON, invalid schema, then valid JSON. Assert three calls, cached rerun makes zero calls, rubric/model changes invalidate cache, and serialized artifacts contain no test API key.

- [ ] **Step 6: Run judge tests and commit**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_judge.py -q`

```bash
git -C training-eval-suite add src/evaluate/custom_10h_summary/rubric.py src/evaluate/custom_10h_summary/judge.py tests/custom_10h_summary/test_judge.py
git -C training-eval-suite commit -m "feat: add cached AI topic summary judge"
```

---

### Task 7: Run Artifacts, Resume Semantics, Aggregation, and Markdown Report

**Files:**
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/artifacts.py`
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/report.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_artifacts.py`
- Create: `training-eval-suite/tests/custom_10h_summary/test_report.py`

**Interfaces:**
- Produces `RunArtifacts(run_dir)` append/read methods for all JSONL files and manifest transitions.
- Produces `aggregate_judgments(judgments, topics, failures) -> dict`.
- Produces `render_report(manifest, compatibility, aggregate, topics, judgments, failures) -> str`.

- [ ] **Step 1: Write failing resume and append tests**

Assert reopening a run indexes completed recording/topic IDs, duplicate completion is not appended, a truncated final JSONL line is reported and ignored, and previous valid lines remain readable.

- [ ] **Step 2: Implement append-safe artifacts and manifest lifecycle**

States are `created`, `running`, `completed`, and `failed`. Persist configuration and checkpoint hashes before stage execution; update counts after every completed source/topic; never store environment values other than the non-secret model name.

- [ ] **Step 3: Write failing aggregation/report tests**

Assert mean, median, standard deviation, p10/p25/p50/p75/p90, flag rates, score buckets by topic length/chunk count, failure count, best/worst topic examples, and compatibility warnings appear in outputs.

- [ ] **Step 4: Implement aggregation and report rendering**

The Markdown report must be reproducible entirely from saved JSON/JSONL and contain no model inference calls.

- [ ] **Step 5: Run tests and commit**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_artifacts.py tests/custom_10h_summary/test_report.py -q`

```bash
git -C training-eval-suite add src/evaluate/custom_10h_summary/artifacts.py src/evaluate/custom_10h_summary/report.py tests/custom_10h_summary/test_artifacts.py tests/custom_10h_summary/test_report.py
git -C training-eval-suite commit -m "feat: persist and report Custom 10h evaluations"
```

---

### Task 8: CLI Orchestration and Stage-Level Resume

**Files:**
- Create: `training-eval-suite/src/evaluate/custom_10h_summary/cli.py`
- Create: `training-eval-suite/scripts/eval_custom_10h_summary.sh`
- Create: `training-eval-suite/tests/custom_10h_summary/test_cli.py`

**Interfaces:**
- Produces `build_parser() -> argparse.ArgumentParser`.
- Produces `run_evaluation(args, dependencies=None) -> Path` returning the run directory.
- CLI invocation: `python -m src.evaluate.custom_10h_summary.cli`.

- [ ] **Step 1: Write failing CLI contract tests**

Test defaults resolve data and all three checkpoints correctly from the repository relationship; `--skip-speaker` fails without compatible labels; `--resume` skips completed sources/topics; `--force-stage judge` reuses topics but invalidates judge artifacts; `--source-id` and `--limit` constrain work deterministically.

- [ ] **Step 2: Run CLI tests and verify RED**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary/test_cli.py -q`

- [ ] **Step 3: Implement orchestration**

Execute stages in order: load → ASR → CAM++ embeddings/labels → segment/recap → compatibility → judge → aggregate/report. Lazy-load ASR, CAM++, ViT5 and BARTpho only when a selected item lacks a valid cache entry. Append failures with `stage`, stable item ID, exception type, safe message and retryability.

- [ ] **Step 4: Implement shell wrapper**

The wrapper changes to the nested repository root, uses the active Python interpreter, and forwards all arguments unchanged. It must not `source` or echo `.env`; Python loads only the two allowed variables.

- [ ] **Step 5: Run the complete fake-dependency suite**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary -q`

Expected: PASS without GPU, network, model downloads, or real API calls.

- [ ] **Step 6: Commit Task 8 in the nested repository**

```bash
git -C training-eval-suite add src/evaluate/custom_10h_summary/cli.py scripts/eval_custom_10h_summary.sh tests/custom_10h_summary/test_cli.py
git -C training-eval-suite commit -m "feat: orchestrate resumable Custom 10h evaluation"
```

---

### Task 9: Dependency Setup, Real Smoke Test, Documentation, and Final Verification

**Files:**
- Create: `training-eval-suite/openwiki/operations/custom-10h-summary-evaluation.md`
- Modify: `training-eval-suite/openwiki/quickstart.md`
- Modify: `training-eval-suite/AGENTS.md`
- Create during run: `training-eval-suite/eval_results/custom_10h_summary/runs/smoke-<timestamp>/...`

**Interfaces:**
- Documents exact setup, smoke, resume, full-run, report-only, and cache-invalidation commands.

- [ ] **Step 1: Install/check the pinned CAM++ toolkit**

Run: `cd training-eval-suite && ./scripts/setup_campp.sh`

Expected: pinned 3D-Speaker checkout exists under `.vendor`, ModelScope/requirements import successfully, and the CAM++ batch script is present.

- [ ] **Step 2: Run a model-only smoke test without AI judge**

Select the smallest valid `source_id` discovered by the loader and run with `--source-id <id> --run-id smoke-models --skip-judge`. Verify ASR transcripts, CAM++ labels, topic outputs, compatibility artifact, and no secret values.

- [ ] **Step 3: Run one-topic AI-judge smoke test**

Run the same source with `--run-id smoke-ai --limit 1`. Confirm `ai_judgments.jsonl`, `aggregate.json`, and `report.md` exist and the computed total matches component weights.

- [ ] **Step 4: Interrupt and resume a controlled smoke run**

Stop after at least one cached stage item, rerun with `--resume`, and confirm logs/artifact counts show no repeated ASR, CAM++ embedding, recap, or judge work.

- [ ] **Step 5: Write operations documentation**

Document prerequisites, the pinned CAM++ revision/model ID, all checkpoint defaults, artifact schemas, rubric weights, input-equivalence checks, cost warning, common failures, and how to regenerate only `aggregate.json`/`report.md` from saved judgments.

- [ ] **Step 6: Run all relevant verification**

Run: `cd training-eval-suite && python -m pytest tests/custom_10h_summary -q`

Run: `python -m pytest tests/unit/test_asr_engine.py tests/unit/test_hierarchical_summarization.py tests/unit/test_seq2seq_inference.py -q`

Run: `git diff --check`

Expected: all tests pass and diff check is clean.

- [ ] **Step 7: Commit documentation in the nested repository and record its pointer in root**

```bash
git -C training-eval-suite add openwiki/operations/custom-10h-summary-evaluation.md openwiki/quickstart.md AGENTS.md
git -C training-eval-suite commit -m "docs: explain Custom 10h summary evaluation"
git add training-eval-suite
git commit -m "feat: add Custom 10h end-to-end summary evaluation"
```

Do not stage unrelated report files or the user's existing uncommitted nested change.
