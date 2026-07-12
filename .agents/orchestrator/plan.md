# plan.md — Thesis Review and Evaluation Plan

This plan details the steps to review and evaluate the streaming meeting summary thesis report for academic and methodology quality.

## Milestones

1. **Information Gathering & Initial Analysis**
   - **Objectives**: Inspect the thesis document, system summary report, codebase, and evaluation reports. Verify codebase configuration defaults.
   - **Assignee**: `explorer` (`teamwork_preview_explorer`)
   - **Verification**: Explorer produces `handoff.md` with complete evidence chains.

2. **Formulas & Metrics Verification**
   - **Objectives**: Validate mathematical formulas (LaTeX formatting) and check $F_1$, $P_k$, WindowDiff, ROUGE, throughput, and latency metrics against the actual system implementation.
   - **Assignee**: `explorer` (`teamwork_preview_explorer`)
   - **Verification**: Evidence-backed verification log in `handoff.md`.

3. **Report Drafting & Compilation**
   - **Objectives**: Write the structured evaluation report at `/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/report_compilation/thesis_review_report.md`.
   - **Assignee**: `worker` (`teamwork_preview_worker`)
   - **Verification**: Verifiable draft report exists at the destination path.

4. **Review & Validation**
   - **Objectives**: Audit the compiled report for academic rigour and completeness. Check all LaTeX formats parse correctly.
   - **Assignee**: `reviewer` (`teamwork_preview_reviewer`)
   - **Verification**: Reviewer handoff confirms complete compliance and accuracy.
