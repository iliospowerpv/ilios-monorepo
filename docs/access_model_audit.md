# Access Model Audit - iliOS Platform

## Overview

This document defines the user access model for the iliOS real estate investment platform. The system supports three levels of access grants with computed/inherited visibility.

## Entities and Tables

### Core Access Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User accounts | id, email, is_system_user, parent_company_id |
| `user_portfolio_access` | Portfolio-level grants | id, user_id, role, status |
| `user_company_access` | Company-level membership | id, user_id, company_id, role, status |
| `user_projects` | Project-level membership | id, user_id, site_id, company_id, role, status |
| `companies` | Company entities | id, name |
| `sites` | Project/Site entities | id, name, company_id |

### Text ERD

```
users
  |
  +--< user_portfolio_access (1:1 - one portfolio grant per user)
  |     - user_id FK -> users.id
  |     - role (company_admin | contributor | read_only)
  |     - status (active | invited | disabled)
  |
  +--< user_company_access (1:N - multiple company memberships)
  |     - user_id FK -> users.id
  |     - company_id FK -> companies.id
  |     - role (company_admin | contributor | read_only)
  |     - status (active | invited | disabled)
  |
  +--< user_projects (1:N - multiple project assignments)
        - user_id FK -> users.id
        - site_id FK -> sites.id
        - company_id FK -> companies.id (must match sites.company_id)
        - role (company_admin | contributor | read_only)
        - status (active | invited | disabled)

companies
  |
  +--< sites (1:N - company owns multiple projects)
        - company_id FK -> companies.id
```

## Access Grant Levels

### 1. Portfolio Level (UserPortfolioAccess)

- **Scope**: Access to ALL companies and ALL projects in the portfolio
- **Storage**: Single row in `user_portfolio_access`
- **Inheritance**: Computed at runtime, NOT materialized into company/project rows
- **Use Case**: Executive users, portfolio managers who need visibility across all assets

### 2. Company Level (UserCompanyAccess)

- **Scope**: Access to a specific company and its projects
- **Storage**: Row in `user_company_access` per company
- **Inheritance**: 
  - Does NOT inherit portfolio access (that's computed)
  - Projects within the company are visible unless explicit project assignments are required
- **Use Case**: Company administrators, company-scoped team members

### 3. Project Level (UserProject)

- **Scope**: Access to a specific project/site only
- **Storage**: Row in `user_projects` per project assignment
- **Inheritance**: 
  - Parent company is visible for context (read-only company context)
  - Does NOT grant full company access
- **Use Case**: Site managers, contractors with single-project access

## Access Precedence Rules

### Visibility Precedence (Highest to Lowest)

1. **System User**: Full access to everything (is_system_user = true)
2. **Portfolio Access**: User with active UserPortfolioAccess sees all companies/projects
3. **Company Access**: User with active UserCompanyAccess sees company and its projects
4. **Project Access**: User with active UserProject sees only that project (and parent company context)

### Role Resolution Precedence

When a user has access from multiple sources, the role is resolved as:

1. **Direct beats Inherited**: A direct grant at the accessed level takes precedence
2. **Most specific wins**: Project role > Company role > Portfolio role

Example:
- User has Portfolio access with `contributor` role
- User has Company A direct access with `company_admin` role
- For Company A: effective role = `company_admin` (direct)
- For Company B: effective role = `contributor` (inherited from portfolio)

### Status Enforcement (Non-Negotiable)

Status is checked at ALL relevant levels. Access is blocked if ANY level is suspended/disabled:

| Status | Behavior |
|--------|----------|
| `active` | Full access per role |
| `invited` | Limited access (can view, pending full activation) |
| `disabled` | Access blocked at this level |

**Critical Rule**: If portfolio access is `disabled`, user loses portfolio-inherited access everywhere but retains any direct company/project grants.

## Provenance Definitions

Each member listing includes `access_source` indicating how access was obtained:

| access_source | Description |
|---------------|-------------|
| `direct_company` | Explicit UserCompanyAccess row exists |
| `direct_project` | Explicit UserProject row exists |
| `inherited_portfolio` | Access via UserPortfolioAccess (computed, no stored row) |
| `inherited_company` | Access via company membership to project (if enabled) |
| `project_context` | Project-level user sees parent company for context only |

### Computing Provenance

```
For Company Member List (company_id = X):
  1. Query UserCompanyAccess WHERE company_id = X → access_source = 'direct_company'
  2. Query UserPortfolioAccess (active) → access_source = 'inherited_portfolio'
  3. Query UserProject WHERE company_id = X (with no company access) → access_source = 'project_only'
  4. Merge and deduplicate by user_id, noting if user has multiple sources

For Project Member List (site_id = Y, company_id = Z):
  1. Query UserProject WHERE site_id = Y → access_source = 'direct_project'
  2. Query UserCompanyAccess WHERE company_id = Z → access_source = 'inherited_company'
  3. Query UserPortfolioAccess (active) → access_source = 'inherited_portfolio'
  4. Merge and deduplicate by user_id
```

## Divestiture Scenarios

### Scenario 1: Company Sale

**Situation**: Company A is sold to new owners. Seller users must lose access to Company A.

**Actions**:
1. Delete all UserCompanyAccess rows where company_id = Company A for seller users
2. Delete all UserProject rows where company_id = Company A for seller users
3. Buyer users are granted explicit UserCompanyAccess rows
4. Portfolio users on seller side continue to see Company A ONLY if portfolio access is retained (but this is typically not desired - portfolio access should be reviewed)

**Expected Behavior**:
- Seller users with portfolio access still see Company A (portfolio is cross-company)
- To fully remove seller access: revoke portfolio access OR explicitly check divestiture exclusion list (future enhancement)

### Scenario 2: Project Sale

**Situation**: Project P (site_id) is moved from Company A to Company B (new owner).

**Actions**:
1. Update sites.company_id from A to B
2. Update all UserProject rows: company_id from A to B (maintain invariant)
3. Company A members lose visibility to Project P (unless they also have Company B access)
4. Company B members gain visibility to Project P

**Invariant Enforcement**: UserProject.company_id MUST equal sites.company_id

### Scenario 3: Portfolio Access Removal

**Situation**: User X loses portfolio-level access.

**Actions**:
1. Delete UserPortfolioAccess row for user X
2. No cascade deletes to other tables

**Expected Behavior**:
- User X loses visibility to all companies/projects they don't have direct grants for
- User X retains any explicit UserCompanyAccess and UserProject grants

### Scenario 4: Competing Access (Edge Case)

**Situation**: User has both portfolio access AND direct company access to Company A.

**Display**: Show as `access_source = 'both'` or combine provenance
**Role Resolution**: Direct company role takes precedence
**Removal**: Removing portfolio access leaves direct company access intact

## Integrity Invariants

### INV-1: UserProject.company_id Integrity

```
INVARIANT: UserProject.company_id = sites.company_id (for the referenced site_id)
```

**Enforcement**:
- Application-level validation on UserProject creation/update
- Consider DB trigger or foreign key constraint if feasible

### INV-2: No Duplicate Access Grants

```
INVARIANT: Maximum one UserPortfolioAccess per user
INVARIANT: Maximum one UserCompanyAccess per (user_id, company_id)
INVARIANT: Maximum one UserProject per (user_id, site_id)
```

**Enforcement**: Unique constraints on tables

### INV-3: No Materialized Portfolio Fan-out

```
INVARIANT: Creating portfolio access does NOT create UserCompanyAccess rows
INVARIANT: Portfolio visibility is computed, not stored
```

**Enforcement**: API logic (no auto-creation on portfolio grant)

## API Response Schema Updates

### Company Member Response

```json
{
  "membership_id": 123,        // null if inherited
  "user_id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "access_source": "direct_company | inherited_portfolio | project_only",
  "resolved_role": "company_admin | contributor | read_only",
  "resolved_status": "active | invited | disabled",
  "direct_role": "contributor",   // role from direct grant if exists
  "inherited_role": "read_only"   // role from portfolio if exists
}
```

### Project Member Response

```json
{
  "membership_id": 456,        // null if inherited
  "user_id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "access_source": "direct_project | inherited_company | inherited_portfolio",
  "resolved_role": "company_admin | contributor | read_only",
  "resolved_status": "active | invited | disabled"
}
```

## Migration Notes

### From Materialized to Computed Portfolio Access

1. Existing UserCompanyAccess rows with `created_from_portfolio=true` can be:
   - Kept for backward compatibility (but ignored in favor of computed access)
   - Cleaned up via migration (delete rows where created_from_portfolio=true)
2. Future portfolio grants will NOT create company rows
3. Member listing logic updated to compute portfolio inheritance

### Backward Compatibility

- Existing direct company/project grants remain unchanged
- API response schemas extended (new fields, existing fields preserved)
- Frontend may need updates to display provenance information

---

## Divestiture Safety Checklist

### Pre-Divestiture Verification

Before transferring ownership of a company or project:

1. **Identify affected users**
   - [ ] List all users with portfolio access (will retain visibility unless portfolio access removed)
   - [ ] List all users with direct company access to the divesting entity
   - [ ] List all users with direct project access within the divesting entity

2. **Document current state**
   - [ ] Export current UserCompanyAccess rows for the company
   - [ ] Export current UserProject rows for projects being transferred
   - [ ] Record any users with both portfolio AND direct access

### Company Divestiture Steps

1. **Revoke seller access**
   - [ ] Delete UserCompanyAccess rows for seller users on the company
   - [ ] Delete UserProject rows for seller users on company projects
   - [ ] IMPORTANT: Portfolio users retain visibility unless portfolio access is also revoked

2. **Grant buyer access**
   - [ ] Create UserCompanyAccess rows for buyer users
   - [ ] Optionally create UserProject rows for specific project access

3. **Post-transfer validation**
   - [ ] Verify seller users (non-portfolio) cannot access company
   - [ ] Verify buyer users can access company and projects
   - [ ] Check for orphaned project memberships

### Project Transfer Steps

When moving a project from Company A to Company B:

1. **Update site record**
   - [ ] Update sites.company_id from A to B

2. **Update project memberships (CRITICAL INVARIANT)**
   - [ ] Update ALL UserProject rows: set company_id from A to B
   - [ ] Verify: UserProject.company_id = sites.company_id for all rows

3. **Validate access**
   - [ ] Company A members no longer see project (unless they have Company B access)
   - [ ] Company B members can now see project
   - [ ] Portfolio users see project under new company

### SQL Validation Queries

```sql
-- Find orphaned UserProject rows (company_id mismatch)
SELECT up.id, up.user_id, up.site_id, up.company_id AS up_company_id, s.company_id AS site_company_id
FROM user_projects up
JOIN sites s ON up.site_id = s.id
WHERE up.company_id != s.company_id;

-- List users with both portfolio and direct company access
SELECT u.id, u.email, upa.role AS portfolio_role, uca.company_id, uca.role AS company_role
FROM users u
JOIN user_portfolio_access upa ON u.id = upa.user_id
JOIN user_company_access uca ON u.id = uca.user_id
WHERE upa.status = 'active' AND uca.status = 'active';

-- Count access sources per company
SELECT 
    c.id AS company_id,
    c.name AS company_name,
    COUNT(DISTINCT uca.user_id) AS direct_users,
    (SELECT COUNT(*) FROM user_portfolio_access WHERE status = 'active') AS portfolio_users,
    COUNT(DISTINCT up.user_id) AS project_only_users
FROM companies c
LEFT JOIN user_company_access uca ON c.id = uca.company_id AND uca.status = 'active'
LEFT JOIN user_projects up ON up.company_id = c.id AND up.status = 'active'
    AND up.user_id NOT IN (SELECT user_id FROM user_company_access WHERE company_id = c.id)
GROUP BY c.id, c.name;
```

### Emergency Rollback

If divestiture causes issues:

1. **Restore from checkpoint** - Replit checkpoints preserve database state
2. **Re-grant access manually** - Use exported access lists to restore
3. **Audit access** - Run validation queries to ensure consistency

---

## Access Health Admin Tool

### Overview

The Access Health tool provides system administrators with automated validation checks and repair utilities for access model data integrity.

**Location**: `/admin/access-health` (System Admin only)

*Note: `/settings/access-health` redirects to `/admin/access-health` for backward compatibility.*

### Validation Checks

| Check | Description | Auto-Repairable |
|-------|-------------|-----------------|
| **INV-1 Integrity** | UserProject.company_id must match sites.company_id | Yes |
| **Orphaned Memberships** | References to deleted companies or projects | Yes |
| **Inactive Users with Active Memberships** | Disabled users should not have active memberships | Manual review |
| **Duplicate Memberships** | Same user-entity combination appearing multiple times | Manual review |

### Database Trigger (INV-1 Enforcement)

A database trigger `trg_enforce_inv1_user_project_company_id` on the `user_projects` table automatically enforces INV-1:

```sql
-- On INSERT/UPDATE of user_projects:
-- 1. If company_id is NULL, auto-set to sites.company_id
-- 2. If company_id doesn't match sites.company_id, raise exception
```

### API Endpoints

```
GET  /api/admin/access-health
     Returns all validation results with issue details

POST /api/admin/access-health/repair/orphaned
     Removes membership rows referencing deleted entities

POST /api/admin/access-health/repair/inv1
     Normalizes company_id values in user_projects
```

### Recommended Workflow

1. **Routine Check**: Run validation weekly or after major data changes
2. **Before Divestiture**: Verify no existing issues before ownership changes
3. **Post-Migration**: Always run after database migrations affecting access tables
4. **Repair with Caution**: Review issues before running automated repairs

---

## Audit Findings (January 2026)

### Audit Summary

This audit was conducted to verify the access model is correctly hardened for divestiture scenarios.

#### Findings

| Check | Status | Details |
|-------|--------|---------|
| No materialized portfolio fan-out | **PASS** | `add_portfolio_member` endpoint creates only `user_portfolio_access` row, no company rows |
| No dual-truth rows | **PASS** | Zero `user_company_access` rows with `created_from_portfolio=true` |
| INV-1 integrity | **PASS** | Zero violations; database trigger `trg_enforce_inv1_user_projects_company_id` enforces |
| Provenance computed | **PASS** | Member listings use `access_resolution.py` for computed inheritance |
| Precedence implemented | **PASS** | `SOURCE_PRIORITY` in `access_resolution.py` defines clear precedence |

#### Architecture Verification

1. **Portfolio Access Handling**
   - `add_portfolio_member` (workspace.py:442) creates ONLY a `user_portfolio_access` row
   - No auto-provisioning of `user_company_access` rows
   - Member listings compute inherited access at runtime via `resolve_company_access()`

2. **Company/Project Provenance**
   - `get_company_members` returns `access_source` field with values:
     - `direct_company`: UserCompanyAccess row exists
     - `inherited_portfolio`: UserPortfolioAccess (computed)
     - `project_only`: UserProject without company access
   - `get_project_members` returns `access_source` with:
     - `direct_project`: UserProject row exists
     - `inherited_company`: UserCompanyAccess (computed)
     - `inherited_portfolio`: UserPortfolioAccess (computed)

3. **UserProject.company_id Integrity**
   - Application-level: `validate_company_id_integrity()` in CRUD
   - Database-level: `trg_enforce_inv1_user_projects_company_id` trigger
   - Both enforce: `UserProject.company_id = sites.company_id`

### Divestiture Safety: Test Plan

#### Test Scenario 1: Company Divestiture

**Setup**:
- User A: Portfolio access (active)
- User B: Direct company access to Company X
- User C: Direct project access to Project P1 (in Company X)

**Action**: Divest Company X (remove seller access)

**Validation**:
```sql
-- Step 1: Remove direct company access for sellers
DELETE FROM user_company_access WHERE company_id = [Company X] AND user_id IN ([seller_ids]);

-- Step 2: Remove project access for sellers
DELETE FROM user_projects WHERE company_id = [Company X] AND user_id IN ([seller_ids]);

-- Step 3: Verify no orphaned access
SELECT * FROM user_projects WHERE company_id = [Company X];
SELECT * FROM user_company_access WHERE company_id = [Company X];
```

**Expected Results**:
- User A (portfolio): Still sees Company X (portfolio grants access to all)
- User B: No longer sees Company X
- User C: No longer sees Project P1 or Company X context
- Buyer users: Granted new UserCompanyAccess rows

**Note**: To fully remove seller portfolio users from divested company, either:
1. Revoke their portfolio access entirely
2. Implement divestiture exclusion list (future enhancement)

#### Test Scenario 2: Project Transfer Between Companies

**Setup**:
- Project P moves from Company A to Company B
- User D: Company A member
- User E: Company B member
- User F: Direct project access to P

**Action**: Transfer project ownership

**Validation**:
```sql
-- Step 1: Update site record
UPDATE sites SET company_id = [Company B] WHERE id = [Project P];

-- Step 2: Update project memberships (CRITICAL: maintains INV-1)
UPDATE user_projects SET company_id = [Company B] WHERE site_id = [Project P];

-- Step 3: Verify invariant
SELECT up.id, up.company_id, s.company_id 
FROM user_projects up 
JOIN sites s ON up.site_id = s.id 
WHERE up.site_id = [Project P] AND up.company_id != s.company_id;
-- Should return 0 rows
```

**Expected Results**:
- User D: No longer sees Project P (unless also has Company B access)
- User E: Now sees Project P via company inheritance
- User F: Still sees Project P (direct project access retained)

#### Test Scenario 3: Portfolio Access Removal

**Setup**:
- User G: Portfolio access + direct Company A access

**Action**: Remove portfolio access

**Validation**:
```sql
-- Remove portfolio access
DELETE FROM user_portfolio_access WHERE user_id = [User G];

-- Verify direct grants retained
SELECT * FROM user_company_access WHERE user_id = [User G];
-- Should show Company A membership
```

**Expected Results**:
- User G: Loses visibility to companies B, C, D (portfolio-inherited)
- User G: Retains visibility to Company A (direct grant preserved)

### Risk Mitigations Implemented

| Risk | Mitigation | Enforcement |
|------|------------|-------------|
| Portfolio fan-out creates dual truth | No auto-provisioning of company rows | API logic |
| company_id drift in UserProject | Integrity check on create/update | App + DB trigger |
| Orphaned memberships after entity deletion | Cascade deletes via FK constraints | Database |
| Privilege escalation via multiple grants | Precedence rules (direct > inherited) | `access_resolution.py` |

### Recommendations for Future Enhancements

1. **Divestiture Exclusion Lists**: Allow portfolio users to be excluded from specific companies without revoking portfolio access entirely

2. **Audit Trail**: Add logging for all access grant changes (create/update/delete) for compliance

3. **Bulk Access Revocation API**: Add endpoint for bulk-removing access during divestiture events

4. **Access Diff Tool**: Pre-divestiture tool showing which users will lose/gain access
