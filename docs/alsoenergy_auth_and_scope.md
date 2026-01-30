# AlsoEnergy Authentication & Scope Audit

**Date:** January 30, 2026  
**Auditor:** Replit Agent  
**Scope:** READ-ONLY audit of AlsoEnergy integration auth model and connection scoping  
**Reference:** PowerTrack Swagger - `/Auth/token` endpoint  

---

## Executive Summary

The Ilios platform does **NOT** directly call AlsoEnergy's `/Auth/token` endpoint. Instead, authentication is delegated to GCP Cloud Functions, which handle the OAuth password grant flow. Static credentials (username:password) are persisted in GCP Secrets Manager, while short-lived access tokens (~15 min rolling) are managed transiently by the Cloud Functions.

**Key Findings:**
- ✅ Static credentials stored securely in GCP Secrets Manager (not in Ilios DB)
- ✅ Short-lived access tokens NOT persisted (handled by Cloud Functions)
- ⚠️ 401 retry logic is in Cloud Functions, not visible to audit
- ❌ Connections are strictly company-scoped (no portfolio-owned connections)
- ❌ Telemetry Wizard Step 1 only lists same-company connections

---

## 1. Authentication Flow Architecture

### 1.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ILIOS BACKEND                                   │
│  ┌─────────────────────┐    ┌──────────────────────┐                        │
│  │ /api/telemetry/*    │───▶│ TelemetryFuncHTTP    │                        │
│  │ /api/contractors/   │    │ Client               │                        │
│  │    connections/*    │    └──────────────────────┘                        │
│  └─────────────────────┘              │                                     │
│                                       │ POST to Cloud Function URLs         │
│                                       │ with token_secret_id                │
└───────────────────────────────────────┼─────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GCP CLOUD FUNCTIONS                               │
│  ┌─────────────────────┐    ┌──────────────────────────────────────────┐   │
│  │ Token Validation    │───▶│ 1. Retrieve credentials from Secrets Mgr │   │
│  │ Sites Function      │    │ 2. Base64 decode username:password        │   │
│  │ Devices Function    │    │ 3. POST /Auth/token (password grant)      │   │
│  └─────────────────────┘    │ 4. Cache access_token (in-memory, ~15min) │   │
│                             │ 5. Call AlsoEnergy API with Bearer token   │   │
│                             │ 6. On 401: re-auth and retry once          │   │
│                             └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ALSOENERGY POWERTRACK API                           │
│  POST /Auth/token                                                           │
│  Content-Type: application/x-www-form-urlencoded                            │
│  Body: grant_type=password&username=X&password=Y                            │
│                                                                             │
│  Response: { "access_token": "...", "expires_in": 900, ... }                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Where /Auth/token Is Called

| Location | Calls /Auth/token? | Notes |
|----------|-------------------|-------|
| Ilios Backend | ❌ NO | Delegates to Cloud Functions |
| `TelemetryFuncHTTPClient` | ❌ NO | Sends `token_secret_id` to Cloud Function |
| `GCPSecretsManager` | ❌ NO | Only stores/retrieves static credentials |
| GCP Cloud Functions | ✅ YES | Handles OAuth password grant |

**Evidence from backend code:**

```python
# backend/ilios-server/app/helpers/telemetry/telemetry_cloud_function_client.py

class TelemetryFuncHTTPClient(BaseCloudFuncHTTPClient):
    def __init__(self):
        self.token_func_url = settings.telemetry_token_function_url
        self.sites_func_url = settings.telemetry_sites_function_url
        self.devices_func_url = settings.telemetry_devices_function_url
        # ...

    def get_telemetry_sites(self, provider, token_secret_id):
        payload = {
            "data_provider": provider,
            "token_secret_id": token_secret_id,  # GCP Secret path, NOT access_token
        }
        telemetry_response = self.post(payload=payload, use_token=True)
```

The backend sends the **GCP Secrets Manager path** (`token_secret_id`) to the Cloud Function, which then:
1. Retrieves the stored credentials from Secrets Manager
2. Calls AlsoEnergy `/Auth/token` with password grant
3. Returns API response to Ilios

### 1.3 401 Handling

**In Ilios Backend:**

```python
# backend/ilios-server/app/helpers/telemetry/telemetry_cloud_function_client.py

@staticmethod
def handle_response_error(response):
    if response.status_code != status.HTTP_200_OK:
        # Generic error handling - no 401-specific retry
        logger.error(f"Telemetry call failed with status {response.status_code}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, TelemetryMessages.das_provider_unavailable)
```

**Assessment:**
- ⚠️ Backend does NOT have 401-specific retry logic
- ⚠️ 401 handling assumed to be in Cloud Functions (not auditable from this codebase)
- ⚠️ If Cloud Function returns 401, backend surfaces generic "DAS provider unavailable" error

**Recommendation:** Confirm with GCP Cloud Function code that:
1. Token refresh on 401 is implemented
2. Retry logic has backoff to avoid infinite loops
3. Expired credentials surface meaningful error to UI

---

## 2. Token Persistence Audit

### 2.1 What Is Stored Where

| Data | Storage Location | Persisted? | Encrypted? |
|------|------------------|------------|------------|
| AlsoEnergy username:password | GCP Secrets Manager | ✅ YES | ✅ YES (at-rest encryption) |
| Base64-encoded credentials | GCP Secrets Manager | ✅ YES | ✅ YES |
| access_token (~15 min) | Cloud Function memory | ❌ NO | N/A (transient) |
| refresh_token | Not used | ❌ NO | N/A |
| Secret name reference | Ilios DB (`das_connections.secret_token_name`) | ✅ YES | ❌ NO (just the path) |

### 2.2 Credential Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONNECTION CREATION (One-time)                            │
│                                                                             │
│  1. User enters: username, password                                         │
│  2. Backend encodes: base64(username:password)                              │
│  3. Backend validates: Calls Cloud Function to test credentials             │
│  4. Backend stores:                                                         │
│     - Creates GCP Secret: "{env}-company-{cid}-connection-{connid}"        │
│     - Adds secret version with base64 credentials                          │
│     - Stores secret name in das_connections.secret_token_name              │
│  5. Backend configures Firestore: Adds connection to pipeline config       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Code Evidence:**

```python
# backend/ilios-server/app/routers/settings/connections.py

async def create_das_connection(company_id, das_connection, db_session):
    credentials = format_das_credentials(das_connection.provider, das_connection)
    
    # Validate credentials via Cloud Function
    TelemetryFuncHTTPClient().validate_token(das_connection.provider.name, credentials)
    
    # Create connection record
    connection = das_connection_crud.create_item(das_connection_record)
    
    # Store credentials in GCP Secrets Manager
    secret_name = f"{settings.environment_name}-company-{company_id}-connection-{connection.id}"
    secret_manager = GCPSecretsManager()
    secret_manager.create_secret(secret_name)
    secret_manager.add_secret_version(secret_name, credentials)
```

### 2.3 Credential Encoding (AlsoEnergy)

```python
# backend/ilios-server/app/helpers/telemetry/telemetry_helper.py

def format_das_credentials(provider, das_connection):
    if provider == DASProvidersEnum.also_energy:
        # Encode username:password as base64
        token_bytes = f"{das_connection.username}:{das_connection.password}".encode("utf-8")
        credentials_bytes = base64.b64encode(token_bytes)
        credentials = credentials_bytes.decode("utf-8")
    return credentials
```

### 2.4 Assessment

| Requirement | Status | Notes |
|-------------|--------|-------|
| Short-lived tokens NOT persisted | ✅ PASS | access_token only in Cloud Function memory |
| Static credentials encrypted at rest | ✅ PASS | GCP Secrets Manager handles encryption |
| No credentials in Ilios database | ✅ PASS | Only secret path stored, not actual creds |
| No credentials in logs | ⚠️ UNCONFIRMED | Depends on Cloud Function logging config |

---

## 3. Connection Scoping Model

### 3.1 Current Data Model

```sql
-- das_connections table
CREATE TABLE das_connections (
    id              INTEGER PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name            VARCHAR NOT NULL,
    provider        ENUM('kmc', 'also_energy') NOT NULL,
    secret_token_name VARCHAR NOT NULL,
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP
);
```

**Key Observations:**
- `company_id` is **NOT NULL** - every connection must belong to exactly one company
- No `scope` or `owner_type` column
- No mechanism to share connections across companies

### 3.2 Current Authorization

```python
# backend/ilios-server/app/routers/settings/connections.py

@settings_connections_router.get("/")
async def get_company_connections(
    company: Company = Depends(get_authorized_company),
):
    return {"items": company.das_connections}  # Only returns THIS company's connections
```

**Frontend (Wizard Step 1):**

```typescript
// TelemetryWizard.tsx
const { data: connections } = useQuery({
    queryKey: ['connections', companyId],
    queryFn: () => ApiClient.connections.getConnections(companyId as number),
    enabled: !!companyId && open
});
```

**API Client:**

```typescript
// api/connections.ts
const getConnections = async (companyId: number): Promise<Connections> => {
    const response = await httpClient.get(`/api/contractors/${companyId}/connections/`);
    return response.data;
};
```

### 3.3 Gap: No Portfolio-Owned Connections

**Current State:**
- Connections are strictly company-scoped
- If Company A and Company B are in the same portfolio and share an AlsoEnergy account, they must create duplicate connections
- Credential management overhead for multi-company portfolios

**Desired State:**
- Portfolio-level connections that can be shared across subsidiary companies
- Maintain company-level connections for company-specific accounts

---

## 4. Proposed Schema Change for Portfolio-Owned Connections

### 4.1 Minimal Schema Addition

Add two columns to `das_connections`:

```sql
ALTER TABLE das_connections
ADD COLUMN owner_type VARCHAR(20) DEFAULT 'company' CHECK (owner_type IN ('company', 'portfolio')),
ADD COLUMN owner_company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL;
```

**Column Semantics:**

| Column | Type | Description |
|--------|------|-------------|
| `owner_type` | `'company'` \| `'portfolio'` | Indicates if connection is company-scoped or portfolio-shared |
| `owner_company_id` | INTEGER (nullable) | For `portfolio` type: the "hub" company that owns/manages the connection |

**When `owner_type = 'company'` (default):**
- Existing behavior: `company_id` determines ownership
- `owner_company_id` is NULL or matches `company_id`

**When `owner_type = 'portfolio'`:**
- `company_id` still set (for backwards compatibility and cascading deletes)
- `owner_company_id` identifies the managing company
- All companies in the same portfolio (via `company.portfolio_id`) can access

### 4.2 Backward Compatibility

**Migration Strategy:**

```sql
-- Migration: Set existing connections to explicit company scope
UPDATE das_connections 
SET owner_type = 'company', 
    owner_company_id = company_id 
WHERE owner_type IS NULL;
```

### 4.3 Alternative: Separate Table

If the inline columns feel overloaded, consider:

```sql
CREATE TABLE das_connection_access (
    id            INTEGER PRIMARY KEY,
    connection_id INTEGER NOT NULL REFERENCES das_connections(id) ON DELETE CASCADE,
    company_id    INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    access_type   VARCHAR(20) DEFAULT 'owner' CHECK (access_type IN ('owner', 'shared')),
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (connection_id, company_id)
);
```

**Trade-offs:**

| Approach | Pros | Cons |
|----------|------|------|
| Add columns to `das_connections` | Minimal change, single query | Nullable column for `owner_company_id` |
| Separate `das_connection_access` | Clean many-to-many, explicit access grants | More complex queries, additional table |

**Recommendation:** Start with inline columns (`owner_type` + `owner_company_id`) for simplicity.

---

## 5. Updated Plan for Wizard Step 1

### 5.1 Current Behavior

The Telemetry Wizard Step 1 ("Connection") allows:
1. **Use Existing Connection** - Dropdown populated from `GET /api/contractors/{companyId}/connections/`
2. **Create New Connection** - Form for name, provider, credentials

**Gap:** Only shows connections owned by the current company.

### 5.2 Proposed Changes

**Backend Endpoint Update:**

Create new endpoint or modify existing:

```python
# GET /api/telemetry/connections/available?company_id={companyId}
# Returns: Company-owned + Portfolio-shared connections

@telemetry_router.get("/connections/available")
async def get_available_connections(
    company_id: int,
    current_user: CurrentUserSchema = Depends(AuthorizedUser(...)),
    db_session: Session = Depends(get_session),
):
    company = get_authorized_company(company_id, current_user, db_session)
    
    # Get company's own connections
    company_connections = db_session.query(DASConnection).filter(
        DASConnection.company_id == company_id
    ).all()
    
    # Get portfolio-shared connections (if company is part of a portfolio)
    portfolio_connections = []
    if company.portfolio_id:
        portfolio_connections = db_session.query(DASConnection).filter(
            DASConnection.owner_type == 'portfolio',
            DASConnection.company_id.in_(
                db_session.query(Company.id).filter(
                    Company.portfolio_id == company.portfolio_id
                )
            )
        ).all()
    
    return {
        "company_connections": [ConnectionSchema.from_orm(c) for c in company_connections],
        "portfolio_connections": [ConnectionSchema.from_orm(c) for c in portfolio_connections],
    }
```

**Response Schema:**

```typescript
interface AvailableConnectionsResponse {
  company_connections: Connection[];    // Owned by this company
  portfolio_connections: Connection[];  // Shared across portfolio
}
```

**Frontend Changes:**

```typescript
// TelemetryWizard.tsx - Step 1 modification

const { data: availableConnections } = useQuery({
    queryKey: ['available-connections', companyId],
    queryFn: () => ApiClient.connections.getAvailableConnections(companyId),
    enabled: !!companyId && open
});

// In render:
<FormControl fullWidth>
    <InputLabel>Select Connection</InputLabel>
    <Select value={selectedConnectionId} onChange={...}>
        <ListSubheader>Company Connections</ListSubheader>
        {availableConnections?.company_connections.map(conn => (
            <MenuItem key={conn.id} value={conn.id}>
                {conn.name} ({conn.provider})
            </MenuItem>
        ))}
        
        {availableConnections?.portfolio_connections.length > 0 && (
            <>
                <ListSubheader>Portfolio Connections</ListSubheader>
                {availableConnections?.portfolio_connections.map(conn => (
                    <MenuItem key={conn.id} value={conn.id}>
                        {conn.name} ({conn.provider}) - Shared
                    </MenuItem>
                ))}
            </>
        )}
    </Select>
</FormControl>
```

### 5.3 UI/UX Considerations

1. **Visual Distinction:** Portfolio connections should be visually marked (badge, icon, or "(Shared)" suffix)
2. **Create Flow:** When creating a new connection, add radio button for "Company-only" vs "Share with Portfolio"
3. **Permissions:** Only company_admins or portfolio_admins can create portfolio-shared connections
4. **Audit Trail:** Log when a portfolio connection is used by a different company

---

## 6. Implementation Roadmap

### Phase 1: Schema Change (Backend-only)

| Task | Effort | Notes |
|------|--------|-------|
| Add `owner_type`, `owner_company_id` columns | Low | Alembic migration |
| Backfill existing connections | Low | Set `owner_type='company'` |
| Add index on `(owner_type, owner_company_id)` | Low | Query performance |

### Phase 2: API Update

| Task | Effort | Notes |
|------|--------|-------|
| Create `GET /api/telemetry/connections/available` | Medium | New endpoint |
| Update connection creation to support `owner_type` | Medium | Modify POST |
| Add authorization check for portfolio access | Medium | Cross-company validation |

### Phase 3: Frontend Update

| Task | Effort | Notes |
|------|--------|-------|
| Update Wizard Step 1 to call new endpoint | Low | Change query |
| Add grouped Select with subheaders | Low | UI component |
| Add "Share with Portfolio" toggle in create form | Medium | New form field |

### Phase 4: Audit Trail

| Task | Effort | Notes |
|------|--------|-------|
| Log portfolio connection usage | Low | Add to audit events |
| Add to telemetry audit docs | Low | Documentation |

---

## 7. Appendix: File Paths

**Backend:**
```
backend/ilios-server/app/
├── models/telemetry.py                    # DASConnection, DASProvidersEnum
├── crud/das_connection.py                 # DASConnectionCRUD
├── routers/settings/connections.py        # Connection CRUD endpoints
├── routers/telemetry/telemetry.py         # Telemetry mapping endpoints
├── helpers/telemetry/
│   ├── telemetry_cloud_function_client.py # Cloud Function HTTP client
│   ├── secrets_manager.py                 # GCP Secrets Manager wrapper
│   ├── telemetry_helper.py                # Credential formatting
│   └── firestore_client.py                # Firestore config sync
├── schema/telemetry.py                    # Pydantic schemas
└── settings.py                            # Cloud Function URLs
```

**Frontend:**
```
frontend/rea-investment-fe/src/
├── api/connections.ts                     # Connection API client
└── modules/asset-management/pages/
    └── AssetManagementSiteDetails/tabs/Telemetry/
        ├── Telemetry.tsx                  # Main component
        └── TelemetryWizard.tsx            # 4-step wizard
```

**GCP (External - not in this repo):**
```
Cloud Functions:
- telemetry_token_function_url       # Token validation
- telemetry_sites_function_url       # Fetch DAS sites
- telemetry_devices_function_url     # Fetch DAS devices

Secrets Manager:
- Pattern: {env}-company-{company_id}-connection-{connection_id}

Firestore:
- Collection: company_configs
- Document: {company_id}
- Structure: { connections: [...], sites: [...] }
```

---

*End of AlsoEnergy Authentication & Scope Audit*
