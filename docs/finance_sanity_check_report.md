# Finance Module Sanity Check Audit Report

**Date:** January 26, 2026  
**Scope:** Data model verification, navigation contract, lifecycle handling, Finance module boundaries, test data safety

---

## Executive Summary

The audit confirms that the Ilios platform architecture is sound. **"Project" is correctly implemented as a UI-only terminology change** - the canonical entity remains the `Site` table. No separate "Project" entity/table exists. The Finance module properly operates as a capital governance engine without general ledger functionality. Navigation remains stable across all lifecycle states.

---

## 1. Data Model Verification

### Finding: COMPLIANT

#### Canonical Entity: `Site` (table: `sites`)
- **Location:** `backend/ilios-server/app/models/site.py` (line 100-155)
- **Primary Key:** `id` (Integer, Identity)
- **Parent:** `company_id` (FK to `companies.id`)
- **Status:** The `Site` model is the single source of truth for physical asset records

#### "Project" Implementation: UI TERMINOLOGY ONLY
- **No `projects` table exists** in the database
- **`UserProject`** (table: `user_projects`) is a **junction table for access control**, NOT a separate entity
  - Location: `backend/ilios-server/app/models/user.py` (line 72-82)
  - Purpose: Links users to sites and companies for permission scoping
  - Contains: `user_id`, `site_id`, `company_id` (all FKs)
  - This is correctly named for its RBAC function, not a new entity

#### Foreign Key Integrity: VERIFIED
All modules correctly reference the canonical `sites` table:

| Module | Model | FK Reference |
|--------|-------|--------------|
| Finance | `FinanceBudget` | `site_id` → `sites.id` |
| Finance | `FinanceObligation` | `site_id` → `sites.id` |
| Finance | `FinanceActual` | `site_id` → `sites.id` |
| Telemetry | `TelemetrySiteMapping` | `site_id` → `sites.id` |
| Documents | `Document` | `site_id` → `sites.id` |
| Devices | `Device` | `site_id` → `sites.id` |

**Conclusion:** No rollback needed. The data model is correctly structured.

---

## 2. Routing + Navigation Contract

### Finding: MOSTLY COMPLIANT (Minor clarifications possible)

#### Global Navigation (Sidebar)
**Location:** `frontend/rea-investment-fe/src/components/layout/NavMenu/NavMenu.tsx` (lines 68-82)

| Menu Item | Path | Status |
|-----------|------|--------|
| My Portfolio | `/my-portfolio` | OK |
| Dashboard | `/dashboard` | OK |
| O&M | `/operations-and-maintenance` | OK |
| Diligence | `/due-diligence` | OK |
| Finance | `/finance` | OK |
| Asset Management | `/asset-management` | OK |
| Reports | `/reports` | OK |

**No ambiguous "Overview" label exists in the global sidebar navigation.**

#### "Overview" Tab Usage (ACCEPTABLE)
The term "Overview" is used **within entity detail pages as a tab label**, not as a global nav item. This is appropriate because:

1. Context is always clear from breadcrumbs (e.g., `Asset Management > Acme Corp > Solar Site 1 > [Overview tab]`)
2. "Overview" tabs exist at multiple scopes as designed:
   - **Module level:** Asset Management root page has an Overview tab (portfolio-level summary)
   - **Company level:** Company detail pages have Overview tabs (company-level summary)
   - **Project/Site level:** Site detail pages have Overview tabs (site-level canonical record)
   - **Device level:** Device detail pages have Overview tabs (device-level details)

**Locations of Overview tabs:**
- `frontend/rea-investment-fe/src/modules/asset-management/pages/AssetManagement/AssetManagement.tsx:24`
- `frontend/rea-investment-fe/src/modules/asset-management/pages/AssetManagementCompanyDetails/AssetManagementCompanyDetails.tsx:36`
- `frontend/rea-investment-fe/src/modules/asset-management/pages/AssetManagementSiteDetails/AssetManagementSiteDetails.tsx:36`
- `frontend/rea-investment-fe/src/modules/operations-and-maintenance/pages/CompanyDetails/CompanyDetails.tsx:38`
- `frontend/rea-investment-fe/src/modules/operations-and-maintenance/pages/SiteDetails/SiteDetails.tsx:40`
- `frontend/rea-investment-fe/src/modules/due-diligence/pages/Site/SiteDetails.tsx:49`
- `frontend/rea-investment-fe/src/modules/settings/pages/MyCompany/MyCompany.tsx:35`

#### Route Map: Portfolio → Company → Project Flow

```
Portfolio Level:
├── /my-portfolio                    → User's assigned projects across companies
├── /asset-management                → Portfolio-wide overview
├── /finance                         → Finance landing (company selection)
├── /operations-and-maintenance      → O&M landing
├── /due-diligence                   → Due Diligence landing
└── /reports                         → Reports landing

Company Level:
├── /asset-management/companies/:companyId         → Company detail
├── /finance/companies/:companyId                  → Company finance summary
├── /operations-and-maintenance/companies/:companyId → Company O&M
└── /due-diligence/companies/:companyId            → Company diligence

Project (Site) Level:
├── /asset-management/companies/:companyId/sites/:siteId        → Project overview (canonical record)
├── /finance/companies/:companyId/sites/:siteId                 → Project finance
├── /operations-and-maintenance/companies/:companyId/sites/:siteId → Project O&M
└── /due-diligence/companies/:companyId/sites/:siteId           → Project diligence
```

#### Breadcrumb Implementation: CORRECT
**Location:** `frontend/rea-investment-fe/src/handles/handles.ts`

Each route uses `RouteHandle.createHandle()` with a `crumbsBuilder` function that dynamically generates breadcrumbs showing the navigation hierarchy. Examples:

- Asset Management Site Details: `Asset Management > [Company Name] > [Site Name]`
- Finance Site Details: `Finance > [Company Name] > [Site Name]`

**Conclusion:** Navigation is clear and unambiguous. No changes required.

---

## 3. Contextual Activation by Lifecycle

### Finding: COMPLIANT

#### Lifecycle State Field: EXISTS
**Location:** `backend/ilios-server/app/models/site.py` (lines 215-219)

```python
class SiteStatuses(enum.Enum):
    construction = "Construction"
    placed_in_service = "Placed in Service"
    decommissioned = "Decommissioned"
    sold = "Sold"
```

**Storage Location:** `SiteAdditionalFieldList.status` (line 256)
```python
status = Column(Enum(SiteStatuses), nullable=True)
```

#### Global Navigation: STABLE
All modules remain visible in the sidebar regardless of site lifecycle state. **Navigation is NOT gated by lifecycle.** This is correct behavior.

#### Module-by-Module Lifecycle Handling:

| Module | Lifecycle-Aware? | Implementation |
|--------|-----------------|----------------|
| **Finance** | Yes | `finance_ready` flag shows readiness status; `missing_prerequisites` array lists blockers; always accessible |
| **Asset Management** | Partial | Status displayed in Site Level Details card; actions remain available |
| **O&M** | Implicit | Telemetry-dependent widgets would show no data for non-operational sites |
| **Due Diligence** | No explicit handling | Documents and tasks remain accessible regardless of state |

#### Recommendations (NO CODE CHANGES NOW):
1. O&M module could show "No telemetry available - Project not yet Placed in Service" message when `status !== 'placed_in_service'` and telemetry is empty
2. Due Diligence could show lifecycle-aware messaging on the Overview tab
3. These are enhancements, not blockers

**Conclusion:** Lifecycle handling is appropriately contextual. Global navigation remains stable.

---

## 4. Finance Module Boundaries Check

### Finding: COMPLIANT

#### Finance Module Purpose: Capital Governance Engine
**Location:** `backend/ilios-server/app/models/finance.py`

#### Verification Checklist:

| Check | Status | Evidence |
|-------|--------|----------|
| No double-entry accounting | PASS | No `journal` or `entry` tables; no debit/credit columns on transaction tables |
| No reconciliation logic | PASS | No `reconcile`, `reconciliation`, or matching logic in models or routes |
| Actuals as variance feed only | PASS | `FinanceActual` model is a simple transaction record with `amount`, `description`, `source`; used for budget variance calculation |
| References other modules' signals | PASS | Finance checks `missing_prerequisites` (ownership, interconnection, insurance dates) without duplicating the underlying data |

#### Finance Models Inventory:
1. **FinanceVendor** - Vendor registry (name, type, contact info)
2. **FinanceBudget** - Budget container with line items
3. **FinanceBudgetLineItem** - Individual budget line (category, amount, vendor FK)
4. **FinanceObligation** - Commitment/payment request with approval workflow
5. **FinanceApproval** - Approval record with decision and audit trail
6. **FinanceActual** - Actual transaction feed (source: QuickBooks, Gravity, etc.)

**Conclusion:** Finance module correctly operates as a capital governance layer, not a general ledger.

---

## 5. Seeded Test Data Safety

### Finding: COMPLIANT (Standard test isolation)

#### Test Data Location:
All test fixtures and seed data are isolated in:
- `backend/ilios-server/tests/fixtures/` (sites.py, tasks.py, roles.py, etc.)
- `backend/ilios-server/tests/conftest.py`

#### Protection Mechanisms:
1. **Test database isolation:** Tests use pytest fixtures that create isolated database sessions
2. **No production data seeding:** No seed scripts in `app/` directory that could run in production
3. **Environment separation:** Test fixtures are only loaded by pytest, not by application startup

#### Verification:
```bash
# No seed/demo data in application code
grep -r "seed\|Seed\|TEST_\|DEMO_\|demo" backend/ilios-server/app/ 
# Result: No matches (only test directory has such patterns)
```

**Conclusion:** Test data is properly isolated and cannot leak into production.

---

## Safe Fixes Applied

No code changes were required. All audit checks passed.

---

## Remaining Recommendations (No Code Changes Now)

### For Sales/Pipeline Module (Future Roadmap):
1. **DO NOT** create a separate `Project` table - continue using `Site` as the canonical entity
2. **DO NOT** create `Pipeline`, `Deal`, or `Opportunity` tables yet
3. When building Sales module:
   - Add `FinanceBudget.deal_id` is already present (nullable) for future deal linking
   - Consider adding a `pipeline_stage` enum to `SiteAdditionalFieldList` when needed
   - Use the existing `SiteStatuses` enum for lifecycle, not a new pipeline concept

### Terminology Consistency:
1. **Preserve internal identifiers:** Keep `site_id`, `sites` table, `site` in API paths
2. **UI-only relabeling:** Continue using "Project" only in user-facing strings
3. Document this convention in `replit.md` (already documented)

### Lifecycle Enhancement (Future):
1. Add contextual banners in O&M when project is not "Placed in Service"
2. Add disabled action states with messaging in Due Diligence for pre-construction projects
3. These are UX improvements, not architectural changes

---

## Key File Paths Reference

### Data Models
- `backend/ilios-server/app/models/site.py` - Canonical Site model, SiteStatuses enum
- `backend/ilios-server/app/models/user.py` - UserProject junction table
- `backend/ilios-server/app/models/finance.py` - Finance module models

### Navigation
- `frontend/rea-investment-fe/src/components/layout/NavMenu/NavMenu.tsx` - Sidebar navigation
- `frontend/rea-investment-fe/src/handles/handles.ts` - RouteHandle class for breadcrumbs

### Route Handles (Breadcrumb Builders)
- `frontend/rea-investment-fe/src/modules/asset-management/pages/*/handle.ts`
- `frontend/rea-investment-fe/src/modules/finance/pages/*/handle.ts`
- `frontend/rea-investment-fe/src/modules/operations-and-maintenance/pages/*/handle.ts`

### Finance API Routes
- `backend/ilios-server/app/routers/finance/` - All Finance endpoints

---

## Conclusion

The Ilios platform architecture is correctly implemented. "Project" is purely a UI terminology change - the canonical `Site` entity remains intact. Navigation is stable regardless of lifecycle state. The Finance module operates within its intended boundaries as a capital governance engine. No immediate fixes are required.
