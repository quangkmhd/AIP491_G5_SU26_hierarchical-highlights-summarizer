# ui-001+002+streaming — Web Prototype (Hierarchical, Streaming) (Archived)

**Goal:** Single-page web prototype for the streaming Hierarchical recap (no Highlights tab).

**Result:** src/ui/{__init__,index.html,styles.css,app.js}; src/runtime/api.py serves UI at / and static at /static. 4 Playwright structure tests.

**Verification at archive time:** Full suite green (214/214); branch merged.

**Known limitation:** End-to-end Playwright streaming test (click Process and assert chapter card appears) was simplified to structure-only tests due to the ~30s model load on first request and SSE event flow taking >60s. Manual curl verification confirms the API works correctly (see `tests/integration/test_api_streaming.py` for the integration-level test).
