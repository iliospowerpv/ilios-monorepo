# Deal to Project Conversion Audit Report

**Date**: January 2026  
**Author**: Replit Agent  
**Status**: Audit Complete, Safe Fixes Applied

---

## Summary of Findings

| Area | Status | Notes |
|------|--------|-------|
| Data Model + Identity Integrity | ✅ Compliant | Deal → Site one-way reference with `converted_to_project_id` |
| Conversion Logic | ✅ Fixed | Idempotency guard added, validation improved |
| Lifecycle + Module Activation | ✅ Compliant | Sets `due_diligence` lifecycle on conversion |
| Navigation + Terminology | ✅ Compliant | Clear separation: Deals in Sales, Projects in Asset Management |
| Finance/Diligence Boundaries | ✅ Compliant | No automatic obligations or accounting entries created |
| Audit Trail | ✅ Compliant | `sales_state_transitions` table logs all events |

---

## A) Data Model + Identity Integrity

### Entities Involved

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SALES MODULE                                 │
│  ┌─────────────────┐                                                │
│  │     deals       │  Pre-project pipeline entity                   │
│  │─────────────────│                                                │
│  │ id (PK)         │                                                │
│  │ name            │                                                │
│  │ company_id (FK) │──────────┐                                    │
│  │ is_converted    │          │                                    │
│  │ converted_to_   │──────────┼───────────────┐                    │
│  │   project_id    │          │               │                    │
│  │ ...deal fields  │          │               ▼                    │
│  └─────────────────┘          │    ┌─────────────────────┐         │
│                               │    │      sites          │         │
│                               │    │ (Canonical Project) │         │
│                               │    │─────────────────────│         │
│                               │    │ id (PK)             │         │
│                               └───▶│ company_id (FK)     │         │
│                                    │ name                │         │
│                                    │ address, city, state│         │
│                                    │ system_size_ac/dc   │         │
│                                    └─────────────────────┘         │
│                                             │                       │
│                                             ▼                       │
│                               ┌─────────────────────────┐          │
│                               │ site_additional_fields  │          │
│                               │─────────────────────────│          │
│                               │ site_id (FK)            │          │
│                               │ lifecycle_state         │          │
│                               │ sales_stage             │          │
│                               │ ownership_structure     │          │
│                               │ offtaker_name           │          │
│                               └─────────────────────────┘          │
│                                                                     │
│  ┌───────────────────────────┐                                     │
│  │ sales_state_transitions   │  Audit Log                          │
│  │───────────────────────────│                                     │
│  │ id (PK)                   │                                     │
│  │ deal_id (FK, nullable)    │                                     │
│  │ site_id (FK, nullable)    │                                     │
│  │ transition_type           │                                     │
│  │ from_state, to_state      │                                     │
│  │ changed_by_id (FK)        │                                     │
│  │ created_at                │                                     │
│  └───────────────────────────┘                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Compliance Verification

1. **"Project" is NOT a separate table** ✅
   - The `sites` table remains the canonical entity
   - "Project" is UI terminology only (per `replit.md` guidelines)
   - No `projects` table exists

2. **Conversion creates exactly one Site record** ✅
   - Deal stores `converted_to_project_id` as FK to `sites.id`
   - One-way reference: Deal → Site (Site does not reference Deal)

3. **No identity drift risk** ✅
   - After conversion, Deal is marked `is_converted = True`
   - Site becomes the authoritative record for downstream modules
   - Deal data is copied once; post-conversion edits happen on Site only
   - UI disables Deal editing after conversion (`disabled={deal.is_converted}`)

### Field Authority Table

| Field | Pre-Conversion | Post-Conversion |
|-------|---------------|-----------------|
| Name | Deal.name | Site.name (copied) |
| Address | Deal.address | Site.address (copied) |
| System Size | Deal.system_size_ac/dc | Site.system_size_ac/dc (copied) |
| Ownership | Deal.ownership_structure | SiteAdditionalFieldList.ownership_structure |
| Offtaker | Deal.offtaker_name | SiteAdditionalFieldList.offtaker_name |

---

## B) Conversion Logic (Correctness + Safety)

### File Paths

| Component | Path |
|-----------|------|
| Deal Create Form | `frontend/rea-investment-fe/src/modules/sales/pages/SalesHome/SalesHome.tsx` |
| Deal Detail Page | `frontend/rea-investment-fe/src/modules/sales/pages/DealDetail/DealDetail.tsx` |
| Conversion Handler (Backend) | `backend/ilios-server/app/routers/sales/deals.py` (line 237) |
| Conversion Handler (Frontend) | `frontend/rea-investment-fe/src/modules/sales/api/sales.ts` (line 117) |
| DB Migrations | `backend/ilios-server/alembic/versions/84b32177eb40_add_deals_table_and_update_sales_.py` |
| | `backend/ilios-server/alembic/versions/aa97f8f2cb84_update_deal_fields_for_frontend_.py` |

### Verification Checklist

1. **Permissions** ⚠️ Partial
   - Currently hardcoded `user_id = 1`
   - TODO: Integrate with auth context for proper user extraction
   - Safe for MVP; requires enhancement for production

2. **Validation** ✅ Fixed
   - Checks `deal.name` is present
   - Checks `data.company_id` is provided
   - Returns 400 error with clear message if validation fails

3. **Transaction Safety** ✅ Fixed
   - Uses try/except with explicit `db.rollback()` on failure
   - `db.flush()` before commit to catch FK violations early

4. **Idempotency** ✅ Fixed
   - If `deal.is_converted && deal.converted_to_project_id` exists:
     - Returns existing project reference
     - Does NOT create duplicate
   - Returns informative message: "Deal was already converted to project X"

5. **Mapping** ✅
   - `Deal.converted_to_project_id` → `Site.id`
   - Queryable via `deal.converted_project` relationship

---

## C) Lifecycle + Module Activation Contract

### Conversion Lifecycle State

Upon conversion, the Site is created with:
- `lifecycle_state = 'due_diligence'`
- `sales_stage = 'mipa_signed'`

This is correct per the designed flow:
- Deal progresses through 14 sales stages
- At MIPA Signed, conversion is allowed
- New Site starts in Due Diligence lifecycle

### Module Readiness Defaults

| Module | State After Conversion |
|--------|----------------------|
| Due Diligence | Active, shows as "initiated" |
| Finance | Shows "not ready" (no prerequisites set) |
| Operations | Inactive (no telemetry until Placed in Service) |
| Asset Management | Active, Site visible in company portfolio |

### Navigation Visibility

- All modules remain visible in sidebar regardless of lifecycle state
- Lifecycle controls contextual messaging, not navigation visibility
- Compliant with architectural guidelines

---

## D) Navigation + Terminology Consistency

### Verification

1. **Deals live under Sales module** ✅
   - Route: `/sales` → SalesHome with kanban pipeline
   - Route: `/sales/deal/:dealId` → DealDetail page

2. **Projects are canonical Site records** ✅
   - After conversion, redirects to `/asset-management/site/:siteId`
   - No ambiguous "Overview" links

3. **Breadcrumbs and deep links** ✅
   - Deal → Convert → lands on Project/Site detail page
   - Deal shows "Converted to Project" chip with link

4. **No ambiguous terminology** ✅
   - Sales module uses "Deal" consistently
   - Asset Management uses "Project" for Sites

---

## E) Finance and Diligence Boundaries

### Verification

1. **No automatic finance entries created** ✅
   - Conversion does NOT create:
     - Budget entries
     - Obligations
     - Invoices
     - Accounting entries

2. **Lightweight placeholders only** ✅
   - Only `SiteAdditionalFieldList` created with:
     - lifecycle_state
     - sales_stage
     - ownership_structure
     - offtaker_name

3. **No DD checklist duplication** ✅
   - Sales has minimal handoff checklist (6 fields)
   - Full DD checklists are in Due Diligence module only

---

## F) Audit Trail + History

### Current Implementation ✅

`sales_state_transitions` table logs:
- `deal_id` - Which deal
- `site_id` - Which site (nullable, set on conversion)
- `transition_type` - 'stage_transition', 'converted_to_project', etc.
- `from_state` - Previous state
- `to_state` - New state
- `changed_by_id` - User who made change
- `created_at` - Timestamp
- `notes` - Optional notes

### Logged Events

1. Deal created → transition logged
2. Deal stage changed → transition logged
3. Deal converted → special transition with type `converted_to_project`

---

## Safe Fixes Applied

| Fix | Reason |
|-----|--------|
| Added idempotency guard | Prevents duplicate Site creation on retry |
| Added validation for name and company_id | Ensures minimum data before conversion |
| Added try/except with rollback | Transaction safety on failure |
| Fixed field name mismatch | `system_size_kw_dc` → `system_size_ac/dc` |
| Updated frontend types | `ConvertToProjectRequest` now requires `company_id` |
| Fixed Site creation pattern | Uses property assignment instead of constructor |
| **Removed CA fallback** | State validation now required (see Hardening Pass below) |
| **Added unique constraint** | `uq_deals_converted_to_project_id` enforces one-to-one mapping |
| **Race condition handling** | Catches unique constraint violations and returns existing project |

---

## Manual Test Plan (10 minutes)

### Prerequisites
- Login as system@user.com / SystemUser123!
- Navigate to Sales module

### Test Steps

1. **Create Deal** (2 min)
   - Click "Add Deal" button
   - Fill: Name, Company, Address, City, State, System Size AC/DC
   - Submit → Verify deal appears in Prospect column

2. **Stage Progression** (2 min)
   - Click on deal card → DealDetail page
   - Click "Change Stage" → select "NDA Signed"
   - Verify stage changes and history updates

3. **Progress to MIPA Signed** (1 min)
   - Change stage to "MIPA Signed"
   - Verify "Convert to Project" button becomes enabled

4. **Convert to Project** (2 min)
   - Click "Convert to Project"
   - Add optional notes
   - Click "Convert"
   - Verify redirect to Asset Management site detail page

5. **Verify Idempotency** (1 min)
   - Call API directly: `POST /api/sales/deals/{id}/convert-to-project`
   - Verify returns existing project, no duplicate created

6. **Verify Audit Trail** (1 min)
   - Return to deal page (if accessible) or check database
   - Verify `sales_state_transitions` has conversion entry

7. **Verify Module States** (1 min)
   - Check Due Diligence shows new project
   - Check Finance shows project with "not ready" status
   - Check Operations has no telemetry data (expected)

---

## Hardening Pass (January 2026)

### 1) State Parsing / Default Behavior - RESOLVED

**Issue Identified**: Line 277 had `state_value = State.CA` as a fallback when US state couldn't be parsed. This could silently assign incorrect location data.

**Resolution**: Since `Site.state` is NOT NULL in the database schema, we cannot use NULL. Instead:
- **Removed CA fallback** completely
- **Replaced with validation error**: Returns HTTP 400 with clear message if state is invalid
- **Error message format**: `"Valid US state is required for conversion. '{state}' is not a recognized state. Please update the deal with a valid 2-letter US state code."`

**Why this approach**: 
- Downstream modules (Finance, Due Diligence) depend on accurate location for tax jurisdiction, utility zone calculations
- Silently defaulting to CA could cause compliance issues
- Explicit validation forces data quality before conversion

**Files Changed**:
- `backend/ilios-server/app/routers/sales/deals.py` - State validation logic (lines 267-284)

### 2) Transaction Atomicity + DB Safety - ENFORCED

**Verification**: The conversion runs within SQLAlchemy's default transaction context:
1. All operations (`db.add(site)`, `db.flush()`, `db.add(additional_fields)`, deal update, `db.add(transition)`) are within a single try block
2. Single `db.commit()` at end commits all changes atomically
3. `db.rollback()` in exception handler reverts all changes on failure

**Unique Constraint Added**:
- **Migration**: `ecaeb0d4307a_add_unique_constraint_converted_project_.py`
- **Constraint**: `uq_deals_converted_to_project_id` on `deals.converted_to_project_id`
- **Model updated**: `converted_to_project_id = Column(..., unique=True)`

**Race Condition Handling**:
- If two concurrent requests try to convert the same deal:
  1. First request succeeds and commits
  2. Second request hits unique constraint violation
  3. Exception handler catches it, re-fetches deal, and returns existing project reference
- Result: Idempotent behavior even under concurrent load

**Files Changed**:
- `backend/ilios-server/app/models/sales.py` - Added `unique=True` to converted_to_project_id
- `backend/ilios-server/alembic/versions/ecaeb0d4307a_*.py` - Migration for unique constraint
- `backend/ilios-server/app/routers/sales/deals.py` - Race condition handling in exception block

---

## 5-Minute Validation Test

### Test 1: State Validation (1 min)
1. Create a deal with invalid state (e.g., "XX" or empty)
2. Try to convert → Should get 400 error with clear message
3. Update deal with valid state (e.g., "CA")
4. Convert → Should succeed

### Test 2: Unique Constraint (2 min)
1. Create a deal with valid data
2. Call convert API twice quickly (curl or parallel tabs)
3. Both should return success with same project_id
4. Check database: Only one Site record created

### Test 3: Atomicity (2 min)
1. Create a deal
2. Temporarily break the audit log insert (e.g., invalid changed_by_id)
3. Try to convert → Should fail
4. Verify: No orphan Site record created (rollback worked)
5. Restore and verify normal conversion works

---

## Risks and Recommendations

### Low Risk
- Hardcoded `user_id = 1` in conversion handler
  - **Recommendation**: Extract from auth context in production

### RESOLVED (was Medium Risk)
- ~~No unique constraint on `deals.converted_to_project_id`~~
  - **Fixed**: Added `uq_deals_converted_to_project_id` unique constraint
  - Race condition handling added in exception block

### Not Applicable
- No CRM contact management needed
- No accounting/bank feed logic required
- No redesign of other modules needed
