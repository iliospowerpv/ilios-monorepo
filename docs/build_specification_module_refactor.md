# Build Specification: Module Boundary Refactor

**Document Version:** 2.0  
**Date:** February 2, 2026  
**Status:** GREENFIELD REFACTOR - Breaking Changes Acceptable

---

## 1. Current State Inventory

### 1.1 Current Data Model (Confirmed)

| Entity | Table | Model File |
|--------|-------|------------|
| Project | `sites` | `app/models/site.py` → `Site` |
| Project Extended Data | `site_additional_fields` | `app/models/site.py` → `SiteAdditionalFieldList` |
| Deal (Pre-Acquisition) | `deals` | `app/models/sales.py` → `Deal` |
| Document | `documents` | `app/models/document.py` → `Document` |
| Extracted Field | `document_keys` | `app/models/document.py` → `DocumentKey` |
| Task | `tasks` | `app/models/task.py` → `Task` |
| Audit Trail | `sales_state_transitions` | `app/models/sales.py` → `SalesStateTransition` |
| Role/Permissions | `roles` | `app/models/role.py` → `Role` (JSON permissions map) |

### 1.2 Lifecycle State Location

**Current:** `site_additional_fields.lifecycle_state` (Enum column)

```python
# app/models/site.py line 365
lifecycle_state = Column(Enum(LifecycleState), nullable=True, default=LifecycleState.sales_pre_diligence)
```

**Enum Definition:** `app/static/sales.py`
```python
class LifecycleState(enum.Enum):
    sales_pre_diligence = "Sales / Pre-Diligence"
    due_diligence = "Due Diligence"
    implementation = "Implementation"
    placed_in_service = "Placed in Service"
    operations = "Operations"
```

### 1.3 Current Conversion Flow

**Endpoint:** `POST /api/sales/deals/{deal_id}/convert`  
**File:** `app/routers/sales/deals.py` lines 250-351

**Current Flow:**
1. Validate deal exists and not already converted
2. Validate state code
3. Create `Site` record with deal data
4. Create `SiteAdditionalFieldList` with `lifecycle_state = due_diligence`
5. Set `deal.is_converted = True`, `deal.converted_to_project_id = site.id`
6. Create audit log entry (`SalesStateTransition`)

**Missing per spec:**
- ❌ System-constructed project name (`constructed_name`)
- ❌ Data Room checklist shell creation
- ❌ Finance shell creation
- ❌ O&M shell creation
- ❌ Signed agreement required/waiver flag

### 1.4 Current Nav/Routes

**File:** `frontend/.../NavMenu/NavMenu.tsx` line 72-89

```typescript
const menuItems = [
  ['home', <HomeIcon />, 'Home', '/home', false],
  ['portfolio', <DashboardIcon />, 'Portfolio', '/portfolio', false],
  ['sales', <TrendingUpIcon />, 'Sales', '/sales', false],  // → Acquisitions
  ['due-diligence', <FactCheckIcon />, 'Diligence', '/due-diligence', false],  // → Project Hub tab
  ['operations-and-maintenance', <WhatshotIcon />, 'O&M', '/operations-and-maintenance', false],
  ['asset-management', <AccountBalanceIcon />, 'Asset Management', '/asset-management', false],  // → Project Hub
  ['finance', <AccountBalanceWalletIcon />, 'Finance', '/finance', false],
  ['reports', <AssessmentIcon />, 'Reports', '/reports', false],
  ['portfolio-admin', <AdminPanelSettingsIcon />, 'Portfolio Admin', '/portfolio-admin', false],  // → Admin
  ['admin', <SettingsIcon />, 'Admin', '/admin/access-health', false],
];
```

---

## 2. Target State Mapping

### 2.1 Target Left Nav Modules

| Module | Route | Purpose |
|--------|-------|---------|
| Home | `/home` | Unified landing page |
| Acquisitions | `/acquisitions` | Deal pipeline only |
| Project Hub | `/project-hub` | Canonical project shell |
| O&M | `/om` | Devices, telemetry, alerts, work orders |
| Finance | `/finance` | Budgets, approvals, invoices |
| Reports | `/reports` | Portfolio + project reports |
| Admin | `/admin` | Portfolio admin + settings |

### 2.2 Project Hub Tabs

| Tab | Route | Owner |
|-----|-------|-------|
| Overview | `/project-hub/:id/overview` | Project Hub |
| Data Room | `/project-hub/:id/data-room` | Data Room (documents, extraction) |
| O&M | `/project-hub/:id/om` | Read-only rollup → deep links to `/om` |
| Finance | `/project-hub/:id/finance` | Read-only rollup → deep links to `/finance` |
| Tasks | `/project-hub/:id/tasks` | Unified task view |
| Reporting | `/project-hub/:id/reports` | Project-level reports |

### 2.3 Route Redirects (Backward Compatibility)

| Old Route | New Route | Action |
|-----------|-----------|--------|
| `/sales/*` | `/acquisitions/*` | 301 redirect |
| `/asset-management/companies/:cid/sites/:sid/*` | `/project-hub/:sid/*` | 301 redirect |
| `/due-diligence/companies/:cid/sites/:sid/*` | `/project-hub/:sid/data-room/*` | 301 redirect |
| `/operations-and-maintenance/*` | `/om/*` | 301 redirect |
| `/portfolio-admin/*` | `/admin/*` | 301 redirect |

---

## 3. Schema Changes (DDL-Level)

### 3.1 Extend `document_keys` Table

**Migration Name:** `add_extraction_workflow_to_document_keys`

```sql
ALTER TABLE document_keys
  ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'manual',
  ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'accepted',
  ADD COLUMN accepted_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN accepted_at TIMESTAMP,
  ADD COLUMN override_value VARCHAR,
  ADD COLUMN overridden_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN overridden_at TIMESTAMP,
  ADD COLUMN canonical_field VARCHAR(100);

-- Constraint for source
ALTER TABLE document_keys
  ADD CONSTRAINT chk_source CHECK (source IN ('ai', 'manual'));

-- Constraint for status
ALTER TABLE document_keys
  ADD CONSTRAINT chk_status CHECK (status IN ('proposed', 'accepted', 'overridden', 'rejected'));

-- Index for faster queries
CREATE INDEX idx_document_keys_status ON document_keys(status);
CREATE INDEX idx_document_keys_canonical_field ON document_keys(canonical_field);
```

### 3.2 Add `constructed_name` and `name_override` to `sites`

**Migration Name:** `add_project_name_fields_to_sites`

```sql
ALTER TABLE sites
  ADD COLUMN constructed_name VARCHAR(255),
  ADD COLUMN name_override VARCHAR(255),
  ADD COLUMN name_override_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN name_override_at TIMESTAMP;

-- Display name computed: COALESCE(name_override, constructed_name, name)
-- Note: We keep 'name' for backward compatibility during migration
```

### 3.3 Add Signed Agreement Tracking

**Migration Name:** `add_signed_agreement_tracking`

```sql
ALTER TABLE sites
  ADD COLUMN signed_agreement_document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
  ADD COLUMN signed_agreement_waived BOOLEAN DEFAULT FALSE,
  ADD COLUMN signed_agreement_waived_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN signed_agreement_waived_at TIMESTAMP;
```

### 3.4 Create Lifecycle Task Templates Table

**Migration Name:** `create_lifecycle_task_templates`

```sql
CREATE TABLE lifecycle_task_templates (
  id SERIAL PRIMARY KEY,
  lifecycle_state VARCHAR(50) NOT NULL,
  task_name VARCHAR(255) NOT NULL,
  task_description TEXT,
  role_assignment VARCHAR(100),  -- e.g., 'company_admin', 'contributor'
  due_days_from_transition INTEGER DEFAULT 7,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ltt_lifecycle_state ON lifecycle_task_templates(lifecycle_state);
```

### 3.5 Rename `sales_state_transitions` → `audit_log_lifecycle`

**Migration Name:** `rename_sales_transitions_to_audit_log`

```sql
-- Keep existing table but add more fields for comprehensive audit
ALTER TABLE sales_state_transitions
  ADD COLUMN reason TEXT,
  ADD COLUMN actor_role VARCHAR(50);

-- Rename for clarity (optional, can keep original name)
-- ALTER TABLE sales_state_transitions RENAME TO lifecycle_audit_log;
```

---

## 4. Backend Changes

### 4.1 New/Modified Endpoints

#### 4.1.1 Acquisitions Module (renamed from Sales)

| Endpoint | Method | Change |
|----------|--------|--------|
| `/api/acquisitions/deals` | GET | Rename from `/api/sales/deals` |
| `/api/acquisitions/deals/{id}` | GET/PUT/DELETE | Rename from `/api/sales/deals/{id}` |
| `/api/acquisitions/deals/{id}/convert` | POST | Enhance conversion logic |
| `/api/acquisitions/pipeline` | GET | Rename from `/api/sales/pipeline` |

**Files to modify:**
- `app/routers/sales/deals.py` → rename to `app/routers/acquisitions/deals.py`
- `app/routers/sales/__init__.py` → rename to `app/routers/acquisitions/__init__.py`
- `app/crud/sales.py` → rename to `app/crud/acquisitions.py`

#### 4.1.2 Conversion Endpoint Enhancements

**File:** `app/routers/acquisitions/deals.py`

```python
@router.post("/{deal_id}/convert")
def convert_deal_to_project(deal_id: int, data: ConvertToProjectRequest, db: Session, current_user: User):
    # EXISTING validation...
    
    # NEW: Generate system-constructed name
    # Format: {State}-{CompanyAbbr}-{SequenceNum}
    company = db.query(Company).get(data.company_id)
    sequence = db.query(Site).filter(Site.company_id == data.company_id).count() + 1
    constructed_name = f"{deal.state}-{company.abbreviation or company.name[:4].upper()}-{sequence:04d}"
    
    # Create Site with constructed_name
    site = Site()
    site.constructed_name = constructed_name
    site.name = deal.name  # Keep original for backward compat
    # ... existing fields ...
    
    # NEW: Create Data Room shell (document checklist)
    _create_data_room_shell(db, site.id)
    
    # NEW: Create Finance shell
    _create_finance_shell(db, site.id, data.company_id)
    
    # NEW: Create O&M shell (placeholder)
    _create_om_shell(db, site.id)
    
    # NEW: Set signed_agreement flag
    site.signed_agreement_document_id = None  # Will be uploaded later
    site.signed_agreement_waived = False
    
    # ... existing commit logic ...
```

#### 4.1.3 Project Hub Endpoints

**New File:** `app/routers/project_hub/__init__.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/project-hub/{id}` | GET | Get project details |
| `/api/project-hub/{id}/overview` | GET | Get overview data |
| `/api/project-hub/{id}/lifecycle` | POST | Transition lifecycle state |
| `/api/project-hub/{id}/signed-agreement` | POST | Upload/link signed agreement |
| `/api/project-hub/{id}/signed-agreement/waive` | POST | Waive signed agreement requirement |
| `/api/project-hub/{id}/blockers` | GET | Get readiness blockers |
| `/api/project-hub/{id}/next-steps` | GET | Get recommended next steps |

#### 4.1.4 Data Room Endpoints (Document Extraction Workflow)

**File:** `app/routers/documents/extraction.py` (NEW)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/documents/{doc_id}/keys` | GET | Get all extracted fields |
| `/api/documents/{doc_id}/keys/{key_id}/accept` | POST | Accept proposed value |
| `/api/documents/{doc_id}/keys/{key_id}/reject` | POST | Reject proposed value |
| `/api/documents/{doc_id}/keys/{key_id}/override` | POST | Override with new value |
| `/api/documents/{doc_id}/keys/pending` | GET | Get pending proposals |

#### 4.1.5 Lifecycle Transition Endpoint

**File:** `app/routers/project_hub/lifecycle.py` (NEW)

```python
@router.post("/{project_id}/lifecycle")
def transition_lifecycle(
    project_id: int,
    data: LifecycleTransitionRequest,
    db: Session,
    current_user: User = Depends(get_current_user)
):
    # PERMISSION CHECK: Only Company Admin or Superuser
    if not current_user.is_system_user:
        # Check if user is company admin for this project's company
        project = db.query(Site).get(project_id)
        access = db.query(UserCompanyAccess).filter(
            UserCompanyAccess.user_id == current_user.id,
            UserCompanyAccess.company_id == project.company_id,
            UserCompanyAccess.role == 'company_admin',
            UserCompanyAccess.status == 'active'
        ).first()
        if not access:
            raise HTTPException(403, "Only Company Admin or Superuser can transition lifecycle")
    
    # VALIDATION: Cannot advance past Diligence without signed agreement
    if data.to_state in [LifecycleState.implementation, LifecycleState.placed_in_service, LifecycleState.operations]:
        if not project.signed_agreement_document_id and not project.signed_agreement_waived:
            raise HTTPException(400, "Signed agreement required to advance past Diligence")
    
    # Get current state from SiteAdditionalFieldList
    additional_fields = db.query(SiteAdditionalFieldList).filter_by(site_id=project_id).first()
    old_state = additional_fields.lifecycle_state
    
    # Update lifecycle state
    additional_fields.lifecycle_state = data.to_state
    
    # AUDIT: Log transition
    transition = SalesStateTransition(
        site_id=project_id,
        transition_type="lifecycle",
        from_state=old_state.value if old_state else None,
        to_state=data.to_state.value,
        reason=data.reason,
        changed_by_id=current_user.id,
        actor_role="system_user" if current_user.is_system_user else "company_admin"
    )
    db.add(transition)
    
    # AUTO-CREATE: Task templates for this lifecycle state
    _create_lifecycle_tasks(db, project_id, data.to_state, current_user.id)
    
    db.commit()
    return {"status": "success", "new_state": data.to_state.value}
```

### 4.2 CRUD Module Changes

| Current File | New File | Change |
|-------------|----------|--------|
| `app/crud/sales.py` | `app/crud/acquisitions.py` | Rename |
| - | `app/crud/project_hub.py` | NEW: Project operations |
| `app/crud/document.py` | `app/crud/document.py` | ADD: Acceptance workflow methods |
| - | `app/crud/lifecycle.py` | NEW: Lifecycle transition logic |

### 4.3 Schema Updates

**File:** `app/schema/document.py`

```python
class DocumentKeySource(str, Enum):
    ai = "ai"
    manual = "manual"

class DocumentKeyStatus(str, Enum):
    proposed = "proposed"
    accepted = "accepted"
    overridden = "overridden"
    rejected = "rejected"

class DocumentKeyExtended(BaseModel):
    id: int
    document_id: int
    name: str
    value: Optional[str]
    source: DocumentKeySource
    status: DocumentKeyStatus
    accepted_by_id: Optional[int]
    accepted_at: Optional[datetime]
    override_value: Optional[str]
    overridden_by_id: Optional[int]
    overridden_at: Optional[datetime]
    canonical_field: Optional[str]
    
class DocumentKeyAcceptRequest(BaseModel):
    canonical_field: Optional[str] = None  # Optional: map to Site canonical field

class DocumentKeyOverrideRequest(BaseModel):
    override_value: str
    canonical_field: Optional[str] = None
```

---

## 5. Frontend Changes

### 5.1 Route Structure Changes

**File:** `frontend/src/App.tsx`

```typescript
// TARGET ROUTE STRUCTURE
<Route path="/acquisitions" element={<AcquisitionsModuleContainer />}>
  <Route index element={<AcquisitionsHome />} />
  <Route path="deal/:dealId" element={<DealDetail />} />
</Route>

<Route path="/project-hub" element={<ProjectHubModuleContainer />}>
  <Route index element={<ProjectList />} />
  <Route path=":projectId" element={<ProjectShell />}>
    <Route index element={<Navigate to="overview" replace />} />
    <Route path="overview" element={<ProjectOverview />} />
    <Route path="data-room" element={<DataRoom />} />
    <Route path="data-room/:documentId" element={<DocumentDetail />} />
    <Route path="om" element={<ProjectOMRollup />} />
    <Route path="finance" element={<ProjectFinanceRollup />} />
    <Route path="tasks" element={<ProjectTasks />} />
    <Route path="reports" element={<ProjectReports />} />
  </Route>
</Route>

<Route path="/om" element={<OMModuleContainer />}>
  <Route index element={<OMDashboard />} />
  <Route path="projects/:projectId/*" element={<ProjectOMDetail />} />
</Route>

<Route path="/finance" element={<FinanceModuleContainer />}>
  <Route index element={<FinanceDashboard />} />
  <Route path="projects/:projectId/*" element={<ProjectFinanceDetail />} />
</Route>

<Route path="/reports" element={<ReportsModuleContainer />}>
  <Route index element={<ReportsDashboard />} />
</Route>

<Route path="/admin" element={<AdminModuleContainer />}>
  <Route index element={<PortfolioAdmin />} />
  <Route path="companies/:companyId" element={<CompanyAdmin />} />
  <Route path="projects/:projectId" element={<ProjectAdmin />} />
  <Route path="settings/*" element={<Settings />} />
</Route>

{/* Legacy redirects */}
<Route path="/sales/*" element={<Navigate to="/acquisitions" replace />} />
<Route path="/asset-management/*" element={<Navigate to="/project-hub" replace />} />
<Route path="/due-diligence/*" element={<Navigate to="/project-hub" replace />} />
<Route path="/operations-and-maintenance/*" element={<Navigate to="/om" replace />} />
<Route path="/portfolio-admin/*" element={<Navigate to="/admin" replace />} />
```

### 5.2 NavMenu.tsx Updates

```typescript
const menuItems: [string, React.ReactNode, string, string, boolean][] = [
  ['home', <HomeIcon key="home" />, 'Home', '/home', false],
  ['acquisitions', <TrendingUpIcon key="acquisitions" />, 'Acquisitions', '/acquisitions', false],
  ['project-hub', <AccountBalanceIcon key="project-hub" />, 'Project Hub', '/project-hub', false],
  ['om', <WhatshotIcon key="om" />, 'O&M', '/om', false],
  ['finance', <AccountBalanceWalletIcon key="finance" />, 'Finance', '/finance', false],
  ['reports', <AssessmentIcon key="reports" />, 'Reports', '/reports', false],
  ['admin', <AdminPanelSettingsIcon key="admin" />, 'Admin', '/admin', false],
];
```

### 5.3 Module Folder Restructure

| Current Folder | Action | New Location |
|---------------|--------|--------------|
| `modules/sales` | Rename | `modules/acquisitions` |
| `modules/asset-management` | Rename | `modules/project-hub` |
| `modules/due-diligence` | Merge | `modules/project-hub/tabs/DataRoom` |
| `modules/operations-and-maintenance` | Rename | `modules/om` |
| `modules/portfolio-admin` | Merge | `modules/admin` |
| `modules/settings` | Merge | `modules/admin/settings` |

### 5.4 New/Modified Components

#### 5.4.1 Project Hub Shell (NEW)

**File:** `modules/project-hub/components/ProjectShell/ProjectShell.tsx`

```typescript
const ProjectShell: React.FC = () => {
  const { projectId } = useParams();
  const { data: project } = useQuery(['project', projectId], () => fetchProject(projectId));
  
  const tabs = [
    { label: 'Overview', path: 'overview' },
    { label: 'Data Room', path: 'data-room' },
    { label: 'O&M', path: 'om' },
    { label: 'Finance', path: 'finance' },
    { label: 'Tasks', path: 'tasks' },
    { label: 'Reporting', path: 'reports' },
  ];
  
  return (
    <Box>
      <ProjectHeader project={project} />
      <LifecycleStrip lifecycleState={project?.lifecycleState} />
      <ReadinessBlockers projectId={projectId} />
      <TabNavigation tabs={tabs} />
      <Outlet context={{ project }} />
    </Box>
  );
};
```

#### 5.4.2 Deal Read-Only Banner (MODIFY)

**File:** `modules/acquisitions/pages/DealDetail/DealDetail.tsx`

```typescript
const DealDetail: React.FC = () => {
  const { dealId } = useParams();
  const { data: deal } = useQuery(['deal', dealId], () => fetchDeal(dealId));
  
  if (deal?.isConverted) {
    return (
      <Box>
        <Alert severity="info" sx={{ mb: 2 }}>
          <AlertTitle>Deal Converted</AlertTitle>
          This opportunity has been converted to a Project.
          <Button 
            component={Link} 
            to={`/project-hub/${deal.convertedToProjectId}`}
            variant="contained"
            sx={{ ml: 2 }}
          >
            Continue in Project Hub
          </Button>
        </Alert>
        <DealReadOnlyView deal={deal} />
      </Box>
    );
  }
  
  return <DealEditableView deal={deal} />;
};
```

#### 5.4.3 Data Room Extraction Workflow (NEW)

**File:** `modules/project-hub/tabs/DataRoom/components/ExtractionField/ExtractionField.tsx`

```typescript
interface ExtractionFieldProps {
  field: DocumentKeyExtended;
  onAccept: (fieldId: number, canonicalField?: string) => void;
  onReject: (fieldId: number) => void;
  onOverride: (fieldId: number, newValue: string, canonicalField?: string) => void;
}

const ExtractionField: React.FC<ExtractionFieldProps> = ({ field, onAccept, onReject, onOverride }) => {
  if (field.status === 'proposed') {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Chip label="PROPOSED" color="warning" size="small" />
        <Typography>{field.name}: {field.value}</Typography>
        <IconButton onClick={() => onAccept(field.id)} color="success">
          <CheckIcon />
        </IconButton>
        <IconButton onClick={() => onReject(field.id)} color="error">
          <CloseIcon />
        </IconButton>
        <IconButton onClick={() => setShowOverride(true)}>
          <EditIcon />
        </IconButton>
      </Box>
    );
  }
  
  if (field.status === 'accepted') {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Chip label="ACCEPTED" color="success" size="small" />
        <Typography>{field.name}: {field.value}</Typography>
        <Typography variant="caption" color="text.secondary">
          by {field.acceptedByName} on {formatDate(field.acceptedAt)}
        </Typography>
      </Box>
    );
  }
  
  // ... other statuses
};
```

### 5.5 Permission Key Updates

**File:** `modules/*/permission-checks.ts`

| Old Permission Key | New Permission Key |
|-------------------|-------------------|
| `Sales` | `Acquisitions` |
| `Asset Management` | `Project Hub` |
| `Diligence` | `Data Room` |
| `O&M (Production Monitoring)` | `O&M` |
| `Settings Page` | `Admin` |

---

## 6. Permission/RBAC Changes

### 6.1 New Permission Structure

```json
{
  "Acquisitions": { "view": true, "edit": true, "convert": true },
  "Project Hub": { "view": true, "edit": true },
  "Data Room": { "view": true, "edit": true, "accept_fields": true },
  "O&M": { "view": true, "edit": true },
  "Finance": { "view": true, "edit": true, "approve": true },
  "Reports": { "view": true },
  "Admin": { "view": true, "edit": true },
  "Lifecycle": { "transition": true }
}
```

### 6.2 Permission Migration SQL

```sql
-- Migrate existing permissions to new keys
UPDATE roles SET permissions = permissions || 
  jsonb_build_object('Acquisitions', permissions->'Sales')
WHERE permissions ? 'Sales';

UPDATE roles SET permissions = permissions || 
  jsonb_build_object('Project Hub', permissions->'Asset Management')
WHERE permissions ? 'Asset Management';

UPDATE roles SET permissions = permissions || 
  jsonb_build_object('Data Room', permissions->'Diligence')
WHERE permissions ? 'Diligence';

UPDATE roles SET permissions = permissions || 
  jsonb_build_object('O&M', permissions->'O&M (Production Monitoring)')
WHERE permissions ? 'O&M (Production Monitoring)';

-- Add Lifecycle.transition for admin roles
UPDATE roles SET permissions = permissions || 
  '{"Lifecycle": {"transition": true}}'::jsonb
WHERE name IN ('System Admin', 'Company Admin');
```

---

## 7. Acceptance Criteria Checklist

### 7.1 Acquisitions Module

- [ ] Route `/acquisitions` loads deal pipeline
- [ ] Route `/acquisitions/deal/:id` loads deal detail
- [ ] Converted deals show read-only view with banner
- [ ] Banner links to `/project-hub/:projectId`
- [ ] All edit controls disabled when `is_converted = true`
- [ ] Legacy route `/sales/*` redirects to `/acquisitions/*`

### 7.2 Project Hub Module

- [ ] Route `/project-hub` lists accessible projects
- [ ] Route `/project-hub/:id` loads project shell with tabs
- [ ] Overview tab shows canonical project record
- [ ] Data Room tab shows documents + extraction workflow
- [ ] O&M tab shows read-only rollup with deep links
- [ ] Finance tab shows read-only snapshot with deep links
- [ ] Tasks tab shows unified task list
- [ ] Reporting tab shows project reports
- [ ] Legacy route `/asset-management/*` redirects to `/project-hub/*`

### 7.3 Data Room (Extraction Workflow)

- [ ] AI-extracted fields show "PROPOSED" status
- [ ] Accept button marks field as "accepted" with user/timestamp
- [ ] Reject button marks field as "rejected"
- [ ] Override allows entering new value, marks as "overridden"
- [ ] Accepted/overridden values can update canonical Site fields
- [ ] Audit trail visible in UI (who/when/what)

### 7.4 Deal → Project Conversion

- [ ] Conversion generates `constructed_name` (e.g., `TX-ACME-0001`)
- [ ] Conversion creates Site record
- [ ] Conversion creates Data Room shell (checklist association)
- [ ] Conversion creates Finance shell
- [ ] Conversion creates O&M shell
- [ ] `signed_agreement_document_id` is null (upload later)
- [ ] Deal becomes read-only after conversion
- [ ] Audit log entry created

### 7.5 Lifecycle Management

- [ ] Lifecycle strip shows current state prominently
- [ ] Transition only allowed by Company Admin or Superuser
- [ ] Cannot advance past Diligence without signed agreement (or waiver)
- [ ] Each transition logged to audit table
- [ ] Task templates auto-created on transition
- [ ] Permission denied error for unauthorized users

### 7.6 Project Name

- [ ] `constructed_name` generated at conversion
- [ ] `name_override` editable only by Admin/Superuser
- [ ] `display_name` = `name_override ?? constructed_name`
- [ ] Name override changes logged to audit

### 7.7 Tasks

- [ ] Single `tasks` table (no duplication)
- [ ] Tasks linkable from: Document, Alert, Device, Manual
- [ ] My Work view shows user's assigned tasks
- [ ] Project Tasks view shows all project tasks
- [ ] Context Tasks appear within module screens

### 7.8 Navigation

- [ ] Left nav shows: Home, Acquisitions, Project Hub, O&M, Finance, Reports, Admin
- [ ] Permission-based visibility works correctly
- [ ] All legacy routes redirect appropriately

---

## 8. File Change Summary

### 8.1 Backend Files (35 files)

| Category | Files to Change | Type |
|----------|----------------|------|
| Routers | 6 files | Rename/Modify |
| CRUD | 4 files | Rename/Modify/Create |
| Models | 3 files | Modify |
| Schemas | 4 files | Modify/Create |
| Migrations | 5 files | Create |
| Static | 1 file | Modify |
| Helpers | 2 files | Create |

### 8.2 Frontend Files (50+ files)

| Category | Files to Change | Type |
|----------|----------------|------|
| App.tsx | 1 file | Major rewrite |
| NavMenu | 1 file | Modify |
| Modules | 6 folders | Rename/Restructure |
| Components | 15+ files | Create/Modify |
| API hooks | 10+ files | Rename/Modify |
| Types | 5+ files | Modify |
| Tests | 20+ files | Update paths |

---

## 9. Implementation Order

### Phase 1: Backend Schema (Day 1)
1. Create Alembic migrations for all schema changes
2. Run migrations on dev database
3. Verify schema changes

### Phase 2: Backend Logic (Days 2-3)
1. Rename sales → acquisitions (routers, CRUD)
2. Enhance conversion endpoint
3. Create project-hub endpoints
4. Create extraction workflow endpoints
5. Create lifecycle transition endpoint

### Phase 3: Frontend Routes (Day 4)
1. Update App.tsx with new route structure
2. Add legacy redirects
3. Update NavMenu.tsx

### Phase 4: Frontend Modules (Days 5-7)
1. Rename module folders
2. Create ProjectShell component
3. Integrate Data Room as tab
4. Create extraction workflow UI
5. Add read-only deal view with banner

### Phase 5: Testing (Days 8-9)
1. Update all tests for new paths
2. E2E testing of conversion flow
3. E2E testing of lifecycle transitions
4. Permission testing

### Phase 6: Cleanup (Day 10)
1. Remove dead code
2. Update documentation
3. Final review

---

**Total Estimated Effort:** 10 development days
