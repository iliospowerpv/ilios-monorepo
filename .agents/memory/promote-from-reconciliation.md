---
name: Promote-from-Reconciliation action layer
description: How the candidate→active promotion (and Create Task hand-off) is surfaced on the read-only Reconciliation tab, and the guardrails that must never be loosened.
---

# Promote-from-Reconciliation action layer

The Reconciliation tab stays a **read-only audit view** (see dd-reconciliation-view). Promotion and "Create Task" are an additive *action layer* on top of it — they reuse EXISTING backend endpoints and add no backend/endpoint/migration/task-schema changes.

Promotion endpoints live under `/api/projects/{site_id}/assumptions/*` (NOT under due-diligence): `POST /promotion/diff {file_id}`, `POST /promote {document_id, file_id, notes?}`. Row→id mapping: `document_id ← row.document_id`, `file_id ← row.document_version_id`.

## Guardrails (do not loosen)
- **Acceptance/override stays in Data Room.** This layer only promotes already-accepted values (`accepted_not_promoted` rows). It adds no accept/override controls; acceptance-oriented statuses keep their Data Room deep link.
- **Never field-level promote.** Promotion is **file-version-scoped + all-or-nothing**: it promotes every accepted value on that document version, not just the launched row. The reconciliation grid shows one row per field, so the promote dialog MUST say explicitly "not just this row/field" or it implies a false 1-row=1-field scope.
- **Always show a live, re-fetched full diff (blast radius) before promote.** Re-fetch the diff at confirm time; if it differs from the reviewed payload, BLOCK promotion, re-render, and force a second confirm. Disable confirm when `has_changes=false`.
- **`removed` diff rows are informational only** — promotion never retires/deletes them; label them as such.
- **Promote ≠ baseline update.** Success copy must state the active baseline / expected math was NOT updated. Never touch baselines/expected/telemetry.

## Permission gate (FE convenience only; backend stays authoritative)
`user.is_system_user || user.role.permissions['Diligence'].edit` (via `useAuth()` from contexts/auth/auth). Read-only users see no promote/task buttons. Also require a valid numeric site id.

**Why:** the reconciliation surface had no write path; the temptation is to "just promote this one field," which would silently re-baseline a whole document version and bypass the Data Room acceptance audit. The diff-reconfirm + version-scope copy + baseline-not-updated messaging exist to keep the action honest.

**How to apply:** when extending this layer (Phase 2: richer task description with provenance IDs/deep links, per-field intent), keep all guardrails above; enrich description/UX only.
