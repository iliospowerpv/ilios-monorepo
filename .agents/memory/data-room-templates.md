---
name: Data Room Templates
description: Company-scoped reusable Data Room structure templates; how they snapshot/apply and where they plug into site creation.
---

# Data Room Templates

Reusable, company-scoped capture of a Data Room's **structure only** — stages, expected documents, ordering, descriptions, guidance, optionality. Templates NEVER carry files, versions, file metadata, approvals, or history.

## Permanent rule (user-mandated invariant)
Templates are **immutable snapshots of structure**. Applying a template is a **creation operation, not a synchronization operation** — existing Data Rooms are NEVER silently reconciled to a template. **Why:** a template defines expected structure at one point in time; treating apply as "sync to existing" would be a destructive merge (duplicating/overwriting live sections, expected-document slots, and the files/approvals attached to them). **How to apply:** any future "apply" affordance (including from the Manage Templates surface) must scaffold a *new* Data Room via the existing site-creation path; never add a "reconcile/update this existing Data Room from template" code path. Mirrored in `replit.md` Key invariants.

## Key design facts
- **Routes are site-nested**, not company-nested: `/api/due-diligence/{site_id}/document-templates`. Authz via `get_authorized_site` + Diligence view (read) / edit (mutate). A template's `company_id` must equal the site's company; cross-company access is rejected.
- Because listing is site-nested, the **creation dialogs** (AddProjectDialog / CreateProjectDialog) must resolve a *representative* site of the chosen company first (`assetManagement.sites({company_id, limit:1})`) to list company-scoped templates. If the company has no sites, no templates exist anyway → graceful empty.
- **Apply path reuses existing DD scaffolding helpers** — template apply builds section mappers then calls the same apply helper the default site-creation path uses; do not duplicate scaffolding logic. Snapshot→apply is a structural round-trip (sections/docs/order/descriptions reproduced).
- **Site creation integration**: optional `template_id` on `CreateSiteSchema`; when present, apply template after the site exists; when absent, behavior is unchanged (default helpers). Additive, "Site" stays canonical.
- **Authz on the apply path**: the create endpoint already requires `assets_management:edit`, but applying a template is a *Diligence action*, so when `template_id` is supplied the endpoint must ALSO require `Diligence:edit` — fail-closed BEFORE the template lookup or site-row create. **Why:** "all template actions use existing Diligence permissions"; gating only on AM edit lets an AM-edit-without-Diligence caller scaffold a Data Room from a template (broken access control). **How to apply:** any new path that consumes/applies template structure must mirror the Diligence gate, not just the host module's permission.

## Gotchas
- FE `Params` type (src/api/user.ts) lacks `company_id`; pass a locally-typed variable (not a fresh object literal) to `sites()` to dodge the excess-property TS error.
- Permission gate pattern in FE: `user?.is_system_user || user?.role?.permissions?.['Diligence']?.view|edit` (useAuth from src/contexts/auth/auth.tsx).
- Backend test cmd: `cd backend/ilios-server && test_db_name=heliumdb_test python -m pytest <path> -p no:cacheprovider -o addopts="" -q`.
