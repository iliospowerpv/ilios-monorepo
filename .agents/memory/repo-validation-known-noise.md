---
name: Known pre-existing validation noise (ilios-server tests + FE tsc)
description: Pre-existing test/typecheck failures unrelated to current work, so future validation runs don't waste time chasing them.
---

# Pre-existing failures that are NOT your regression

When validating changes, these fail on the base code independent of your edits. Confirm they live in files you did not touch (via `git diff --stat`) before assuming you caused them.

## Backend (`backend/ilios-server`, pytest)
- `tests/test_in_app_parsing_service.py::TestTextExtraction::*` — the tests `patch` `extract_text_from_pdf` to return the **string** `"PDF text"`, but the deprecated `extract_text()` does `text, _ = extract_text_from_pdf(...)`. Unpacking a string raises `ValueError: too many values to unpack`. The real helper returns a 2-tuple; the test mock is out of sync. Pre-existing.
- `tests/test_parsing_idempotency.py::*` — insert `ai_parsing_results` with `file_id=999` and no matching `files` row → `ForeignKeyViolation` under conftest `create_all` (FKs enabled). Pre-existing test-data setup gap in this harness.
- General harness gotchas live in `backend-test-harness.md` (needs `test_db_name` env + own DB; override the coverage `addopts`; no `pytest-mock`).
- `tests/test_extraction_registry.py` DOES pass cleanly — use it as the signal for extraction-registry changes.

## Frontend (`frontend/rea-investment-fe`, `npx tsc --noEmit`)
- All `tsc --noEmit` errors are confined to `**/__tests__/*.test.tsx` fixtures with stale mock objects missing fields added by prior sprints (e.g. `timezone`, `das_connection_name`, `telemetry_site_name`, `ai_supported`, `dc_wiring_loss`, `sites_decommissioned`). App source compiles clean.
- The webpack dev server / `node scripts/build.js` build uses Babel and does **not** typecheck, so the app builds and serves (HTTP 200) despite these test-file type errors. To check only app source: `npx tsc --noEmit 2>&1 | rg "error TS" | rg -v "__tests__|\.test\."` → expect zero.
