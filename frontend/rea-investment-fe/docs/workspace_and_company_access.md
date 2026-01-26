# Workspace and Company Access Documentation

## Overview

This document describes the user company membership system and workspace functionality introduced in the iliOS platform. It enables:

1. **Multi-company membership**: Users can belong to multiple companies (HoldCo/ProjectCo) without requiring project assignments
2. **User-centric workspace**: A landing view showing all accessible companies and projects
3. **Context-aware company admin**: Manage company members based on Context Bar selection

## Data Model

### UserCompanyAccess Table

The `user_company_access` table provides first-class company membership, independent of project assignments.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `user_id` | Integer | FK to users.id |
| `company_id` | Integer | FK to companies.id |
| `role` | Enum | `company_admin`, `contributor`, `read_only` |
| `status` | Enum | `active`, `invited`, `disabled` |
| `created_at` | DateTime | When membership was created |
| `created_by_user_id` | Integer | FK to users.id - who created this membership |
| `updated_at` | DateTime | Last update timestamp |

**Constraints:**
- Unique constraint on `(user_id, company_id)` - a user can only have one membership per company
- Indexes on `company_id` and `user_id` for efficient lookups

### Roles

| Role | Description |
|------|-------------|
| `company_admin` | Can manage company members, assign roles, add/remove users |
| `contributor` | Full access to company resources, cannot manage members |
| `read_only` | View-only access to company resources |

### Status

| Status | Description |
|--------|-------------|
| `active` | Active membership, user has full access based on role |
| `invited` | User has been invited but hasn't completed setup |
| `disabled` | Membership suspended, no access |

## Coexistence with UserProject

The `user_company_access` table coexists with the existing `user_projects` table:

- **UserProject**: Grants project-level access (sites table)
- **UserCompanyAccess**: Grants company-level membership without requiring project assignment

### Access Resolution Order

When determining if a user has access to a company, the system checks in this order:

1. **UserCompanyAccess**: Authoritative membership signal when present
2. **UserProject**: Implicit company access via project assignments
3. **parent_company_id**: Legacy parent company association

The accessible entities endpoint (`/api/users/account/me/accessible-entities`) unions companies from all three sources.

## API Endpoints

### Workspace API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspace` | Get workspace summary and company list |
| GET | `/api/workspace/companies/{company_id}/members` | Get company members |
| POST | `/api/workspace/companies/{company_id}/members` | Add user to company |
| PATCH | `/api/workspace/companies/{company_id}/members/{membership_id}` | Update membership |
| DELETE | `/api/workspace/companies/{company_id}/members/{membership_id}` | Remove membership |

### Request/Response Examples

#### GET /api/workspace

```json
{
  "summary": {
    "companies_count": 3,
    "projects_count": 12,
    "pending_tasks_count": 5,
    "needs_attention_count": 2
  },
  "companies": [
    {
      "company_id": 1,
      "company_name": "Green Lantern",
      "role": "company_admin",
      "access_source": "membership",
      "project_count": 5
    },
    {
      "company_id": 2,
      "company_name": "Apollo Energy",
      "role": null,
      "access_source": "project",
      "project_count": 3
    }
  ]
}
```

#### POST /api/workspace/companies/{company_id}/members

Request:
```json
{
  "user_id": 5,
  "company_id": 1,
  "role": "contributor"
}
```

Response:
```json
{
  "id": 10,
  "user_id": 5,
  "company_id": 1,
  "role": "contributor",
  "status": "active",
  "created_at": "2026-01-26T20:50:00Z",
  "created_by_user_id": 1,
  "updated_at": "2026-01-26T20:50:00Z"
}
```

## Role Enforcement

### System Users

System users (`is_system_user = true`) have full access to all companies and can:
- View all companies and projects
- Add users to any company
- Manage memberships in any company

### Company Admins

Users with `company_admin` role in a company can:
- View all members of their company
- Add new users to their company
- Update roles/status of existing members
- Remove members from their company

### Regular Users

Users with `contributor` or `read_only` roles can:
- View the member list of companies they belong to
- Cannot add/modify/remove members

## Frontend Routes

| Route | Description |
|-------|-------------|
| `/workspace` | User-centric landing with portfolio summary and company list |
| `/company-admin` | Context-aware company administration (uses currentCompanyId) |

## Usage Examples

### Adding a User to a Company Without Project Assignment

```python
# Backend (CRUD)
from app.crud.user_company_access import UserCompanyAccessCRUD
from app.models.user import CompanyRole, MembershipStatus

crud = UserCompanyAccessCRUD(db_session)
membership = crud.add_membership(
    user_id=5,
    company_id=1,
    role=CompanyRole.contributor,
    status=MembershipStatus.active,
    created_by_user_id=current_user.id
)
```

### Checking Company Admin Status

```python
crud = UserCompanyAccessCRUD(db_session)
if crud.is_company_admin(user_id=5, company_id=1):
    # User can manage this company
    pass
```

## Future Extensions

The system is designed to be extended for:

1. **Invitations**: Use `status = invited` for pending invitations, track invitation tokens
2. **Deal/Fund Roles**: Add new role types as needed
3. **Audit Trail**: `created_by_user_id` tracks who created memberships
4. **Role Hierarchy**: Roles can be extended with hierarchical permissions

## Migration Notes

- Existing `user_projects` table remains unchanged
- Legacy `parent_company_id` continues to work
- New memberships should use `user_company_access` for explicit company-level access
- Migration script: `b1c2d3e4f5g6_add_user_company_access_table.py`
