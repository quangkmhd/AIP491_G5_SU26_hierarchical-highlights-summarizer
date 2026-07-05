"""End-to-end smoke for the streaming UX harness.

Runs the harness with 3 synthetic participants and writes a Markdown
report to docs/generated/streaming-ux-report.md. Asserts the report
has the right shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eval.streaming_ux_harness import main as harness_main


def main() -> int:
    rc = harness_main(["--participants", "3", "--output", "docs/generated/streaming-ux-report.md"])
    report_path = ROOT / "docs" / "generated" / "streaming-ux-report.md"
    if not report_path.exists():
        print(f"FAIL: report not written to {report_path}")
        return 1
    text = report_path.read_text(encoding="utf-8")
    print("=== Report ===")
    print(text)
    if "highlights" in text.lower():
        print("FAIL: report mentions highlights (DR1 should be out of scope)")
        return 1
    if "Time-to-first-chapter" not in text:
        print("FAIL: report missing Time-to-first-chapter metric")
        return 1
    if "Overall streaming UX" not in text:
        print("FAIL: report missing Overall streaming UX metric")
        return 1
    print("OK: report has correct shape")
    return 0


if __name__ == "__main__":
    sys.exit(main())
