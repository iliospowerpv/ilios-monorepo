---
name: Document Identity & Expected Documents
description: Foundation that formalizes the Document row as logical identity and adds a static per-stage Expected Documents catalog.
---

# Document Identity & Expected Documents

The existing `documents` row IS the canonical logical Document Identity — there is NO
separate identity table. Identity is additive metadata only and changes no lifecycle.

- Resolution precedence for the canonical/display name: `canonical_name` -> `custom_name` -> enum `name.value`.
- `aliases` is JSONB, treated as `[]` when NULL.
- Read-only this phase: there is intentionally NO identity write endpoint. Backfill only adopts
  an existing `custom_name` into `canonical_name`.

Expected Documents are a **static Python catalog** (`helpers/due_diligence/expected_documents.py`)
built over `document_name_section_mapper`. Definitions only — they NEVER materialize a
Document/File row, and do no present/missing matching server-side (that is a later phase).
`required` defaults True (these are DD requirements); tune per-doc via `EXPECTED_DOCUMENT_OVERRIDES`.

**Why:** The whole feature family is additive/flag-safe and must reuse existing promotion/
archive/move-stage/Diligence permissions; fabricating placeholder rows or a parallel identity
store would violate the "Site is canonical, additive-only" invariant.

## FastAPI route-ordering gotcha (documents router)
On `app/routers/due_diligence/documents.py`, dynamic routes like `/{document_id}` are typed
`document_id: int` but Starlette still matches ANY string segment first, then FastAPI 422s —
it does NOT fall through to a later static route. So any new STATIC GET (e.g. `/expected-documents`)
MUST be registered BEFORE `/{document_id}`, or it is shadowed and returns 422.
**How to apply:** put new literal-path GETs above the `/{document_id}` handler in this router.
