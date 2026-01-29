# iliOS Telemetry Hookup Workflow Audit

**Document Version:** 1.0  
**Audit Date:** January 29, 2026  
**Audit Type:** Read-Only Code & Architecture Review  
**Scope:** DAS (Data Acquisition System) connection workflow, site/device mapping, telemetry data pipeline

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Supported DAS Providers](#supported-das-providers)
3. [Data Model](#data-model)
4. [UI Workflow](#ui-workflow)
5. [Backend API Flow](#backend-api-flow)
6. [Data Pipeline Architecture](#data-pipeline-architecture)
7. [Security Considerations](#security-considerations)
8. [Identified Issues (Ranked)](#identified-issues-ranked)
9. [Proposed Target UX Workflow](#proposed-target-ux-workflow)

---

## Executive Summary

The iliOS telemetry hookup workflow enables real estate asset managers to connect solar/energy sites to external Data Acquisition Systems (DAS) for automated performance monitoring. The system currently supports two providers (KMC and Also Energy) and follows a three-tier architecture:

1. **PostgreSQL** - Stores connection metadata and mapping relationships
2. **GCP Firestore** - Stores pipeline configuration for Cloud Functions
3. **GCP BigQuery** - Stores time-series telemetry data (power, energy, irradiance)

The current implementation embeds telemetry mapping within the Site and Device creation/edit forms rather than providing a dedicated hookup wizard. This creates UX friction and limits visibility into sync health.

---

## Supported DAS Providers

| Provider | Auth Method | Credential Format | Status |
|----------|-------------|-------------------|--------|
| **KMC** | API Token | Token string stored in GCP Secrets Manager | Active |
| **Also Energy** | Username/Password | Base64-encoded `username:password` in GCP Secrets Manager | Active |

### Provider Enum Definition
**File:** `backend/ilios-server/app/models/telemetry.py`

```python
class DASProvidersEnum(enum.Enum):
    # Make sure enum name is same as in telemetry
    kmc = "KMC"
    also_energy = "Also Energy"
```

### Credential Formatting
**File:** `backend/ilios-server/app/helpers/telemetry/telemetry_helper.py`

```python
def format_das_credentials(provider, das_connection):
    """Depending on the provider, shape the token correctly:
    - KMC - return the <token> field as is
    - Also Energy - encode with base64 pair of username and password separated with colon (:)"""
    
    if provider == DASProvidersEnum.kmc and das_connection.token:
        credentials = das_connection.token
    elif provider == DASProvidersEnum.also_energy and das_connection.username and das_connection.password:
        token_bytes = f"{das_connection.username}:{das_connection.password}".encode("utf-8")
        credentials_bytes = base64.b64encode(token_bytes)
        credentials = credentials_bytes.decode("utf-8")
    return credentials
```

---

## Data Model

### PostgreSQL Tables

#### 1. `das_connections`
Company-scoped DAS provider connections with encrypted credential references.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | NO | Primary key |
| `company_id` | integer | NO | FK to companies |
| `name` | varchar | NO | User-defined connection name |
| `provider` | enum (DASProvidersEnum) | NO | "KMC" or "Also Energy" |
| `secret_token_name` | varchar | NO | GCP Secrets Manager secret ID |
| `created_at` | timestamp | YES | Creation timestamp |
| `updated_at` | timestamp | YES | Last update timestamp |

**File:** `backend/ilios-server/app/models/telemetry.py`

#### 2. `telemetry_sites_mapping`
Maps iliOS Sites to external DAS site identifiers.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | NO | Primary key |
| `site_id` | integer | YES | FK to sites (unique constraint) |
| `connection_id` | integer | YES | FK to das_connections |
| `telemetry_site_id` | varchar | NO | External site ID from DAS provider |
| `telemetry_site_name` | varchar | NO | External site name from DAS provider |
| `created_at` | timestamp | YES | Creation timestamp |
| `updated_at` | timestamp | YES | Last update timestamp |

**Constraint:** One site can have at most one telemetry mapping.

**File:** `backend/ilios-server/app/models/telemetry.py`

#### 3. `telemetry_devices_mapping`
Maps iliOS Devices to external DAS device identifiers.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | integer | NO | Primary key |
| `device_id` | integer | NO | FK to devices (unique constraint) |
| `telemetry_device_id` | varchar | NO | External device ID from DAS provider |
| `telemetry_device_name` | varchar | NO | External device name from DAS provider |
| `created_at` | timestamp | YES | Creation timestamp |
| `updated_at` | timestamp | YES | Last update timestamp |

**File:** `backend/ilios-server/app/models/telemetry.py`

### Firestore Document Structure

**Collection:** Company configurations  
**File:** `backend/ilios-server/app/firestore_models/firestore_company_config.py`

```
FSCompanyConfig {
  id: int (company_id)
  connections: FSConnection[] {
    id: int
    data_provider: string ("kmc" | "also_energy")
    token_secret_id: string (full GCP secret path)
  }
  sites: FSSite[] {
    id: int (iliOS site_id)
    external_id: string (DAS site ID)
    connection_id: int
    devices: FSDevice[] {
      id: int (iliOS device_id)
      external_id: string (DAS device ID)
    }
  }
}
```

### Entity Relationship Diagram (Textual)

```
┌─────────────────┐        ┌─────────────────────────┐
│    companies    │        │     das_connections     │
├─────────────────┤        ├─────────────────────────┤
│ id (PK)         │◄───────│ company_id (FK)         │
│ name            │        │ id (PK)                 │
│ ...             │        │ name                    │
└─────────────────┘        │ provider (enum)         │
                           │ secret_token_name       │
                           └───────────┬─────────────┘
                                       │
                                       │ 1:N
                                       ▼
┌─────────────────┐        ┌─────────────────────────┐
│      sites      │        │ telemetry_sites_mapping │
├─────────────────┤        ├─────────────────────────┤
│ id (PK)         │◄───────│ site_id (FK, UNIQUE)    │
│ company_id      │        │ connection_id (FK)      │
│ name            │        │ telemetry_site_id       │
│ ...             │        │ telemetry_site_name     │
└────────┬────────┘        └─────────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐        ┌───────────────────────────┐
│     devices     │        │ telemetry_devices_mapping │
├─────────────────┤        ├───────────────────────────┤
│ id (PK)         │◄───────│ device_id (FK, UNIQUE)    │
│ site_id (FK)    │        │ telemetry_device_id       │
│ name            │        │ telemetry_device_name     │
│ category        │        └───────────────────────────┘
└─────────────────┘

                    ┌───────────────────────────────┐
                    │    Firestore (GCP)            │
                    │  FSCompanyConfig              │
                    │  ├── connections[]            │
                    │  └── sites[]                  │
                    │      └── devices[]            │
                    └───────────────────────────────┘

                    ┌───────────────────────────────┐
                    │    BigQuery (GCP)             │
                    │  platform_{env} dataset       │
                    │  ├── site_power_actual_vs_expected()
                    │  ├── site_energy_actual_vs_expected_daily()
                    │  ├── device_power_actual_vs_expected()
                    │  ├── device_last_report_ts()  │
                    │  └── device_availability_metrics()
                    └───────────────────────────────┘
```

---

## UI Workflow

### Connection Management

**Location:** Settings Module → Connections  
**Access Control:** `SettingsPermissions` with `edit` or `view` action

| Step | Action | Frontend Component | API Call |
|------|--------|-------------------|----------|
| 1 | Navigate to Settings → Connections | (Not fully audited) | — |
| 2 | Add new connection | Connection form | `POST /api/contractors/{company_id}/connections/` |
| 3 | Enter credentials | Form fields (token or username/password) | — |
| 4 | Submit | — | Validates via Cloud Function |

### Site Mapping (Embedded in SiteForm)

**File:** `frontend/rea-investment-fe/src/components/forms/SiteForm/SiteForm.tsx`

| Step | Action | Component Logic | API Call |
|------|--------|-----------------|----------|
| 1 | Open Site create/edit form | `SiteForm` component | — |
| 2 | If no existing mapping, load connections | `useQuery(['connections', {companyId}])` | `GET /api/contractors/{company_id}/connections/` |
| 3 | Select DAS connection | Dropdown populated from query | — |
| 4 | Fetch available sites from DAS | `useQuery(['sites', {companyId, connectionId}])` | `GET /api/contractors/{company_id}/connections/{connection_id}/sites` |
| 5 | Select DAS site | Dropdown with external site names | — |
| 6 | Submit form | `saveMappingData` mutation | `POST /api/telemetry/sites/{site_id}/mapping` |

**Key Fields in Form:**
- `das_connection_name` - Display name of selected connection
- `telemetry_site_name` - Display name of mapped DAS site

### Device Mapping (Embedded in DeviceForm)

**File:** `frontend/rea-investment-fe/src/components/forms/DeviceForm/DeviceForm.tsx`

| Step | Action | Component Logic | API Call |
|------|--------|-----------------|----------|
| 1 | Open Device create form | `DeviceForm` component | — |
| 2 | Load available DAS devices for site | `useQuery(['telemetry-devices', {siteId}])` | `GET /api/telemetry/sites/{site_id}/devices` |
| 3 | Select DAS device (optional) | Dropdown with external device names | — |
| 4 | Submit form | `addDevice` mutation | `POST /api/am/sites/{site_id}/devices` (includes mapping) |
| 5 | Trigger data fetch | `updateDevices` mutation | `PUT /api/am/sites/{site_id}/devices/{device_id}/telemetry-details` |

**Telemetry-Eligible Device Categories:**
- `inverter`
- `module`
- `weather_station`

**File:** `backend/ilios-server/app/helpers/device_helper.py`

---

## Backend API Flow

### API Endpoints

#### Connection Management
**Router:** `backend/ilios-server/app/routers/settings/connections.py`

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/contractors/{company_id}/connections/` | Create new DAS connection | SettingsPermissions(edit) |
| `GET` | `/api/contractors/{company_id}/connections/` | List company connections | SettingsPermissions(view) |
| `GET` | `/api/contractors/{company_id}/connections/{connection_id}` | Get connection details | SettingsPermissions(view) |
| `PUT` | `/api/contractors/{company_id}/connections/{connection_id}` | Update connection | SettingsPermissions(edit) |
| `DELETE` | `/api/contractors/{company_id}/connections/{connection_id}` | Delete connection | SettingsPermissions(edit) |
| `GET` | `/api/contractors/{company_id}/connections/{connection_id}/sites` | List sites from DAS provider | SettingsPermissions(view) |
| `GET` | `/api/contractors/{company_id}/connections/{connection_id}/sites/{site_id}/devices` | List devices from DAS provider (via connections router) | SettingsPermissions(view) |

#### Site/Device Telemetry Mapping
**Router:** `backend/ilios-server/app/routers/telemetry/telemetry.py`

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/telemetry/sites/{site_id}/mapping` | Create site mapping | SettingsPermissions(edit) + company admin site access |
| `GET` | `/api/telemetry/sites/{site_id}/devices` | Fetch telemetry devices for a mapped site | AssetPermissions(view) + company admin site access |

**Note:** No DELETE endpoint exists for site mapping removal via API. Mapping deletion must be handled through database operations or the connection deletion cascade.

#### Device Telemetry Operations
**Router:** `backend/ilios-server/app/routers/assets_management/devices.py`

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `PUT` | `/api/am/sites/{site_id}/devices/{device_id}/telemetry-details` | Fetch and update device with DAS static info | AssetPermissions(edit) |

**Note:** Device mapping occurs during device creation via `POST /api/am/sites/{site_id}/devices` with `telemetry_device_id` and `telemetry_device_name` fields.

#### Operations & Maintenance (Telemetry Consumption)
**Router:** `backend/ilios-server/app/routers/operations_and_maintenance/sites.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/om/sites/{site_id}` | Get site with telemetry status |
| `GET` | `/api/om/sites/{site_id}/devices` | Get devices with last_reported timestamp |
| `GET` | `/api/om/sites/{site_id}/actual-production-chart` | Get site production chart data |

### Helper Modules

| Module | File Path | Purpose |
|--------|-----------|---------|
| Telemetry Helper | `backend/ilios-server/app/helpers/telemetry/telemetry_helper.py` | Core telemetry operations, mapping CRUD |
| Cloud Function Client | `backend/ilios-server/app/helpers/telemetry/telemetry_cloud_function_client.py` | HTTP client for GCP Cloud Functions |
| Firestore Client | `backend/ilios-server/app/helpers/telemetry/firestore_client.py` | Firestore document operations |
| Secrets Manager | `backend/ilios-server/app/helpers/telemetry/secrets_manager.py` | GCP Secrets Manager operations |
| BigQuery Site | `backend/ilios-server/app/helpers/telemetry/bigquery/site.py` | Site-level telemetry queries |
| BigQuery Device | `backend/ilios-server/app/helpers/telemetry/bigquery/device.py` | Device-level telemetry queries |
| BigQuery Base | `backend/ilios-server/app/helpers/telemetry/bigquery/base.py` | Base class with caching, query execution |

### Cloud Function URLs (from settings.py)

| Setting | Purpose |
|---------|---------|
| `telemetry_token_function_url` | Validate DAS credentials |
| `telemetry_sites_function_url` | Fetch sites list from DAS provider |
| `telemetry_devices_function_url` | Fetch devices list from DAS provider |
| `telemetry_device_static_info_func_url` | Fetch device static info from DAS |

### Data Sync Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONNECTION CREATION                                │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Frontend   │────▶│   Backend API    │────▶│ Cloud Function      │
│  (Form)     │     │  (connections.py)│     │ (token validation)  │
└─────────────┘     └──────────────────┘     └─────────────────────┘
                           │                          │
                           │ On success:              │ Validates with
                           ▼                          │ DAS provider
                    ┌──────────────────┐              │
                    │  GCP Secrets     │◀─────────────┘
                    │  Manager         │
                    │ (store creds)    │
                    └──────────────────┘
                           │
                           ▼
                    ┌──────────────────┐
                    │   PostgreSQL     │
                    │ (das_connections)│
                    └──────────────────┘
                           │
                           ▼
                    ┌──────────────────┐
                    │    Firestore     │
                    │ (FSCompanyConfig)│
                    └──────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            SITE MAPPING                                      │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  SiteForm   │────▶│  GET /sites      │────▶│ Cloud Function      │
│  (Select    │     │  (from DAS)      │     │ (fetch DAS sites)   │
│   DAS site) │     └──────────────────┘     └─────────────────────┘
└─────────────┘              │
     │                       │ Returns site list
     │                       ▼
     │              ┌──────────────────┐
     │              │  User selects    │
     │              │  DAS site        │
     │              └──────────────────┘
     │                       │
     ▼                       ▼
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Submit     │────▶│ POST /mapping    │────▶│   PostgreSQL        │
│             │     │                  │     │ (telemetry_sites_   │
│             │     │                  │     │  mapping)           │
└─────────────┘     └──────────────────┘     └─────────────────────┘
                           │
                           ▼
                    ┌──────────────────┐
                    │    Firestore     │
                    │ (add to sites[]) │
                    └──────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                     TELEMETRY DATA CONSUMPTION                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  O&M Dashboard  │────▶│  BigQuery        │────▶│  GCP Cloud          │
│  (Frontend)     │     │  (via Backend)   │     │  Functions          │
└─────────────────┘     └──────────────────┘     │  (scheduled sync)   │
                               │                 └─────────────────────┘
                               │                          │
                               ▼                          │ Periodic polling
                        ┌──────────────┐                  │ from DAS providers
                        │ Redis Cache  │                  │
                        │ (15-min TTL) │                  ▼
                        └──────────────┘           ┌──────────────┐
                                                   │ DAS Provider │
                                                   │ APIs         │
                                                   │ (KMC/Also)   │
                                                   └──────────────┘
```

---

## Data Pipeline Architecture

### Integration Mode

**Type:** API Polling via GCP Cloud Functions (serverless)

The iliOS backend does NOT directly communicate with DAS provider APIs. Instead:

1. **Credentials** are stored in GCP Secrets Manager
2. **Cloud Functions** run on a schedule to poll DAS providers
3. **Firestore** stores mapping configuration that Cloud Functions read
4. **BigQuery** stores the resulting time-series data
5. **Backend** queries BigQuery for display (with Redis caching)

### BigQuery Functions

**Dataset:** `platform_{environment}` (e.g., `platform_dev`, `platform_prod`)

| Function | Parameters | Returns |
|----------|------------|---------|
| `site_power_actual_vs_expected` | interval_start, interval_end, timezone | site_id, site_power_actual[], site_power_expected[] |
| `site_energy_actual_vs_expected_daily` | interval_start, interval_end, timezone | site_id, site_energy_actual[], site_energy_expected[] |
| `site_power_actual_vs_expected_and_irradiance` | interval_start, interval_end, timezone | site_id, power + irradiance arrays |
| `device_power_actual_vs_expected` | interval_start, interval_end, timezone | device_id, device_power_actual[], device_power_expected[] |
| `device_last_report_ts` | interval_start, interval_end, timezone | device_id, device_last_report_ts |
| `device_availability_metrics` | interval_start, interval_end, timezone | device_id, availability metrics |

### Caching Strategy

**File:** `backend/ilios-server/app/helpers/telemetry/bigquery/base.py`

- **Cache Backend:** Redis (via `app.redis_cache.cache`)
- **Default TTL:** 15 minutes (aligned with data granularity)
- **Cache Key Pattern:** `{metric}-{object_type}-{ids}-{interval_start}-{interval_end}`
- **Serialization:** Python pickle

---

## Security Considerations

### Credential Storage

| Aspect | Implementation | Assessment |
|--------|----------------|------------|
| Storage Location | GCP Secrets Manager | ✅ Secure |
| Access Method | Service account with key file | ⚠️ Key file on disk |
| Secret ID Format | `projects/{project_id}/secrets/{id}/versions/latest` | ✅ Versioned |
| Credential Validation | Via Cloud Function before storage | ✅ Validated |

**File:** `backend/ilios-server/app/helpers/telemetry/secrets_manager.py`

### Role-Based Access Control (RBAC)

| Module | Permission Class | Actions Used |
|--------|-----------------|--------------|
| Settings (Connections) | `SettingsPermissions` | view, edit |
| Asset Management (Devices) | `AssetPermissions` | view, edit |
| Operations & Maintenance | `OnMPermissions` | view |
| Telemetry Mapping | `SettingsPermissions` + company admin | edit |

**Files:**
- `backend/ilios-server/app/helpers/authorization/module_based/settings.py`
- `backend/ilios-server/app/helpers/authorization/module_based/asset_management.py`
- `backend/ilios-server/app/helpers/authorization/module_based/operation_monitoring.py`

### Audit Trail

| Event | Logged | Location |
|-------|--------|----------|
| Connection creation | ✅ (AuditingMiddleware) | Audit log |
| Credential validation | ✅ (Logger) | Application logs |
| Mapping creation | ✅ (AuditingMiddleware) | Audit log |
| BigQuery queries | ✅ (Logger) | Application logs |
| Sync failures | ❓ Unknown | Cloud Function logs (external) |

**Gap:** No visibility into Cloud Function sync status or failures from within iliOS application.

---

## Identified Issues (Ranked)

### Critical Priority

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| **C1** | **No connection test feedback** - Users cannot verify credentials work before saving | User confusion, wasted time on broken connections | `connections.py` - no pre-save test endpoint |
| **C2** | **No sync health visibility** - No way to see if data is flowing or when last sync occurred | Operators cannot diagnose data gaps | Missing from UI entirely |
| **C3** | **Device mapping during creation only** - Cannot map existing devices to telemetry | Requires device recreation for telemetry hookup | `DeviceForm.tsx` - only in "add" mode |

### High Priority

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| **H1** | **No dedicated hookup wizard** - Mapping embedded in Site/Device forms | Poor discoverability, fragmented UX | `SiteForm.tsx`, `DeviceForm.tsx` |
| **H2** | **No bulk device mapping** - Must map devices one by one | Time-consuming for large sites | `DeviceForm.tsx` |
| **H3** | **No lifecycle state validation** - Can map telemetry regardless of site status | Potential data quality issues for non-operational sites | No validation in `telemetry.py` |
| **H4** | **Complex multi-system architecture** - PostgreSQL + Firestore + BigQuery + Secrets | Debugging difficulty, operational overhead | System-wide |

### Medium Priority

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| **M1** | **No site mapping removal API** - No DELETE endpoint for site mapping | Cannot clean up stale mappings (only via connection delete cascade) | `telemetry.py` router missing endpoint |
| **M2** | **No connection editing for credentials** - Can update name but unclear on credential update flow | Security concern if credentials rotate | `connections.py` PUT endpoint |
| **M3** | **Cache invalidation on mapping change** - Redis cache may serve stale data | Brief data inconsistency after mapping changes | `bigquery/base.py` |
| **M4** | **No provider-specific error messages** - Generic "unavailable" message | Hard to diagnose specific provider issues | `TelemetryMessages` enum |

### Low Priority

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| **L1** | **Hardcoded timezone offset** - Some methods default to UTC-6 | May not work for sites in other timezones | `bigquery/site.py` |
| **L2** | **Missing index on telemetry_site_id** - Query performance for lookups | Slow queries at scale | `telemetry.py` model |
| **L3** | **No connection name uniqueness hint** - Error only on submit | Minor UX friction | `SiteForm.tsx` |

---

## Proposed Target UX Workflow

### Design Principles

1. **Dedicated Hookup Wizard** - Separate from Site/Device creation
2. **Progressive Disclosure** - Guide users through connection → site → devices
3. **Real-time Feedback** - Test connections before saving
4. **Sync Health Dashboard** - Visibility into data pipeline status
5. **Bulk Operations** - Map multiple devices at once

### Proposed User Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TELEMETRY HOOKUP WIZARD                              │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: Connection Setup
┌─────────────────────────────────────────────────────────────────────────────┐
│  [Select DAS Provider]  ▼ KMC / Also Energy                                 │
│                                                                              │
│  [Connection Name]     ____________________                                  │
│                                                                              │
│  --- KMC ---                            --- Also Energy ---                  │
│  [API Token]  ____________________      [Username]  __________________       │
│                                         [Password]  __________________       │
│                                                                              │
│  [🔍 Test Connection]                                                        │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ✅ Connection successful! Found 12 sites available.                  │   │
│  │    Last sync: 5 minutes ago                                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  [Cancel]                                                  [Save & Continue] │
└─────────────────────────────────────────────────────────────────────────────┘

Step 2: Site Mapping
┌─────────────────────────────────────────────────────────────────────────────┐
│  Map iliOS Projects to DAS Sites                                             │
│                                                                              │
│  ┌────────────────────────────────┬──────────────────────────────────────┐  │
│  │ iliOS Project                  │ DAS Site                              │  │
│  ├────────────────────────────────┼──────────────────────────────────────┤  │
│  │ 🏢 Sunnydale Solar Farm       │ [Select DAS Site ▼]                   │  │
│  │    Status: Placed in Service   │  ○ SUNNYDALE-001                     │  │
│  │                                │  ○ SUNNYDALE-002                     │  │
│  │                                │  ● Not Mapped                         │  │
│  ├────────────────────────────────┼──────────────────────────────────────┤  │
│  │ 🏢 Desert View Array          │ [DESERT-MAIN ✓]                       │  │
│  │    Status: Placed in Service   │  Last data: 2 min ago                │  │
│  ├────────────────────────────────┼──────────────────────────────────────┤  │
│  │ 🏗️ New Construction Site      │ [Disabled - Not Operational]          │  │
│  │    Status: Construction        │                                       │  │
│  └────────────────────────────────┴──────────────────────────────────────┘  │
│                                                                              │
│  [Back]                                                    [Save & Continue] │
└─────────────────────────────────────────────────────────────────────────────┘

Step 3: Device Mapping (per site)
┌─────────────────────────────────────────────────────────────────────────────┐
│  Map Devices for: Sunnydale Solar Farm                                       │
│                                                                              │
│  [☑ Auto-match by name]  [☐ Show mapped only]                               │
│                                                                              │
│  ┌────────────────────────────────┬──────────────────────────────────────┐  │
│  │ iliOS Device                   │ DAS Device                            │  │
│  ├────────────────────────────────┼──────────────────────────────────────┤  │
│  │ ☑ Inverter 1 (Inverter)       │ [INV-001 ▼]                           │  │
│  │ ☑ Inverter 2 (Inverter)       │ [INV-002 ▼]                           │  │
│  │ ☑ Weather Station (Weather)   │ [WS-MAIN ▼]                           │  │
│  │ ☐ Transformer (N/A)           │ [Not telemetry-enabled]               │  │
│  └────────────────────────────────┴──────────────────────────────────────┘  │
│                                                                              │
│  [Map All Selected]                                                          │
│                                                                              │
│  [Back]                                                    [Finish Setup]    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         SYNC HEALTH DASHBOARD                                │
└─────────────────────────────────────────────────────────────────────────────┘

Settings → Telemetry → Health
┌─────────────────────────────────────────────────────────────────────────────┐
│  Telemetry Sync Status                                                       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ KMC Production Connection                                             │   │
│  │ ✅ Healthy | Last sync: 3 min ago | Next sync: 12 min                │   │
│  │ Sites: 8 mapped | Devices: 42 mapped                                  │   │
│  │ [View Details] [Edit] [Resync Now]                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ AlsoEnergy Backup                                                     │   │
│  │ ⚠️ Warning | Last sync: 2 hours ago | Error: Rate limited            │   │
│  │ Sites: 2 mapped | Devices: 8 mapped                                   │   │
│  │ [View Details] [Edit] [Retry Now]                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  [+ Add New Connection]                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Implementation Recommendations

1. **New Route:** `/settings/telemetry` - Dedicated telemetry management area
2. **New Components:**
   - `TelemetryWizard` - Multi-step connection + mapping wizard
   - `SyncHealthDashboard` - Connection status overview
   - `BulkDeviceMapper` - Grid-based device mapping interface
3. **New API Endpoints:**
   - `POST /api/connections/{id}/test` - Test connection without saving
   - `GET /api/connections/{id}/health` - Get sync status and last sync time
   - `POST /api/sites/{id}/devices/bulk-mapping` - Map multiple devices at once
4. **Backend Enhancements:**
   - Add `last_sync_at` and `sync_status` columns to `das_connections`
   - Expose Cloud Function sync status via internal callback endpoint
   - Add lifecycle state validation before allowing telemetry mapping

---

## Appendix: File Reference

### Backend Files

| Category | File Path |
|----------|-----------|
| **Models** | `backend/ilios-server/app/models/telemetry.py` |
| **Schemas** | `backend/ilios-server/app/schema/telemetry.py` |
| **CRUD** | `backend/ilios-server/app/crud/das_connection.py` |
| **Router - Connections** | `backend/ilios-server/app/routers/settings/connections.py` |
| **Router - Telemetry** | `backend/ilios-server/app/routers/telemetry/telemetry.py` |
| **Router - O&M** | `backend/ilios-server/app/routers/operations_and_maintenance/sites.py` |
| **Helper - Telemetry** | `backend/ilios-server/app/helpers/telemetry/telemetry_helper.py` |
| **Helper - Cloud Functions** | `backend/ilios-server/app/helpers/telemetry/telemetry_cloud_function_client.py` |
| **Helper - Firestore** | `backend/ilios-server/app/helpers/telemetry/firestore_client.py` |
| **Helper - Secrets** | `backend/ilios-server/app/helpers/telemetry/secrets_manager.py` |
| **Helper - BigQuery Base** | `backend/ilios-server/app/helpers/telemetry/bigquery/base.py` |
| **Helper - BigQuery Site** | `backend/ilios-server/app/helpers/telemetry/bigquery/site.py` |
| **Helper - BigQuery Device** | `backend/ilios-server/app/helpers/telemetry/bigquery/device.py` |
| **Firestore Models** | `backend/ilios-server/app/firestore_models/firestore_company_config.py` |
| **Settings** | `backend/ilios-server/app/settings.py` |
| **Messages** | `backend/ilios-server/app/static/messages.py` |
| **Authorization** | `backend/ilios-server/app/helpers/authorization/module_based/settings.py` |
| **BigQuery Engine** | `backend/ilios-server/app/bigquery/bigquery.py` |

### Frontend Files

| Category | File Path |
|----------|-----------|
| **Site Form** | `frontend/rea-investment-fe/src/components/forms/SiteForm/SiteForm.tsx` |
| **Device Form** | `frontend/rea-investment-fe/src/components/forms/DeviceForm/DeviceForm.tsx` |
| **Connections API** | `frontend/rea-investment-fe/src/api/connections.ts` |
| **Asset Mgmt API** | `frontend/rea-investment-fe/src/api/asset-management.ts` |
| **Device Overview** | `frontend/rea-investment-fe/src/modules/asset-management/pages/DeviceDetails/tabs/Overview/Overview.tsx` |

---

*End of Audit Document*
