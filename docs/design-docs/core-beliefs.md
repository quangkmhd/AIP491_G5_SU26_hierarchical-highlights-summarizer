# Core Beliefs

- The repository is the system of record for agents.
- `AGENTS.md` is a router, not an encyclopedia.
- Verification evidence matters more than confidence.
- One bounded task is better than many half-finished tasks.
- Repeated human feedback should become reusable harness rules.
- Cleanup and simplification are part of shipping, not afterthoughts.
- If an agent cannot discover a fact in-repo, treat that fact as operationally unavailable.
- A code review that finds Important or Critical issues must result in code
  changes *in the same session*, not a new feature branch. Defer only Minor
  items, and write them to `docs/exec-plans/tech-debt-tracker.md`.
- Naming must describe the *concept*, not the feature id, the build order, or
  the author's initials. Test files live under `tests/` and are named by the
  layer or the input they exercise.
- The Types layer never imports from `config`/`repo`/`service`/`runtime`. If
  you find yourself wanting to, the design is wrong.
