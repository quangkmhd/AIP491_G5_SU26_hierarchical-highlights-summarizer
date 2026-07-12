# context.md — Thesis Review and Evaluation Context

## Context
- **Target Thesis Report**: `/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/report_compilation/Khoa_luan_Streaming_Meeting_Summary_hoan_chinh.md`
- **System Summary Report**: `/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/report_compilation/system_summary_report.md`
- **Output Report Path**: `/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/report_compilation/thesis_review_report.md`
- **Ecosystem**: Meeting Summarization system with streaming, segmenting (TextTiling, sliding window), and translation capabilities.
- **Evaluation Standards**: PluginEval/evaluation-methodology, academic quality standards.

## Codebase Map
- **Config & Source Code**: Look for scoring configs, system hyperparameters, default prompts under `src/` or similar.
- **Evaluation Results**: Look under `data/`, `logs/`, or test suites.

## Identified Metrics & Components to Verify
- Mathematical formulas for segmentation (e.g. TextTiling, cosine similarity, WindowDiff, Pk)
- ROUGE scores ($ROUGE-1, ROUGE-2, ROUGE-L$)
- Performance metrics ($P_k$, $WindowDiff$)
- Throughput and latency figures
- LaTeX parser compatibility of all inline and display math.
