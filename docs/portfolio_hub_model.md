# Portfolio Hub Access Model

## Overview

The portfolio hub model provides bounded, hierarchical access control for users who need access to multiple companies within a portfolio group. Instead of granting global access to all companies, portfolio access is scoped to specific "portfolio hubs" - designated companies that serve as group anchors for other companies.

## Problem Solved

Previously, `UserPortfolioAccess` granted users access to ALL companies in the system (global scope). This was a security and access control issue because:
- Users could see companies outside their intended scope
- No way to segment portfolio users by company groups
- Violated principle of least privilege

## Data Model

### Company.portfolio_hub_id

A self-referencing foreign key on the `companies` table:
- `NULL` or points to self → Company is a "hub" (can be a group anchor)
- Points to another company → Company belongs to that hub's group

```sql
ALTER TABLE companies ADD COLUMN portfolio_hub_id INTEGER REFERENCES companies(id);
```

### UserPortfolioAccess.portfolio_hub_company_id

Links portfolio access to a specific hub:
- Required field (not nullable after migration)
- Combined with `user_id` forms a unique constraint
- A user can have multiple portfolio access records (one per hub)

```sql
ALTER TABLE user_portfolio_access ADD COLUMN portfolio_hub_company_id INTEGER REFERENCES companies(id);
CREATE UNIQUE INDEX uix_user_hub ON user_portfolio_access(user_id, portfolio_hub_company_id);
```

## Access Resolution

### For portfolio users:
1. Find all `UserPortfolioAccess` records for the user (active status)
2. For each access record, get the `portfolio_hub_company_id`
3. Query companies where `portfolio_hub_id = hub_id OR id = hub_id`
4. User has access to those companies and their projects

### Helper Functions (app/helpers/portfolio_hub.py)

- `resolve_company_hub_id(db, company_id)` → Returns the hub ID for a company
- `get_portfolio_group_company_ids(db, hub_id)` → Returns all company IDs in a hub group
- `user_has_portfolio_access_to_company(db, user_id, company_id)` → Boolean access check

## Affected Areas

### Backend
- **workspace.py**: Uses hub-scoped queries for accessible companies
- **account.py (accessible-entities)**: Includes hub companies in context bar data
- **telemetry/telemetry.py**: DAS connections can be shared within hub boundary
- **das_connection.py**: `get_hub_connections()` for hub-scoped connection discovery

### Frontend
- **AddUserDialog**: Requires hub selection for portfolio-level access
- **PortfolioLevelPage**: Shows "Portfolio Hub" column in members table
- **Context Bar**: Gets hub-scoped companies from accessible-entities API

## Migration Strategy

The Alembic migration includes a backfill:
1. Portfolio users with `parent_company_id` → Assigned to that company's hub
2. Portfolio users without parent company → Status set to 'invited' (admin must assign hub)
3. Companies without explicit hub → Left as NULL (self-referential = own hub)

## API Endpoints

### New Endpoints
- `GET /api/workspace/portfolio/hubs` - List available portfolio hubs
- `GET /api/telemetry/sites/{site_id}/available-connections` - Get hub-scoped DAS connections

### Modified Endpoints
- `POST /api/workspace/portfolio/members` - Requires `portfolio_hub_company_id`
- `GET /api/workspace/portfolio/members` - Returns hub info per member
- `GET /api/users/account/me/accessible-entities` - Includes hub-scoped companies

## Usage Examples

### Adding a portfolio user
```javascript
await ApiClient.workspace.addPortfolioMember({
  user_id: 123,
  portfolio_hub_company_id: 456, // Required hub selection
  role: 'contributor'
});
```

### Querying hub companies
```python
from app.helpers.portfolio_hub import get_portfolio_group_company_ids

hub_id = 1  # The hub company
company_ids = get_portfolio_group_company_ids(db_session, hub_id)
# Returns [1, 5, 8, 12] - hub + member companies
```

## Security Guardrails

### Telemetry Hub Boundary Enforcement

**GUARDRAIL: All telemetry connections, sharing, discovery, and UI visibility MUST be constrained to portfolio_hub_id boundaries.**

No telemetry object, credential, or health signal may be visible outside its hub scope, except to system administrators in explicit admin views.

#### Enforcement Points

| Endpoint/Operation | Scope | Implementation |
|-------------------|-------|----------------|
| Connection CRUD (`/settings/.../connections`) | Company-only | Uses `get_authorized_company` - can only manage own connections |
| Connection Discovery (`/telemetry/.../available-connections`) | Hub-scoped | Uses `get_hub_connections()` - sees own + hub-shared connections |
| Site Mapping Create | Hub-scoped | Validates `connection_id` against `get_hub_connections()` |
| Site Mapping Update | Hub-scoped | Validates `connection_id` against `get_hub_connections()` |
| Health Monitoring | Site-scoped | Only queries site's own devices from BigQuery |
| Device Mapping | Site-scoped | Only site's own devices can be mapped |

#### Key Implementation Details

1. **DASConnectionCRUD.get_hub_connections(company_id)**: Returns all connections accessible to a company:
   - Own company's connections
   - Connections from other companies in the same portfolio hub

2. **Connection ID Validation**: Both `create_site_mapping()` and `update_site_mapping()` must validate that the provided `connection_id` is in the accessible connections list

3. **No Cross-Hub Leakage**: A company in Hub A cannot use connections from Hub B, even if both hubs exist in the same database

## Future Considerations

- Admin UI for managing hub assignments (companies → hubs)
- Bulk hub migration tools for reorganizing company groups
- Hub-level reporting and analytics aggregation
