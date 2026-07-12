# Handoff Report: Thesis Validation and Codebase Verification

This handoff report summarizes the findings of the scientific accuracy validation and codebase verification of the Vietnamese Meeting Summarization system.

---

## 1. Observation

We directly observed several discrepancies, formatting errors, and codebase failures:

### 1. LaTeX Rendering and Indexing Mismatches
* **Line 49 of `Khoa_luan_Streaming_Meeting_Summary_hoan_chinh.md`** contains double backslashes in the inline formula:
  > `kết hợp điểm sâu ở các bán kính $\\{3, 5, 10, 15, 20\\}$`
* **Line 112 and 115 of `Khoa_luan_Streaming_Meeting_Summary_hoan_chinh.md`** define the block-level BoW sums:
  > `$$ B_L^i(w) = \sum_{j=\max(0, i-k+1)}^{i} b_j(w) $$`
  > `$$ B_R^i(w) = \sum_{j=i+1}^{\min(n-1, i+k)} b_j(w) $$`
  while the sequence is 1-indexed: $U = (u_1, u_2, \dots, u_n)$.

### 2. Hyperparameter Discrepancies
* **Line 148 of `Khoa_luan_Streaming_Meeting_Summary_hoan_chinh.md`** reports the selected configuration:
  > `gồm block_size = 2, alpha = 1.5, radii = [3,5,10,15,20] và min_segment_ratio = 0.1`
* **`src/config/text_tiling.py` (Lines 43-66)** defines different codebase defaults:
  > `block_size: int = Field(default=3, ...)`
  > `alpha: float = Field(default=0.9, ...)`
  > `min_segment_ratio: float = Field(default=0.08, ...)`

### 3. Factual Typo in Environment Specs
* **Line 272 of `Khoa_luan_Streaming_Meeting_Summary_hoan_chinh.md`** details:
  > `PyTorch 2.13.0+cu130; Transformers 5.13.1`
  while `pyproject.toml` (Lines 7-8) declares `"torch>=2.6.0"` and `"transformers>=5.12.0"`.

### 4. Broken `win_diff` Metric Code
* **`src/eval/segmentation_metrics.py` (Lines 50-55)** implements WindowDiff as:
  ```python
  for i in range(n - window):
      pred_diff = pred_set[i] != pred_set[i + window]
      true_diff = true_set[i] != true_set[i + window]
      if pred_diff != true_diff:
          mismatches += 1
  ```
  This is identical to `pk` (Lines 31-36), meaning WindowDiff behaves exactly like P_k and does not count boundaries inside the window.

### 5. Pytest Execution Failures
* Running `uv run pytest` fails with the following log:
  ```
  src.data.eval_loader.DataLoaderError: /home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary/data/eval_vi/meeting_ami.json sample #0 failed validation: 2 validation errors for DialogueSample
  summary
    Extra inputs are not permitted [type=extra_forbidden, input_value="welcome Um I'll briefly ...", input_type=str]
  summary_vi
    Extra inputs are not permitted [type=extra_forbidden, input_value="the remote control, but ...", input_type=str]
  ```
  while `src/data/dialogue_sample.py` (Line 20) inherits from `BaseSchema`, which enforces `extra="forbid"`.

---

## 2. Logic Chain

1. **LaTeX Inline Formula Bug**: Inline LaTeX math in markdown uses single backslashes `\` to escape curly braces `{` and `}`. Double backslashes `\\` are interpreted as a KaTeX line-break or formatting syntax error, rendering the formula broken.
2. **Indexing Mismatches**: Since the utterance sequence $U$ is defined as 1-indexed (from 1 to $n$), the left block summation $B_L^i$ starting at $\max(0, \dots)$ references index 0 (which is out of bounds). The right block $B_R^i$ ending at $\min(n-1, \dots)$ fails to include the final utterance $u_n$ when the window is near the end.
3. **Hyperparameter Mismatch**: The thesis claims to use a specific set of optimized parameters (`block_size=2`, `alpha=1.5`, `min_segment_ratio=0.1`) found on development sets. However, the codebase defaults are different. Running the codebase without overrides will run with sub-optimal parameters compared to the reported academic results.
4. **Invalid WindowDiff Metric**: WindowDiff is designed to count the number of boundaries in a sliding window and penalize difference mismatches. However, the python code checks only endpoint equality (`pred_set[i] != pred_set[i + window]`), identical to P_k. Therefore, the WindowDiff results reported in the evaluation scripts are mathematically identical to P_k, representing a scientific implementation bug.
5. **DataLoader Failure**: `meeting_ami.json` contains `summary` and `summary_vi` keys. Since `DialogueSample` inherits from `BaseSchema` which sets `extra="forbid"`, the loading process throws a validation error, crashing the evaluation runner.

---

## 3. Caveats

* We operated strictly in **read-only** mode and did not modify the source code or configurations to resolve the failing tests or bugs.
* We assumed that the quantitative tables in the thesis report were generated with the corrected formulas or via a separate evaluation run before the codebase's refactoring, since P_k and WD values in the tables are slightly different.

---

## 4. Conclusion

The thesis contains mathematical indexing errors, LaTeX rendering bugs, and environment version typos. Crucially, the codebase suffers from two major implementation errors: a broken `win_diff` metric that duplicates `pk`, and a Pydantic strict validation crash (`extra="forbid"`) when loading the `meeting_ami` dataset. To resolve these, the math formulas in the thesis must be corrected, hyperparameter defaults should be synchronized, and the two codebase bugs must be patched.

---

## 5. Verification Method

To verify these findings:
1. **Pytest Failure Verification**: Run `uv run pytest` inside `/home/quangnhvn34/dev/me/AIP491/tools/15-Meeting-summary`. Observe the validation errors on `DialogueSample` for `meeting_ami.json`.
2. **Metric Code Verification**: Inspect `src/eval/segmentation_metrics.py` and compare `win_diff` against `pk` to confirm they share the same binary endpoint check.
3. **Formula Rendering Verification**: Open `report_compilation/Khoa_luan_Streaming_Meeting_Summary_hoan_chinh.md` in a Markdown viewer with KaTeX support, and verify that line 49 exhibits rendering errors.
