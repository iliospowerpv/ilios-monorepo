---
name: DD acceptance read path is file-version-scoped
description: Why combine_user_ai_parsing_results must scope document_keys to the viewed file version, matching the file-scoped write path.
---

Due-diligence acceptance is stored PER FILE VERSION, but `Document.keys` spans
every version of a document. Any read/aggregate over `document.keys` that
reports "accepted" state MUST scope to the file version being viewed, or a newer
version inherits an older version's accepted values.

**Rule:** when a concrete file version is in play, treat a `document_key` as the
viewed version's accepted value only if `file_id == <viewed file>.id` OR
`file_id IS NULL` (legacy document-level key). File-specific keys override
legacy NULL-file keys for the same field name. With no file in context, use all
keys (back-compat).

**Why:** the WRITE path is file-scoped — `bulk_accept` creates/updates
`document_keys` with `file_id=file.id` and creates candidate `project_facts`
keyed on `source_file_id`. The original `combine_user_ai_parsing_results` read
`document.keys` unscoped, so a freshly uploaded version (0 keys, 0 candidate
facts of its own) showed every field's `value` populated from the prior
version's accepted keys → "Accept All" rendered "Accepted"/completed while
"Promote" stayed (correctly) unavailable because no candidate facts existed.
The symptom looks run-related ("it has a second run") but the real axis is the
FILE VERSION, not the parse run.

**How to apply:** in `app/helpers/files/file_helper.py` the scoping lives in
`combine_user_ai_parsing_results` (sort NULL-file keys first, let the name-keyed
dict keep the last/file-specific assignment). If you add another surface that
summarizes DD acceptance from `Document.keys`, apply the same file scoping.
Note: `document_keys` has NO `run_id` column — acceptance is file-scoped, not
run-scoped, so run-level staleness (accept run N, reprocess to run N+1, keys
persist) is a SEPARATE unsolved concern needing run provenance, not this fix.
