# config-001+ — Drop HighlightsConfig Implementation Plan (Archived)

**Goal:** Remove HighlightsConfig from the Config layer (DR1 dropped).

**Result:** MeetingRecapConfig composes 4 sub-configs (TextTilingConfig, ChunkingConfig, AbstractiveConfig, LanguageConfig). HighlightsConfig is deleted along with all tests and references.

**Verification at archive time:**
- `python3 -m unittest discover -s tests -v` → 135/135 OK
- AST layer-rule test still green
- `feature_list.json` config-001+ status: passing
- Branch `feat/config-001-plus` merged to main
