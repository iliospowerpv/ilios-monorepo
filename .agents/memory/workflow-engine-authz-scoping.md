---
name: Workflow engine option/prereq authz scoping
description: Why native workflow dropdown resolvers & prerequisites must scope by module permission, not entity visibility.
---

# Workflow engine dynamic options & prerequisites must mirror the target endpoint's permission

The native Workflow Engine populates wizard dropdowns via `resolve_options(...)` and shows
read-only "blocked" prerequisites via the prerequisite evaluators. For any resolver/evaluator that
fronts a **permission-gated** domain (e.g. the Data Room: `accessible_projects`,
`project_documents`, `document_files`, `has_accessible_project`, `has_uploaded_file`), scope by the
**same module permission the underlying endpoint enforces** — NOT by mere entity/site visibility.

Concretely: scope the visible-candidate sites down to the caller's **Diligence `edit`** set by
re-checking the canonical per-context module permission for each site (fail-closed; platform-bypass
is unrestricted). Membership resolvers stay company-admin scoped.

**Why:** A read that returns labels/ids is still a disclosure. Site visibility is broader than
Data-Room management rights, so scoping a Data-Room dropdown by visibility leaks project/document/
file **names** (and falsely reports a prerequisite as "met") to a user who can *see* a project but
cannot manage its Data Room. An architect review flagged exactly this as a blocking metadata-
disclosure bug.

**How to apply:** When adding a new option resolver or prerequisite that reads a permission-gated
domain, find the permission the real list/upload/parse endpoint requires and reuse that exact
module/action via `require_module_permission` per candidate context. Never substitute
`get_limited_sites_ids()` / visibility for the permission gate. Prereqs/options are advisory and
read-only — the executing endpoint stays the authoritative guard — but they must not over-disclose.
Regression coverage lives in `tests/test_workflow_engine.py` (visible-but-no-Diligence-edit cases).
