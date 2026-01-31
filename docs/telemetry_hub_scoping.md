# Telemetry Hub Scoping

## Overview

This document describes the dual-ownership DAS (Data Acquisition System) connection model and how telemetry connections are scoped within portfolio hub boundaries.

## Portfolio Hub Boundaries

All telemetry connections, sharing, discovery, and UI visibility are constrained to `portfolio_hub_id` boundaries:

- **Hub Company**: A company with `portfolio_hub_id = NULL` acts as a hub
- **Hub Members**: Companies with `portfolio_hub_id` set belong to that hub
- **Isolation**: No cross-hub connection leakage is permitted

## Dual-Ownership Model

DAS connections support two ownership types:

### Company-Owned Connections (`owner_type = 'company'`)
- Traditional behavior - connection belongs to a single company
- `company_id` identifies the owning company
- `owner_company_id` is NULL
- Only visible to the owning company

### Portfolio-Shared Connections (`owner_type = 'portfolio'`)
- Connection shared across all companies in a portfolio hub
- `company_id` identifies the creating company
- `owner_company_id` stores the hub company ID
- Visible to all companies within the same hub

## Database Schema

```sql
-- das_connections table additions
owner_type VARCHAR(20) DEFAULT 'company' CHECK (owner_type IN ('company', 'portfolio'))
owner_company_id INTEGER REFERENCES companies(id)  -- Hub ID for portfolio connections
last_test_at TIMESTAMP  -- When credentials were last validated
last_test_status VARCHAR(20)  -- 'SUCCESS' or 'FAILURE'
last_test_message TEXT  -- Error details on failure
```

## API Endpoints

### Available Connections
`GET /api/telemetry/connections/available` - Global connection discovery
`GET /api/telemetry/sites/{site_id}/available-connections` - Site-specific connections

**Response Structure:**
```json
{
  "company_connections": [
    {
      "id": 1,
      "name": "Local DAS",
      "provider": "KMC",
      "owner_type": "company",
      "owned_by_current_company": true,
      "owner_company_name": null,
      "last_test_at": "2025-01-30T12:00:00Z",
      "last_test_status": "SUCCESS",
      "last_test_message": null
    }
  ],
  "portfolio_connections": [
    {
      "id": 2,
      "name": "Shared DAS",
      "provider": "Also Energy",
      "owner_type": "portfolio",
      "owned_by_current_company": false,
      "owner_company_name": "Parent Corp",
      "last_test_at": "2025-01-30T11:00:00Z",
      "last_test_status": "SUCCESS",
      "last_test_message": null
    }
  ]
}
```

### Creating Portfolio-Shared Connections
`POST /api/companies/{company_id}/settings/connections`

**Request:**
```json
{
  "name": "Shared Solar DAS",
  "provider": "kmc",
  "token": "secret-token",
  "share_with_portfolio": true
}
```

When `share_with_portfolio: true`:
1. System resolves the company's portfolio hub
2. Sets `owner_type = 'portfolio'`
3. Sets `owner_company_id = hub_company_id`
4. Connection becomes discoverable by all hub members

## Hub Resolution Logic

```python
def resolve_company_hub_id(company_id: int) -> Optional[int]:
    """
    Returns the hub company ID for a given company.
    - If company IS a hub (portfolio_hub_id is NULL), returns company_id
    - If company BELONGS to a hub, returns portfolio_hub_id
    """
```

## Access Control

### Viewing Connections
- Users see company-owned connections for their authorized companies
- Users see portfolio-shared connections from their hub (if company belongs to a hub)
- No cross-hub visibility

### Creating/Modifying Connections
- Requires edit permissions on the company
- Portfolio sharing requires company to be part of a hub
- Test status is automatically updated on credential validation

## Audit Trail

All connection operations are logged to the audit system:

| Action | Description |
|--------|-------------|
| `connection_created` | New DAS connection created |
| `connection_updated` | Connection name or credentials updated |
| `connection_deleted` | Connection removed |

Audit entries include:
- `source`: "telemetry_connections"
- `details`: Connection name, ID, and operation specifics

## Health Status States

The `TelemetryHealthStatus` enum supports:

| Status | Description |
|--------|-------------|
| `HEALTHY` | Data flowing, last report ≤30 minutes |
| `WARN` | Data stale, last report 30-120 minutes |
| `ERROR` | No data for >120 minutes |
| `NO_DATA` | No data available in system |
| `NO_DATA_YET` | Mapping complete, awaiting first data |
| `NOT_CONFIGURED` | Telemetry not set up |
| `MAPPED_NO_DEVICES` | Site mapped but no devices mapped |

## Implementation Notes

1. **SQLAlchemy Relationships**: The `Company.das_connections` relationship must specify `foreign_keys="DASConnection.company_id"` to avoid ambiguity with `owner_company_id`

2. **Firestore Sync**: Connection credentials are stored in GCP Secrets Manager; connection configs sync to Firestore for the telemetry pipeline

3. **Credential Validation**: On create/update, credentials are validated via the telemetry Cloud Function. Results are stored in `last_test_*` columns.
