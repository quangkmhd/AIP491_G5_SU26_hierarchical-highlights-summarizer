# runtime-001+002+streaming — FastAPI SSE + CLI stream (Archived)

**Goal:** Expose StreamingOrchestrator over HTTP (SSE) and CLI (NDJSON).

**Result:** FastAPI app with /process (batch) + /stream (SSE) routes; argparse CLI with process|stream subcommands. 10 new tests (5 unit CLI + 4 integration API + 1 layer rule).

**Verification at archive time:** Full suite green (210/210); branch merged.
