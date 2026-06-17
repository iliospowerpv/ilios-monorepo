---
name: Promote-from-Reconciliation action layer
description: The non-obvious guardrails for surfacing candidate→active promotion on the read-only Reconciliation tab. Constraints only — find the endpoints/mappings in the code.
---

# Promote-from-Reconciliation action layer

The Reconciliation tab stays a **read-only audit view** (see dd-reconciliation-view). Promotion and "Create Task" are an additive *action layer* on top of it that must reuse EXISTING endpoints — no backend/endpoint/migration/task-schema changes.

## Guardrails (do not loosen)
- **Acceptance/override stays in the Data Room.** This layer only promotes already-accepted values; it adds no accept/override controls. Acceptance-oriented statuses keep their Data Room deep link.
- **Never field-level promote.** Promotion is **file-version-scoped + all-or-nothing**: it promotes every accepted value on the document version, not just the launched row. The grid shows one row per field, so the dialog MUST say "not just this row/field" or it implies a false 1-row=1-field scope.
- **Always show a live, re-fetched full diff (blast radius) before promote.** Re-fetch at confirm time; if it differs from what was reviewed, BLOCK, re-render, and force a second confirm. Disable confirm when there are no changes.
- **`removed` diff rows are informational only** — promotion never retires/deletes them; label as such.
- **Promote ≠ baseline update.** Success copy must state the active baseline / expected math was NOT updated. Never touch baselines/expected/telemetry.
- Frontend permission gating is convenience only; the backend `Diligence:edit` check stays authoritative.

**Why:** the reconciliation surface had no write path; the tempting shortcut is "promote this one field," which would silently re-baseline a whole document version and bypass the Data Room acceptance audit. The diff-reconfirm + version-scope copy + baseline-not-updated messaging keep the action honest.

**How to apply:** when extending this (e.g. richer task provenance, document-version display in the dialog), keep every guardrail above; enrich description/UX only. Spec of record: `docs/promote_from_reconciliation_audit.md`.
