# SECURITY.md

This file defines the security and safety rules that agents must not guess at.

## Secrets And Credentials

- Never hard-code secrets in source or docs.
- Document approved secret-loading paths here.
- Redact tokens, API keys, and personal data from logs and screenshots.

### Approved secret-loading paths

- The repo's `.env` is empty by design (`touch .env`); populate it with local
  values during development and add to `.gitignore` (already done).
- `src/config/` (when implemented) may read via `python-dotenv`; do not commit
  real keys.
- HuggingFace model checkpoints in `vibert_checkpoints_vi/*.pth` are
  > 450 MB binary files and are excluded from the repo via `.gitignore`.
  Pull them through approved HuggingFace authenticated download paths.

## Untrusted Input

- Treat external content as untrusted until validated.
- Record allowed fetch or execution boundaries here.
- If prompt injection or command injection risk exists, document the guardrail.

### Untrusted-input guardrails already in place

- `src/types/_base.py::BaseSchema` enforces `extra="forbid"` on every model, so
  any unexpected JSON key in a meeting transcript is rejected at the API
  boundary with a `ValidationError`.
- `Utterance` is `frozen=True`, so malicious code that tries to rewrite a
  parsed utterance in-place will fail with a `ValidationError` instead of
  silently mutating the transcript.
- `DialogueTranscript` validates that utterance indices form a contiguous
  0..N-1 sequence, blocking re-ordering or duplication attacks.
- `DialogueTranscript.MAX_UTTERANCES = 5000` is enforced in
  `_validate_transcript`, blocking memory-exhaustion attacks via
  over-sized payloads.
- `TranscriptIngestionRequest.materialize()` re-checks the same limit at the
  request boundary, so an oversized `flat_texts` list is rejected with a clear
  `ValueError` before it reaches the service layer.

## External Actions

- List which actions require explicit approval.
- Record any production or destructive commands that agents must not run by default.
- Prefer sandbox-safe workflows for debugging and verification.

### External actions requiring explicit approval

- Any `git push` to a remote branch (per `AGENTS.md`).
- Any `rm -rf` outside the workspace or in shared cache directories.
- Downloading HuggingFace checkpoints > 100 MB.
- Running the production summarization pipeline (depends on `model-002` and
  `svc-002`; not yet available).

## Dependency And Review Rules

- New dependencies need justification in the active plan.
- Security-sensitive changes require explicit verification steps.
- Repeated security review comments should become checks, not tribal knowledge.

### Dependency additions planned for upcoming work

- `pydantic >= 2` (already managed by uv) -- data validation.
- `transformers` (planned for `model-002`) -- HuggingFace model loading.
- `python-dotenv` (planned for `config`) -- `.env` loading.
- `fastapi` + `uvicorn` (planned for `api-001`) -- HTTP runtime.
- `pytest` is intentionally **not** added; the repo uses `unittest` from the
  standard library to keep the dependency surface minimal.
