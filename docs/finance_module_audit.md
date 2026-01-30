# Finance Module Audit Report

**Date:** January 30, 2026  
**Auditor:** Replit Agent  
**Scope:** READ-ONLY audit of Finance module implementation  
**Purpose:** Map current state, identify gaps vs Ilios "capital governance / decision engine" intent, produce v1 implementation plan

---

## Executive Summary

The Finance module has a **solid foundation** with working CRUD operations for budgets, obligations, approvals, vendors, and actuals. The data model is well-designed and supports the core "capital governance" concept. However, **critical gaps exist** in external integrations (QuickBooks), audit trails, and decision-engine gating rules.

**Key Findings:**
- ✅ Core CRUD operations functional (budgets, obligations, vendors, actuals)
- ✅ Approval workflow exists (draft → submit → approve/reject)
- ✅ Data room package export implemented
- ⚠️ Prerequisite gating is partial (only 5 static fields checked)
- ❌ No QuickBooks integration (enum exists, no OAuth/sync)
- ❌ No audit trail for finance actions
- ❌ No approval thresholds or role-based limits

---

## 1. MODULE OVERVIEW: WHAT EXISTS TODAY

### 1.1 Frontend Routes

| Route | Component | Status | Description |
|-------|-----------|--------|-------------|
| `/finance` | `FinanceModuleContainer` | ✅ Working | Module gate (permission check) |
| `/finance/scope/portfolio` | `FinanceLanding` | ✅ Working | Portfolio-level lens redirect |
| `/finance/scope/company/:companyId` | `FinanceHome` | ✅ Working | Company-level lens |
| `/finance/companies/:companyId` | `FinanceHome` | ✅ Working | Company finance overview |
| `/finance/companies/:companyId/sites/:siteId` | `SiteFinance` | ✅ Working | Project finance detail |

**File Paths:**
```
frontend/rea-investment-fe/src/modules/finance/
├── ModuleContainer.tsx          # Permission gate
├── index.ts                     # Module exports
├── api/
│   └── finance.ts               # API client functions
├── types/
│   └── index.ts                 # TypeScript interfaces/enums
└── pages/
    ├── FinanceLanding/          # Landing/picker page
    ├── FinanceHome/             # Company-level overview
    └── SiteFinance/             # Project-level detail
```

### 1.2 Backend API Endpoints

| Method | Endpoint | Router | Status |
|--------|----------|--------|--------|
| **Portfolio** ||||
| GET | `/api/finance/companies/{company_id}/portfolio/summary` | portfolio | ✅ Working |
| GET | `/api/finance/companies/{company_id}/portfolio/sites/{site_id}/summary` | portfolio | ✅ Working |
| GET | `/api/finance/companies/{company_id}/portfolio/sites/{site_id}/data-room-package` | portfolio | ✅ Working |
| **Budgets** ||||
| GET | `/api/finance/companies/{company_id}/budgets` | budgets | ✅ Working |
| POST | `/api/finance/companies/{company_id}/budgets` | budgets | ✅ Working |
| GET | `/api/finance/companies/{company_id}/budgets/{budget_id}` | budgets | ✅ Working |
| PATCH | `/api/finance/companies/{company_id}/budgets/{budget_id}` | budgets | ✅ Working |
| DELETE | `/api/finance/companies/{company_id}/budgets/{budget_id}` | budgets | ✅ Working |
| POST | `/api/finance/companies/{company_id}/budgets/{budget_id}/line-items` | budgets | ✅ Working |
| PATCH | `/api/finance/companies/{company_id}/budgets/{budget_id}/line-items/{item_id}` | budgets | ✅ Working |
| DELETE | `/api/finance/companies/{company_id}/budgets/{budget_id}/line-items/{item_id}` | budgets | ✅ Working |
| **Obligations** ||||
| GET | `/api/finance/companies/{company_id}/obligations` | obligations | ✅ Working |
| POST | `/api/finance/companies/{company_id}/obligations` | obligations | ✅ Working |
| GET | `/api/finance/companies/{company_id}/obligations/{obligation_id}` | obligations | ✅ Working |
| PATCH | `/api/finance/companies/{company_id}/obligations/{obligation_id}` | obligations | ✅ Working |
| DELETE | `/api/finance/companies/{company_id}/obligations/{obligation_id}` | obligations | ✅ Working |
| POST | `/api/finance/companies/{company_id}/obligations/{obligation_id}/submit` | obligations | ✅ Working |
| POST | `/api/finance/companies/{company_id}/obligations/{obligation_id}/approve` | obligations | ✅ Working |
| GET | `/api/finance/companies/{company_id}/obligations/{obligation_id}/approvals` | obligations | ✅ Working |
| **Vendors** ||||
| GET | `/api/finance/companies/{company_id}/vendors` | vendors | ✅ Working |
| POST | `/api/finance/companies/{company_id}/vendors` | vendors | ✅ Working |
| PATCH | `/api/finance/companies/{company_id}/vendors/{vendor_id}` | vendors | ✅ Working |
| DELETE | `/api/finance/companies/{company_id}/vendors/{vendor_id}` | vendors | ✅ Working |
| **Actuals** ||||
| GET | `/api/finance/companies/{company_id}/actuals` | actuals | ✅ Working |
| POST | `/api/finance/companies/{company_id}/actuals` | actuals | ✅ Working |
| PATCH | `/api/finance/companies/{company_id}/actuals/{actual_id}` | actuals | ✅ Working |
| DELETE | `/api/finance/companies/{company_id}/actuals/{actual_id}` | actuals | ✅ Working |

**File Paths:**
```
backend/ilios-server/app/routers/finance/
├── __init__.py           # Router exports
├── portfolio.py          # Portfolio/site summary, data room
├── budgets.py            # Budget CRUD + line items
├── obligations.py        # Obligation CRUD + approval workflow
├── vendors.py            # Vendor CRUD
└── actuals.py            # Actuals CRUD
```

### 1.3 UI Components & Features

**FinanceHome (Company-Level):**
- ✅ Summary cards: Total Planned, Authorized, Actual, Variance
- ✅ Status cards: Sites Finance Ready, Sites Not Ready, Pending Approvals, Pending Amount
- ✅ Sites table with readiness indicators and drill-down navigation
- ❌ No "Add Budget" action button
- ❌ No integration health widget

**SiteFinance (Project-Level):**
- ✅ Finance Summary Strip (readiness, budget totals, variance)
- ✅ Tabs: Budget & Forecast, Obligations & Payments, Vendors & Contracts, Actuals
- ✅ Export Data Room Package button
- ❌ No "Create Obligation" action button
- ❌ No approval action buttons (approve/reject inline)
- ❌ No variance threshold warnings

---

## 2. DATA MODEL + SOURCE OF TRUTH

### 2.1 Database Tables

#### `finance_vendors`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, IDENTITY | Primary key |
| company_id | INTEGER | FK → companies.id, NOT NULL | Parent company |
| name | VARCHAR(255) | NOT NULL | Vendor name |
| vendor_type | ENUM | NOT NULL | epc, om, insurance, utility, engineering, legal, accounting, other |
| contact_name | VARCHAR(255) | | Primary contact |
| contact_email | VARCHAR(255) | | Contact email |
| contact_phone | VARCHAR(50) | | Contact phone |
| notes | TEXT | | Free-form notes |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| created_at | TIMESTAMP | DEFAULT NOW() | |
| updated_at | TIMESTAMP | DEFAULT NOW() | |

**Source of Truth:** Ilios (manual entry)  
**Created/Updated by:** UI, future import

---

#### `finance_budgets`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, IDENTITY | Primary key |
| company_id | INTEGER | FK → companies.id, NOT NULL | Parent company |
| site_id | INTEGER | FK → sites.id | Optional site scope |
| deal_id | INTEGER | | Optional deal scope (for pre-conversion) |
| name | VARCHAR(255) | NOT NULL | Budget name |
| description | TEXT | | Budget description |
| period_start | DATE | | Budget period start |
| period_end | DATE | | Budget period end |
| status | ENUM | DEFAULT 'draft' | draft, active, closed |
| created_at | TIMESTAMP | DEFAULT NOW() | |
| updated_at | TIMESTAMP | DEFAULT NOW() | |
| created_by_id | INTEGER | FK → users.id | Creator |

**Source of Truth:** Ilios  
**Created/Updated by:** UI (future: baseline model import)

---

#### `finance_budget_line_items`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, IDENTITY | Primary key |
| budget_id | INTEGER | FK → finance_budgets.id, CASCADE | Parent budget |
| vendor_id | INTEGER | FK → finance_vendors.id | Optional vendor |
| category | ENUM | NOT NULL | 13 categories (see enums) |
| description | VARCHAR(500) | | Line item description |
| amount_planned | FLOAT | DEFAULT 0.0 | Planned/budgeted amount |
| amount_authorized | FLOAT | DEFAULT 0.0 | Authorized to spend |
| amount_actual | FLOAT | DEFAULT 0.0 | Actual spent (manual override) |
| start_date | DATE | | Line item period start |
| end_date | DATE | | Line item period end |
| created_at | TIMESTAMP | DEFAULT NOW() | |
| updated_at | TIMESTAMP | DEFAULT NOW() | |

**Source of Truth:** Ilios (amount_actual may come from QuickBooks sync)  
**Created/Updated by:** UI, budget create, future sync

---

#### `finance_obligations`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, IDENTITY | Primary key |
| company_id | INTEGER | FK → companies.id, NOT NULL | Parent company |
| site_id | INTEGER | FK → sites.id | Optional site scope |
| vendor_id | INTEGER | FK → finance_vendors.id | Associated vendor |
| budget_line_item_id | INTEGER | FK → finance_budget_line_items.id | Link to budget line |
| obligation_type | ENUM | NOT NULL | milestone, invoice, retainer, change_order, service_call, other |
| description | TEXT | | Description |
| amount_requested | FLOAT | NOT NULL | Amount requested |
| requested_date | DATE | NOT NULL | Request date |
| due_date | DATE | | Payment due date |
| status | ENUM | DEFAULT 'draft' | draft, submitted, approved, rejected, paid_external, canceled |
| prerequisite_snapshot | JSON | | Captured prerequisites at submission |
| reference_number | VARCHAR(100) | | External reference (invoice #, PO #) |
| created_at | TIMESTAMP | DEFAULT NOW() | |
| updated_at | TIMESTAMP | DEFAULT NOW() | |
| created_by_id | INTEGER | FK → users.id | Creator |

**Source of Truth:** Ilios  
**Created/Updated by:** UI

---

#### `finance_approvals`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, IDENTITY | Primary key |
| obligation_id | INTEGER | FK → finance_obligations.id, CASCADE | Parent obligation |
| approved_by_id | INTEGER | FK → users.id | Approver |
| decision | ENUM | NOT NULL | approved, rejected, override |
| notes | TEXT | | Approval notes |
| override_reason | TEXT | | Reason for override (if applicable) |
| approved_at | TIMESTAMP | DEFAULT NOW() | Decision timestamp |

**Source of Truth:** Ilios  
**Created/Updated by:** Approval workflow

---

#### `finance_actuals`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, IDENTITY | Primary key |
| company_id | INTEGER | FK → companies.id, NOT NULL | Parent company |
| site_id | INTEGER | FK → sites.id | Optional site scope |
| vendor_id | INTEGER | FK → finance_vendors.id | Associated vendor |
| category | ENUM | NOT NULL | Same 13 categories as budget |
| description | VARCHAR(500) | | Transaction description |
| amount | FLOAT | NOT NULL | Transaction amount |
| transaction_date | DATE | NOT NULL | Transaction date |
| reference_id | VARCHAR(100) | | External reference (QBO txn id) |
| source_system | ENUM | DEFAULT 'manual' | manual, quickbooks, gravity, other |
| created_at | TIMESTAMP | DEFAULT NOW() | |
| updated_at | TIMESTAMP | DEFAULT NOW() | |
| created_by_id | INTEGER | FK → users.id | Creator (for manual entries) |

**Source of Truth:** External system (QuickBooks) or manual  
**Created/Updated by:** UI (manual), future QuickBooks sync

---

### 2.2 Textual ERD

```
┌──────────────────┐
│    companies     │
│   (id, name)     │
└────────┬─────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐       ┌──────────────────┐
│  finance_vendors │       │      sites       │
│  (company_id)    │       │  (company_id)    │
└────────┬─────────┘       └────────┬─────────┘
         │                          │
         │                          │
         ▼                          ▼
┌──────────────────────────────────────────────────────────────┐
│                      finance_budgets                          │
│  (company_id, site_id?, deal_id?, name, status, period_*)    │
└──────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌──────────────────────────────────────────────────────────────┐
│                  finance_budget_line_items                    │
│  (budget_id, vendor_id?, category, amount_planned/auth/act)  │
└──────────────────────────────────────────────────────────────┘
         │
         │ 1:N (optional)
         ▼
┌──────────────────────────────────────────────────────────────┐
│                    finance_obligations                        │
│  (company_id, site_id?, vendor_id?, budget_line_item_id?,    │
│   type, amount, status, prerequisite_snapshot)               │
└──────────────────────────────────────────────────────────────┘
         │
         │ 1:N
         ▼
┌──────────────────────────────────────────────────────────────┐
│                     finance_approvals                         │
│  (obligation_id, approved_by_id, decision, notes, override)  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                      finance_actuals                          │
│  (company_id, site_id?, vendor_id?, category, amount,        │
│   transaction_date, source_system, reference_id)             │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 Enums

**FinanceVendorType:**
```
epc, om, insurance, utility, engineering, legal, accounting, other
```

**FinanceObligationType:**
```
milestone, invoice, retainer, change_order, service_call, other
```

**FinanceObligationStatus:**
```
draft, submitted, approved, rejected, paid_external, canceled
```

**FinanceBudgetStatus:**
```
draft, active, closed
```

**FinanceBudgetCategory:**
```
development, construction, interconnection, permitting, equipment,
labor, engineering, legal, insurance, om, administrative, contingency, other
```

**FinanceApprovalDecision:**
```
approved, rejected, override
```

**FinanceActualSource:**
```
manual, quickbooks, gravity, other
```

---

## 3. INTEGRATIONS AUDIT

### 3.1 QuickBooks Integration

| Aspect | Status | Details |
|--------|--------|---------|
| OAuth Flow | ❌ Not Implemented | No OAuth endpoints, no token storage |
| Token Storage | ❌ Not Implemented | No credentials table or secrets |
| Sync Endpoints | ❌ Not Implemented | No sync jobs or webhooks |
| Data Mapping | ⚠️ Enum Ready | `source_system` enum includes 'quickbooks' |
| UI Health Widget | ❌ Not Implemented | No integration status display |

**Existing Code Evidence:**
- `FinanceActualSource.quickbooks` enum exists in `app/static/finance.py`
- `source_system` column in `finance_actuals` table ready for sync
- `reference_id` column available for QBO transaction ID mapping

**Required for QuickBooks Integration:**
1. OAuth2 authorization flow endpoints
2. Token storage (encrypted, with refresh logic)
3. Company-to-QBO-realm mapping
4. Sync job for pulling:
   - Bills/expenses → finance_actuals
   - Vendors → finance_vendors (optional)
   - Classes/Jobs → site/project mapping
5. Last sync timestamp tracking
6. UI for connection management + health status

### 3.2 Other Integrations

| Integration | Status | Notes |
|-------------|--------|-------|
| Gravity | ❌ Not Implemented | Enum exists, no implementation |
| Banking Feeds | ❌ Not Implemented | Not started |
| PowerBI | ✅ Exists (separate) | Reporting module, not finance-specific |

---

## 4. FINANCE WORKFLOWS: "DECISION ENGINE" CHECK

### 4.1 Payment Authorization Flow

**Current Implementation:**

```
┌─────────┐     ┌───────────┐     ┌──────────────────────┐
│  DRAFT  │────▶│ SUBMITTED │────▶│ APPROVED / REJECTED  │
└─────────┘     └───────────┘     └──────────────────────┘
     │                │                      │
     │                │                      ▼
     │                │              ┌──────────────┐
     │                │              │ PAID_EXTERNAL│
     │                │              └──────────────┘
     │                │                      
     ▼                ▼                      
┌─────────┐     ┌───────────┐               
│ CANCELED│     │  (manual) │               
└─────────┘     └───────────┘               
```

**What Works:**
- ✅ Create obligation in draft status
- ✅ Submit obligation (status → submitted, captures prerequisite_snapshot)
- ✅ Approve/reject with notes
- ✅ Override option with reason field
- ✅ Approval history retrieval

**What's Missing:**
| Gap | Priority | Description |
|-----|----------|-------------|
| Approval thresholds | Critical | No dollar-amount limits per role |
| Multi-level approval | High | Single approver only, no escalation |
| Role-based gating | High | Any Finance viewer can approve |
| Notification on submit | Medium | No email/notification to approvers |
| Due date alerts | Medium | No warning for approaching due dates |

### 4.2 Prerequisite Gating

**Current Implementation (in `FinancePortfolioCRUD.get_missing_prerequisites`):**

```python
def get_missing_prerequisites(site: Site) -> list[str]:
    missing = []
    if not hasattr(site, "site_additional_field_list") or not site.site_additional_field_list:
        missing.append("Site additional fields not configured")
        return missing
    fields = site.site_additional_field_list
    if not getattr(fields, "ownership_structure", None):
        missing.append("Ownership Structure")
    if not getattr(fields, "interconnection_utility", None):
        missing.append("Interconnection Utility")
    if not getattr(fields, "insurance_provider", None):
        missing.append("Insurance Provider")
    if not getattr(fields, "key_date_pto", None):
        missing.append("PTO Date")
    if not getattr(fields, "key_date_cod", None):
        missing.append("COD Date")
    return missing[:3]  # Truncated to 3
```

**Assessment:**
- ⚠️ Static field checks only (5 fields)
- ⚠️ No integration with Due Diligence completion status
- ⚠️ No placed-in-service verification
- ⚠️ No insurance expiry checking
- ⚠️ Truncates to 3 items (hides additional missing items)

**Recommended Prerequisites (Not Implemented):**
1. Due Diligence checklist completion %
2. Interconnection agreement uploaded
3. Insurance policy active (not expired)
4. PTO/COD dates set
5. Placed-in-service confirmation
6. O&M contract in place
7. Offtaker agreement signed

### 4.3 Budget vs Actual Variance

**Current Implementation:**
- ✅ Variance calculated: `total_planned - total_actual`
- ✅ Displayed in UI with color coding (green positive, red negative)
- ❌ No threshold alerts
- ❌ No variance % calculation
- ❌ No notification on overrun

### 4.4 Vendor/Service Provider Management

**Current Implementation:**
- ✅ Vendor registry per company
- ✅ Vendor types (EPC, O&M, Insurance, etc.)
- ✅ Link vendors to budget line items
- ✅ Link vendors to obligations
- ❌ No contract/SOW document attachment
- ❌ No vendor performance tracking
- ❌ No vendor spend summary

---

## 5. REPORTING OUTPUTS

### 5.1 Current Outputs

| Output | Status | Format | Description |
|--------|--------|--------|-------------|
| Data Room Package | ✅ Working | JSON | Full site finance export |
| Portfolio Summary | ✅ Working | API/UI | Aggregated budget/actual/variance |
| Site Summary | ✅ Working | API/UI | Per-project finance summary |

**Data Room Package Contents:**
```json
{
  "site_id": 123,
  "site_name": "Project Name",
  "generated_at": "2026-01-30T00:00:00Z",
  "budgets": [/* FinanceBudgetDetailSchema[] */],
  "obligations": [/* FinanceObligationSchema[] */],
  "approvals": [/* FinanceApprovalSchema[] */],
  "actuals": [/* FinanceActualSchema[] */],
  "summary": {/* FinanceSiteSummarySchema */}
}
```

### 5.2 Missing Outputs

| Output | Priority | Description |
|--------|----------|-------------|
| Investor/lender PDF | High | Formatted report for external parties |
| Monthly operating statement | High | Period-over-period comparison |
| Variance report | Medium | Budget vs actual breakdown by category |
| Approval audit trail | Medium | Who approved what, when |
| Excel export | Low | Spreadsheet format for data room |

---

## 6. PERMISSIONS + AUDIT TRAIL

### 6.1 Current Permissions

**Module Permission:** `Finance` (view/edit)

**Authorization Flow:**
```python
# From finance.py
class FinancePermissions(AuthorizedUserSinglePermissionChecker):
    def __init__(self, action, validate_query_module_name=False):
        super().__init__(
            permission_module=PermissionsModules.finance,
            action=action,
            validate_query_module_name=validate_query_module_name,
        )
```

**Frontend Gate:**
```typescript
// From ModuleContainer.tsx
if (user.is_system_user || user.role?.permissions?.['Finance']?.view) {
  return <>{children}</>;
}
```

### 6.2 Permission Matrix

| Action | Required Permission | Notes |
|--------|---------------------|-------|
| View finance data | Finance.view | Works |
| Create/edit budget | Finance.edit | Works |
| Create/edit obligation | Finance.edit | Works |
| Approve obligation | Finance.edit | ⚠️ No separate approval permission |
| Delete budget/obligation | Finance.edit | ⚠️ No soft delete |
| Configure integrations | Finance.edit | ⚠️ Should be separate |

### 6.3 Audit Trail

**Current Status:** ❌ NOT IMPLEMENTED

**Evidence:**
- No `AuditLog` imports in finance routers
- No audit entries created on create/update/delete
- No approval action logging beyond `finance_approvals` table

**Recommended Audit Events:**
1. Budget created/updated/deleted
2. Budget line item added/modified/removed
3. Obligation created/submitted/approved/rejected
4. Override action with reason
5. Vendor created/deactivated
6. Actual imported from external system

### 6.4 Risky Permission Bypasses

| Risk | Location | Recommendation |
|------|----------|----------------|
| `is_system_user` bypass | ModuleContainer.tsx | Audit system user actions |
| No approval thresholds | obligations.py | Add role-based limits |
| Hard delete allowed | All CRUD | Implement soft delete |

---

## 7. ARCHITECTURE SOUNDNESS + ROADMAP FIT

### 7.1 Multi-Company Support

| Capability | Status | Notes |
|------------|--------|-------|
| Company-scoped data | ✅ Good | All tables have company_id FK |
| Cross-company queries | ✅ Good | Authorization checks in place |
| Portfolio roll-up | ✅ Good | `/portfolio/summary` aggregates |

**Verdict:** ✅ KEEP AS-IS

### 7.2 Portfolio Roll-ups + Project Drill-down

| Capability | Status | Notes |
|------------|--------|-------|
| Company → Sites summary | ✅ Good | Working in UI |
| Site detail view | ✅ Good | Working with tabs |
| Cross-company portfolio | ❌ Missing | No multi-company aggregate |

**Verdict:** ✅ KEEP AS-IS (add cross-company later if needed)

### 7.3 Sale/Divestiture Workflows

| Capability | Status | Notes |
|------------|--------|-------|
| Data room export | ✅ Good | JSON package ready |
| Ownership change | ❌ Missing | No transfer workflow |
| Access revocation | ❌ Missing | Manual process |
| Historical data retention | ⚠️ Partial | No versioning |

**Verdict:** ⚠️ REFACTOR SOON - Add ownership transfer workflow

### 7.4 Telemetry Linkage

| Capability | Status | Notes |
|------------|--------|-------|
| Revenue from production | ❌ Missing | No telemetry → revenue calc |
| Performance vs model | ❌ Missing | No baseline comparison |

**Verdict:** ⚠️ FUTURE - Requires telemetry data pipeline

### 7.5 QuickBooks Double-Truth Avoidance

| Concern | Assessment |
|---------|------------|
| Actuals source tracking | ✅ Good - `source_system` enum |
| Reference ID for dedup | ✅ Good - `reference_id` column |
| Sync conflict handling | ❌ Missing - Not implemented |

**Verdict:** ✅ FOUNDATION READY - Implement sync carefully

---

## 8. GAP LIST (PRIORITIZED)

### Critical (Block MVP)

| # | Gap | Impact | Effort |
|---|-----|--------|--------|
| C1 | No audit trail for finance actions | Compliance, accountability | Medium |
| C2 | No approval thresholds | Anyone with edit can approve any amount | Medium |

### High (MVP Quality)

| # | Gap | Impact | Effort |
|---|-----|--------|--------|
| H1 | No QuickBooks integration | Manual actuals entry only | High |
| H2 | No budget/obligation create buttons | Users can only view, not create | Low |
| H3 | No inline approve/reject actions | Must call API directly | Low |
| H4 | Prerequisite checks too basic | False "ready" status | Medium |

### Medium (Post-MVP)

| # | Gap | Impact | Effort |
|---|-----|--------|--------|
| M1 | No contract/document linkage | Can't attach SOWs to vendors | Medium |
| M2 | No recurring obligations | Monthly O&M must be manual | Medium |
| M3 | No variance threshold alerts | Budget overruns not flagged | Low |
| M4 | No PDF/Excel export | JSON only for data room | Medium |
| M5 | No notification on approval needed | Approvers must check manually | Medium |

### Low (Nice-to-Have)

| # | Gap | Impact | Effort |
|---|-----|--------|--------|
| L1 | No multi-level approval | Single approver only | High |
| L2 | No vendor performance metrics | Can't track vendor quality | High |
| L3 | No telemetry revenue linkage | Manual revenue entry | High |

---

## 9. FINANCE v1 IMPLEMENTATION PLAN

### 9.1 Scope Definition

**IN SCOPE (v1):**
1. Audit trail for all finance mutations
2. Create Budget/Obligation action buttons in UI
3. Inline approve/reject on obligation list
4. Approval threshold configuration (company-level setting)
5. Enhanced prerequisite checks (DD completion, insurance expiry)
6. Variance threshold warnings (visual only)
7. Finance quick action from Project page

**OUT OF SCOPE (v1):**
- QuickBooks OAuth integration (v2)
- PDF/Excel export (v2)
- Multi-level approval chains (v2)
- Recurring obligations (v2)
- Contract/document attachments (v2)
- Telemetry revenue linkage (v3)

### 9.2 Required Changes

#### Backend

| Change | File(s) | Description |
|--------|---------|-------------|
| Add audit logging | `routers/finance/*.py` | Call audit service on CRUD |
| Approval threshold check | `routers/finance/obligations.py` | Validate amount vs user threshold |
| Company approval settings | New model + endpoints | Store threshold config per company |
| Enhanced prerequisites | `crud/finance.py` | Check DD completion, insurance dates |

#### Frontend

| Change | File(s) | Description |
|--------|---------|-------------|
| Add Budget button | `SiteFinance.tsx` | Open create budget dialog |
| Add Obligation button | `SiteFinance.tsx` | Open create obligation dialog |
| Inline approve/reject | `ObligationsTab` | Action buttons in table row |
| Variance warning | `FinanceSummaryStrip` | Alert banner when variance > threshold |
| Project quick action | `ProjectView.tsx` | Add Finance to Quick Actions |

#### Database

| Change | Table | Description |
|--------|-------|-------------|
| Approval thresholds | New: `finance_approval_thresholds` | company_id, role, max_amount |
| None needed for audit | Use existing `audit_logs` | Already exists in system |

### 9.3 UX Entry Points

1. **Home → Quick Actions** - Add "Finance Dashboard" link
2. **Project Page → Quick Actions** - Add "Finance" button
3. **Finance Home** - Add "Create Budget" action
4. **Site Finance** - Add "Create Obligation" action
5. **Obligations Tab** - Add approve/reject inline actions

### 9.4 Integration Health Widgets (v2)

For QuickBooks (future):
- Connection status indicator
- Last sync timestamp
- Sync error count
- "Reconnect" action button

---

## 10. ACCEPTANCE TEST CHECKLIST (10-minute manual test)

### Pre-requisites
- [ ] Logged in as user with Finance.edit permission
- [ ] At least one company with 2+ projects exists
- [ ] At least one project has prerequisite fields populated

### Test Cases

**Portfolio Level:**
- [ ] Navigate to `/finance` → redirects to company picker or first company
- [ ] Company summary shows correct project count
- [ ] Summary cards display (Planned, Authorized, Actual, Variance)
- [ ] Click project row → navigates to site finance

**Site Finance:**
- [ ] Summary strip shows readiness status
- [ ] Budget tab shows budget list (may be empty)
- [ ] Obligations tab shows obligation list
- [ ] Vendors tab shows company vendors
- [ ] Actuals tab shows actuals (may be empty)
- [ ] "Export Data Room Package" downloads JSON file

**Budget CRUD (API test):**
- [ ] POST budget → creates with line items
- [ ] GET budget → returns with totals calculated
- [ ] PATCH budget → updates status
- [ ] DELETE budget → removes (cascades line items)

**Obligation Workflow (API test):**
- [ ] POST obligation → creates in draft status
- [ ] POST submit → status becomes submitted, prerequisite_snapshot captured
- [ ] POST approve → status becomes approved, approval record created
- [ ] GET approvals → returns approval history

**Permissions:**
- [ ] User without Finance.view → cannot access /finance routes
- [ ] User with Finance.view only → can view but not create
- [ ] User with Finance.edit → can create/approve

**Data Room Export:**
- [ ] Download contains budgets, obligations, approvals, actuals, summary
- [ ] JSON is valid and complete

---

## 11. APPENDIX

### A. File Path Reference

```
backend/ilios-server/
├── app/
│   ├── routers/finance/
│   │   ├── __init__.py
│   │   ├── actuals.py
│   │   ├── budgets.py
│   │   ├── obligations.py
│   │   ├── portfolio.py
│   │   └── vendors.py
│   ├── crud/
│   │   └── finance.py
│   ├── models/
│   │   └── finance.py
│   ├── schema/
│   │   └── finance.py
│   ├── static/
│   │   └── finance.py
│   └── helpers/authorization/module_based/
│       └── finance.py

frontend/rea-investment-fe/src/
├── modules/finance/
│   ├── ModuleContainer.tsx
│   ├── index.ts
│   ├── api/
│   │   └── finance.ts
│   ├── types/
│   │   └── index.ts
│   └── pages/
│       ├── FinanceLanding/
│       ├── FinanceHome/
│       └── SiteFinance/
```

### B. Migration Reference

Finance tables created in: `alembic/versions/96da4f066b96_add_finance_module_tables.py`

---

*End of Finance Module Audit Report*
