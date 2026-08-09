# Custom 10h Human-Only Evaluation Design

## Goal

Make human review the only quality-assessment workflow for Custom_10h. The model pipeline ends after ASR, CAM++, topic segmentation, chunk summarization, and topic titling. It then creates an offline review page and records that human evaluation is pending.

## Pipeline Contract

The evaluator persists transcripts, speaker labels, topic outputs, input-compatibility diagnostics, failures, and `human_evaluation.html`. It does not produce quality scores or aggregate quality reports. The run manifest records `evaluation_mode: human` and `human_evaluation_status: pending`; pipeline completion does not imply completion of human review.

The CLI has no credential-file option and no remote-scoring controls. Resume and forced-stage behavior remains content-addressed for ASR, speaker, and topic-generation stages.

## Human Results

Reviewers score every topic in the offline page. Browser storage is temporary working state. **Xuất JSON** creates the portable human-evaluation result. Until that export is completed and collected, documentation must describe the result as pending rather than attribute a quality score to a person.

## Data Retention

Keep reusable acoustic/model outputs and topic evidence. Remove obsolete scored artifacts and their cache namespace from both completed Custom_10h runs. Generate a human-review page for every retained run that has topic outputs. Historical quality numbers are not retained in operations documentation.

## Verification

Tests prove that the evaluator runs without credentials, creates the human-review page, writes human-only manifest fields, and exposes no obsolete scoring CLI options. Repository scans verify that the Custom_10h source, tests, and operations documentation contain only the human workflow.
