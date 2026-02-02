# Gap Report & Implementation Plan: Module Boundary Refactor

**Document Version:** 1.0  
**Date:** February 2, 2026  
**Status:** ANALYSIS ONLY - NO CODE CHANGES

---

## 1. Current State Summary

### 1.1 Current Left Nav Modules (NavMenu.tsx)

| Current Module | Route | Icon |
|---------------|-------|------|
| Home | `/home` | HomeIcon |
| Portfolio | `/portfolio` | DashboardIcon |
| **Sales** | `/sales` | TrendingUpIcon |
| **Diligence** | `/due-diligence` | FactCheckIcon |
| **O&M** | `/operations-and-maintenance` | WhatshotIcon |
| **Asset Management** | `/asset-management` | AccountBalanceIcon |
| **Finance** | `/finance` | AccountBalanceWalletIcon |
| Reports | `/reports` | AssessmentIcon |
| Portfolio Admin | `/portfolio-admin` | AdminPanelSettingsIcon |
| Admin | `/admin/access-health` | SettingsIcon |

### 1.2 Target Left Nav Modules (Per Specification)

| Target Module | Purpose |
|--------------|---------|
| **Acquisitions** | Deal pipeline only (ends at conversion) |
| **Project Hub** | Canonical project shell with tabs |
| **O&M** | Devices, telemetry, alerts, work orders |
| **Finance** | Budgets, approvals, invoices |
| **Reporting** | Portfolio + project-level reports |
| **Admin / Setup** | System administration |

### 1.3 Target Project Hub Tabs

| Tab | Owner Module |
|-----|-------------|
| Overview | Project Hub (canonical record) |
| Data Room | Document management, AI extraction |
| O&M | Read-only rollup + deep links to O&M module |
| Finance | Read-only snapshot + deep links to Finance module |
| Tasks | Unified task view (My Work, Project Tasks, Context Tasks) |
| Reporting | Project-level reports |

---

## 2. Current Data Models Inventory

### 2.1 Deal (Pre-Acquisition)
**File:** `backend/ilios-server/app/models/sales.py`
**Table:** `deals`

| Field | Type | Notes |
|-------|------|-------|
| `id` | Integer PK | Auto-increment |
| `name` | VARCHAR(255) | Free text (VIOLATION: should be system-constructed) |
| `sales_stage` | VARCHAR(50) | 14 stages including "Phase 1 Diligence" |
| `lifecycle_state` | VARCHAR(50) | Pre-Diligence, DueDiligence, Implementation, etc. |
| `is_converted` | Boolean | Conversion flag |
| `converted_to_project_id` | FK → sites.id | Link to converted project |
| ...financial/location fields... | | |

**Key Relationships:**
- `converted_project` → Site (one-to-one after conversion)
- `company` → Company

### 2.2 Site/Project (Post-Acquisition)
**File:** `backend/ilios-server/app/models/site.py`
**Table:** `sites`

| Field | Type | Notes |
|-------|------|-------|
| `id` | Integer PK | Auto-increment |
| `company_id` | FK → companies.id | Parent company |
| `name` | VARCHAR | Project name |
| ...many fields... | | See SiteAdditionalFieldList for extended data |

**Key Relationships:**
- `devices` → Device[] (one-to-many)
- `documents` → Document[] (one-to-many)
- `telemetry_mapping` → TelemetrySiteMapping (one-to-one)
- `additional_fields` → SiteAdditionalFieldList (one-to-one)
- `sales_transitions` → SalesStateTransition[] (audit trail)

### 2.3 Document (Data Room)
**File:** `backend/ilios-server/app/models/document.py`
**Table:** `documents`

| Field | Type | Notes |
|-------|------|-------|
| `id` | Integer PK | |
| `site_id` | FK → sites.id | Parent project |
| `section_id` | FK → document_sections.id | Checklist category |
| `name` | Enum(SiteDocumentsEnum) | Predefined document types |
| `custom_name` | String | User-defined name |
| `approver_id` | FK → users.id | |

**Key Relationships:**
- `files` → File[] (uploaded attachments)
- `keys` → DocumentKey[] (extracted fields)
- `task` → Task (linked task for checklist)
- `section` → DocumentSection (grouping)

### 2.4 DocumentKey (Extracted Fields)
**File:** `backend/ilios-server/app/models/document.py`
**Table:** `document_keys`

| Field | Type | Notes |
|-------|------|-------|
| `id` | Integer PK | |
| `document_id` | FK | |
| `editor_id` | FK → users.id | Last editor |
| `name` | String | Field name |
| `value` | String | Extracted/entered value |

**MISSING FIELDS (per spec):**
- `is_proposed` (Boolean) - AI-extracted vs. confirmed
- `is_accepted` (Boolean) - User acceptance status
- `accepted_by_id` (FK) - Who accepted
- `accepted_at` (DateTime) - When accepted
- `source` (Enum) - AI_EXTRACTION, MANUAL_ENTRY, OVERRIDE

### 2.5 Task (Unified)
**File:** `backend/ilios-server/app/models/task.py`
**Table:** `tasks`

| Field | Type | Notes |
|-------|------|-------|
| `id` | Integer PK | |
| `external_id` | VARCHAR | Pretty name (e.g., IOSP1-867) |
| `board_id` | FK → boards.id | Parent board |
| `document_id` | FK → documents.id | Optional: linked document |
| `alert_id` | FK → alerts.id | Optional: linked alert |
| `affected_device_id` | FK → devices.id | Optional: linked device |

**STATUS:** Already supports multiple surfaces (documents, alerts, devices). Compliant with ONE Task model requirement.

### 2.6 Finance Models
**File:** `backend/ilios-server/app/models/finance.py`
**Tables:** `finance_budgets`, `finance_budget_line_items`, `finance_obligations`, `finance_approvals`, `finance_actuals`, `finance_vendors`

**STATUS:** Well-structured, supports both `site_id` and `deal_id` references. No violations.

### 2.7 Telemetry/Devices
**File:** `backend/ilios-server/app/models/device.py`, `backend/ilios-server/app/models/telemetry.py`
**Tables:** `devices`, `das_connections`, `telemetry_site_mapping`, `telemetry_device_mapping`

**STATUS:** Properly scoped to Site. No violations.

---

## 3. Violations of Ownership Rules

### 3.1 CRITICAL: Sales Stage Overlap with Lifecycle

**Current State:**
```typescript
// frontend/rea-investment-fe/src/modules/sales/types/index.ts
export enum SalesStage {
  Prospect = 'prospect',
  ...
  Phase1Diligence = 'phase_1_diligence',  // <-- VIOLATION
  MIPANegotiating = 'mipa_negotiating',
  MIPASigned = 'mipa_signed',
  ...
}
```

**Problem:** "Phase 1 Diligence" is a lifecycle state that happens AFTER conversion to Project, not a sales stage. This blurs Sales ↔ Project Hub boundaries.

**Resolution:** Remove `Phase1Diligence` from SalesStage enum. Sales ends at MIPA Signed (or Term Sheet Signed as alternate conversion point).

---

### 3.2 CRITICAL: Project Name is Free Text

**Current State:**
- `deals.name` - Free text input
- `sites.name` - Free text input
- No deterministic construction at conversion

**Requirement:** Project name must be system-constructed at conversion (e.g., `{State}-{CompanyAbbr}-{SequenceNum}`).

**Resolution:**
1. Add `name_override` column to `sites` for admin edits
2. Generate deterministic `name` at conversion
3. Log all name changes to audit_log

---

### 3.3 MODERATE: Extracted Fields Missing Acceptance Workflow

**Current State:**
- `DocumentKey` stores `name` and `value`
- No distinction between AI-proposed vs. user-accepted
- No audit of who accepted/when

**Requirement:** Extracted fields are PROPOSED until ACCEPTED/OVERRIDDEN by user, then become CANONICAL.

**Resolution:** Add to `document_keys` table:
- `source` ENUM('ai_extraction', 'manual_entry', 'override')
- `is_accepted` BOOLEAN
- `accepted_by_id` FK → users.id
- `accepted_at` TIMESTAMP

---

### 3.4 MODERATE: Deal Read-Only Enforcement Missing

**Current State:**
- `deals.is_converted` flag exists
- No UI enforcement of read-only after conversion
- No banner directing user to Project Hub

**Requirement:** After conversion, Deal becomes READ-ONLY with banner: "This opportunity has been converted to a Project. Continue in Project Hub."

**Resolution:**
1. Add frontend guard in DealDetail.tsx
2. Render banner with link to project
3. Disable all edit controls when `is_converted = true`

---

### 3.5 MODERATE: Lifecycle Transition Controls Missing

**Current State:**
- `SalesStateTransition` audit table exists
- No role-based gate (Company Admin or Superuser only)
- No automatic task template creation on transition

**Requirement:**
- Only Company Admin or Superuser can transition lifecycle
- Every transition is audited
- Transition auto-creates standard task templates

**Resolution:**
1. Add permission check in lifecycle transition endpoint
2. Create lifecycle task templates table
3. Add task creation logic to transition handler

---

### 3.6 LOW: Module Navigation Names Mismatch

**Current:**
| Current Name | Target Name |
|-------------|-------------|
| Sales | Acquisitions |
| Due Diligence | (merge into Data Room tab) |
| Asset Management | Project Hub |

**Resolution:** Update NavMenu.tsx, route paths, and module references.

---

### 3.7 LOW: Duplicate Project Views

**Current State:**
- Asset Management → SiteDetails → Overview (canonical project record)
- Due Diligence → SitePage → Overview (similar view)
- O&M → SiteDetails → Overview (operational view)

**Requirement:** Single canonical Project Hub with tabs, deep-linking to specialized modules.

**Resolution:**
1. Designate Asset Management SiteDetails as the canonical Project Hub
2. Add tabs: Data Room, O&M, Finance, Tasks, Reporting
3. Remove duplicate Overview from Due Diligence module
4. O&M module becomes specialized operational view (deep-linked from Project Hub O&M tab)

---

## 4. Route/Nav Changes Required

### 4.1 Route Mappings

| Current Route | Target Route | Action |
|--------------|--------------|--------|
| `/sales` | `/acquisitions` | Rename |
| `/sales/deal/:dealId` | `/acquisitions/deal/:dealId` | Rename |
| `/due-diligence` | (remove as standalone) | Merge into Project Hub |
| `/due-diligence/companies/:cid/sites/:sid` | `/project-hub/:projectId/data-room` | Redirect |
| `/asset-management` | `/project-hub` | Rename |
| `/asset-management/companies/:cid/sites/:sid` | `/project-hub/:projectId` | Simplify |
| `/asset-management/.../overview` | `/project-hub/:projectId/overview` | Keep as default tab |
| `/operations-and-maintenance` | `/om` (optional shortening) | Keep |
| `/finance` | `/finance` | Keep |
| `/reports` | `/reports` | Keep |
| `/portfolio-admin` | `/admin` or `/setup` | Consolidate |

### 4.2 NavMenu.tsx Updates

```typescript
// TARGET menuItems configuration
const menuItems = [
  ['home', <HomeIcon />, 'Home', '/home', false],
  ['acquisitions', <TrendingUpIcon />, 'Acquisitions', '/acquisitions', false],
  ['project-hub', <AccountBalanceIcon />, 'Project Hub', '/project-hub', false],
  ['om', <WhatshotIcon />, 'O&M', '/om', false],
  ['finance', <AccountBalanceWalletIcon />, 'Finance', '/finance', false],
  ['reports', <AssessmentIcon />, 'Reports', '/reports', false],
  ['admin', <AdminPanelSettingsIcon />, 'Admin', '/admin', false],
];
```

---

## 5. Files to Modify (Grouped by Module)

### 5.1 Acquisitions (formerly Sales)

| File | Change Type | Description |
|------|-------------|-------------|
| `frontend/.../modules/sales/` | Rename folder | → `modules/acquisitions/` |
| `frontend/.../sales/types/index.ts` | Edit | Remove `Phase1Diligence` stage |
| `frontend/.../sales/pages/DealDetail/DealDetail.tsx` | Edit | Add read-only mode + conversion banner |
| `frontend/.../sales/api/sales.ts` | Edit | Update API path references |
| `frontend/src/App.tsx` | Edit | Update route paths `/sales` → `/acquisitions` |
| `frontend/.../NavMenu/NavMenu.tsx` | Edit | Rename "Sales" → "Acquisitions" |
| `backend/.../routers/sales/` | Edit | Update route prefixes if needed |

### 5.2 Project Hub (formerly Asset Management)

| File | Change Type | Description |
|------|-------------|-------------|
| `frontend/.../modules/asset-management/` | Rename folder | → `modules/project-hub/` |
| `frontend/.../AssetManagementSiteDetails/` | Rename | → `ProjectDetails/` |
| `frontend/.../tabs/` | Add tabs | Data Room, O&M, Finance, Reporting |
| `frontend/src/App.tsx` | Edit | Update routes `/asset-management` → `/project-hub` |
| `frontend/.../NavMenu/NavMenu.tsx` | Edit | Rename "Asset Management" → "Project Hub" |
| `backend/.../routers/asset_management/` | Edit | Update route prefixes if needed |

### 5.3 Data Room (formerly Due Diligence)

| File | Change Type | Description |
|------|-------------|-------------|
| `frontend/.../modules/due-diligence/` | Keep but restructure | Becomes embedded tab component |
| `frontend/.../DueDiligenceDocument/` | Keep | AI extraction, poison pills |
| `backend/.../models/document.py` | Edit | Add acceptance workflow fields |
| `backend/.../crud/document.py` | Edit | Add acceptance/rejection logic |

### 5.4 Backend Data Model Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/.../models/document.py` | Edit | Add `source`, `is_accepted`, `accepted_by_id`, `accepted_at` to DocumentKey |
| `backend/.../models/site.py` | Edit | Add `name_override`, `system_name` logic |
| `backend/.../models/task.py` | No change | Already unified |
| `backend/.../schema/document.py` | Edit | Add acceptance schemas |
| New migration | Create | Add DocumentKey acceptance columns |
| New migration | Create | Add Site name_override column |

### 5.5 Lifecycle & Conversion

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/.../routers/sales/deals.py` | Edit | Enhance conversion logic |
| `backend/.../crud/sales.py` | Edit | Add shell creation (Data Room, Finance, O&M) |
| New table | Create | `lifecycle_task_templates` |
| New endpoint | Create | POST `/api/projects/:id/lifecycle-transition` |
| New model | Create | `LifecycleTaskTemplate` |

---

## 6. Permission Changes

### 6.1 New Permission Keys

| Permission | Description | Applies To |
|-----------|-------------|-----------|
| `Acquisitions.view` | View deals/pipeline | Replaces `Sales.view` |
| `Acquisitions.edit` | Edit deals | Replaces `Sales.edit` |
| `ProjectHub.view` | View project details | Replaces `Asset Management.view` |
| `ProjectHub.edit` | Edit project record | |
| `DataRoom.view` | View documents | |
| `DataRoom.edit` | Upload/manage documents | |
| `DataRoom.accept_fields` | Accept AI-extracted fields | |
| `Lifecycle.transition` | Transition lifecycle state | Admin/Superuser only |

### 6.2 Migration of Existing Permissions

```sql
-- Example migration
UPDATE roles SET permissions = 
  jsonb_set(permissions, '{Acquisitions}', permissions->'Sales')
WHERE permissions ? 'Sales';
```

---

## 7. Acceptance Criteria for Implementation

### 7.1 Acquisitions Module

- [ ] Route `/sales` redirects to `/acquisitions`
- [ ] Nav shows "Acquisitions" not "Sales"
- [ ] `Phase1Diligence` stage removed from frontend enum
- [ ] Converted deals show read-only mode with banner
- [ ] Banner includes button linking to Project Hub
- [ ] All deal editing disabled when `is_converted = true`

### 7.2 Project Hub Module

- [ ] Route `/asset-management` redirects to `/project-hub`
- [ ] Nav shows "Project Hub" not "Asset Management"
- [ ] Project page has 6 tabs: Overview, Data Room, O&M, Finance, Tasks, Reporting
- [ ] Overview tab shows canonical project record (existing functionality)
- [ ] Data Room tab embeds due diligence document management
- [ ] O&M tab shows read-only rollup with deep links to `/om/...`
- [ ] Finance tab shows read-only snapshot with deep links to `/finance/...`
- [ ] Tasks tab shows unified task view
- [ ] Reporting tab shows project-level reports

### 7.3 Data Room (embedded)

- [ ] AI-extracted fields show "PROPOSED" badge until accepted
- [ ] Accept/Reject buttons for each proposed field
- [ ] Accepted fields show checkmark and acceptor name
- [ ] Override option with audit logging
- [ ] Poison pill flags visible
- [ ] Diligence checklist with task links

### 7.4 Deal → Project Conversion

- [ ] Conversion only allowed at `MIPASigned` (or `TermSheetSigned`)
- [ ] Conversion creates: Project record, Data Room shell, Finance shell, O&M shell
- [ ] Project name is system-constructed (not free text)
- [ ] Deal moves to "Closed Won" and becomes read-only
- [ ] Signed document flagged as REQUIRED/MISSING if not uploaded
- [ ] Lifecycle starts at `Pre-Diligence`

### 7.5 Lifecycle Management

- [ ] Lifecycle states: Pre-Diligence, Diligence, Implementation, Placed In Service, Operations
- [ ] Only Company Admin or Superuser can transition
- [ ] Every transition logged to `audit_log` (who, when, from, to, reason)
- [ ] Transition cannot proceed past Diligence without signed document (or waiver)
- [ ] Task templates auto-created on lifecycle transition

### 7.6 Tasks (existing - verify)

- [ ] ONE Task model (already compliant)
- [ ] Tasks linkable from: Document, Alert, Device, Manual
- [ ] Three views available: My Work, Project Tasks, Context Tasks

### 7.7 Project Name

- [ ] System-constructed at conversion
- [ ] Editable only by Admin/Superuser
- [ ] All edits logged to `audit_log`

---

## 8. Risk Assessment

### 8.1 HIGH RISK: Data Migration

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Route changes break bookmarks | User frustration | Add redirects from old routes |
| Permission key changes break access | Users locked out | Run permission migration before UI changes |
| DocumentKey schema changes | Data loss if poorly migrated | Test migration on staging first |

### 8.2 MEDIUM RISK: UI Regressions

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Tab restructuring breaks navigation | Confused users | Comprehensive E2E testing |
| Duplicate views cause confusion | Same data in multiple places | Remove duplicates, add clear deep-links |
| Sidebar state persistence broken | Minor annoyance | Test localStorage handling |

### 8.3 LOW RISK: Technical Debt

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Folder renames break imports | Build failures | Use IDE refactoring tools |
| Handle/loader references outdated | 404 errors | Search and replace systematically |
| Test files reference old paths | CI failures | Update test imports |

---

## 9. Implementation Phases

### Phase 1: Backend Schema Changes (Non-Breaking)
1. Add new columns to `document_keys` (source, is_accepted, accepted_by_id, accepted_at)
2. Add `name_override` to `sites`
3. Create `lifecycle_task_templates` table
4. Run migrations

### Phase 2: Backend Logic Updates
1. Add field acceptance/rejection endpoints
2. Enhance conversion endpoint to create shells
3. Add lifecycle transition endpoint with permission gate
4. Add task template creation logic

### Phase 3: Frontend Route/Nav Rename
1. Update NavMenu.tsx labels
2. Update App.tsx route paths
3. Add redirects from old paths
4. Update permission checks

### Phase 4: Project Hub Restructure
1. Rename Asset Management → Project Hub
2. Add Data Room, O&M, Finance, Tasks, Reporting tabs
3. Integrate Due Diligence document management as Data Room tab
4. Add read-only rollup components for O&M and Finance

### Phase 5: Acquisitions Cleanup
1. Remove `Phase1Diligence` from sales stages
2. Add read-only mode to DealDetail
3. Add conversion banner

### Phase 6: Testing & Validation
1. E2E tests for all new flows
2. Permission migration verification
3. Bookmark redirect testing
4. Audit log verification

---

## 10. Summary

This gap report identifies **7 violations** of the target architecture:

1. **CRITICAL:** Sales stage includes lifecycle phase (Phase1Diligence)
2. **CRITICAL:** Project name is free text (should be system-constructed)
3. **MODERATE:** Extracted fields missing acceptance workflow
4. **MODERATE:** Deal read-only enforcement missing post-conversion
5. **MODERATE:** Lifecycle transition controls missing
6. **LOW:** Module navigation names mismatch
7. **LOW:** Duplicate project views across modules

The implementation plan provides a **6-phase approach** with:
- 40+ files requiring modification
- 3 new database migrations
- 1 new data model (LifecycleTaskTemplate)
- Route redirects for backward compatibility
- Permission key migration strategy

**Estimated Effort:** 3-4 sprints for complete implementation
