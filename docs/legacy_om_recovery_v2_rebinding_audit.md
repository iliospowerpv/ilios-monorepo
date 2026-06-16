# Legacy O&M / Asset Management Drill-Down Recovery + V2 Rebinding Audit

**Version:** 1.0
**Type:** Read-only audit / recovery plan (NO code, routes, relinking, migrations, UI, or data-model changes performed)
**Scope:** Locate existing repository code matching prior-version O&M / Asset-Management drill-down screenshots, determine why it is or isn't reachable, and map a V2-native rebinding + recovery plan that reuses existing Ilios components and look-and-feel.
**Companion doc:** `docs/om_v2_alignment_audit.md` (prior sprint) — covers the V2 read-path precedence of the *currently-linked* O&M chart endpoints in depth. This audit extends that into the **drill-down / device-detail / asset-lifecycle** surfaces and the **dead/unlinked** legacy code.

---

## How to read this document

The 13 numbered return sections requested by the brief are below. Audit goals **A–J** are folded into them:

| Return section | Covers audit goal(s) |
|---|---|
| 1. Matched components by screenshot | A (match), partial E |
| 2. Frontend route/component inventory | A, C |
| 3. Backend/API inventory | B |
| 4. Active vs dead/unlinked findings | A, C |
| 5. Old data-model dependency findings | B |
| 6. V2 rebinding map | D |
| 7. Screen-by-screen recovery plan | E |
| 8. Look-and-feel preservation requirements | F |
| 9. Missing-dependency indicator plan | G |
| 10. Reuse classification | H |
| 11. Implementation phase plan | J |
| 12. Risks and non-goals | (constraints) |
| 13. Recommended next-sprint prompt | (handoff) |
| Appendix I. Testing plan | I |

**Confidence legend:** `high` = verified by direct file/route read this sprint; `medium` = reported by exploration + corroborated; `low` = inferred, must be confirmed before implementation.

---

## 0. Executive summary

- **Most of the "lost" functionality is not lost — it migrated.** The screenshots largely correspond to the **standalone O&M module** (`modules/operations-and-maintenance/...`), which has been progressively superseded by the **Project Hub** (`modules/project-hub/...`). Many standalone O&M routes are now `DeprecatedRouteRedirect` shims that forward into the Project Hub `om`/`tasks`/`overview` tabs. So the screens are reachable, just under new routes.
- **There is exactly one genuinely orphaned drill-down screen:** the **O&M Device Details page** (`modules/operations-and-maintenance/pages/DeviceDetails/`). Its routes are **commented out** in `App.tsx` (lines ~455–473, `{/*TODO: Device for O&M*/}`), but the component tree still exists on disk — including the **Actual-vs-Projected performance bar chart** (`tabs/Overview/components/Performance.tsx`) and an **Alerts** tab. This is the single highest-value recovery asset.
- **The active device drill-down already exists** as the **Project Hub Device Details** page (`modules/project-hub/pages/DeviceDetails/`), with Overview/Tasks tabs and the Device-Details / Service-Details / Technical-Details cards from screenshot #2. What it is *missing* versus the screenshot is the **performance (actual vs projected) chart** and an **Alerts** tab — both of which exist in the orphaned O&M version.
- **The inverter heatmap and the actual-production gauge are ALIVE and V2-first.** `InvertersPerformance` (heatmap grid) and `ActualProduction` (semi-doughnut gauge) are mounted and already consume V2-first endpoints (with legacy BigQuery only as a flag-gated fallback).
- **The "Site Devices table with category filters + CSV + grouping" from screenshot #3 is only partially present.** The active Project Hub Devices table has search + column toggle + server-side paging, but **no category filter tabs**, **CSV export is wired but disabled**, and **no grouped rows**. These are *additions to an existing table*, not a rebuild.
- **The "Asset Management All Sites / Pipeline / Schedule / Input Form" unified tabbed screen from screenshot #4 does not exist as one screen.** The pieces are real but scattered: the **All Sites table** = Project Hub Projects table (`/project-hub/sites`); the **Pipeline** = the Acquisitions deal pipeline (Kanban + List); the **Input Form** = the Project Hub Overview cards (Key Dates / Ownership / Asset Overview); a construction **Schedule** tab has **no current equivalent** (the only "schedule" is the telemetry refresh scheduler dialog).
- **The only prohibited old-model dependencies still in these paths are flag-gated BigQuery reads** (device liveness, MTBF/MTTR, inverter performance %), all behind `legacy_telemetry_enabled` (default off → honest N/A). `site_additional_fields`, `deals`, and `entity_relationships` are **legitimate PostgreSQL domain stores** (not prohibited old models) — the only standing rule is that SAFL must never be used as a **V2 baseline source** (it is fine for descriptive/lifecycle display).
- **Biggest genuine V2 gap:** there is **no per-device (inverter) expected baseline**, so device-level "actual vs projected" and the heatmap's performance % are honest **N/A** under V2. Recovering the inverter-detail performance chart is therefore a *binding-to-actuals* exercise with an explicit "projected unavailable" state until a per-device baseline exists.

---

## 1. Matched legacy/existing components by screenshot

### Screenshot #1 — O&M company/site dashboard (Overview/Devices/Alerts/Settings, production gauge, past performance, devices summary, actual-vs-projected power/irradiance, inverter heatmap)

| Screenshot element | Existing component | Path | Status | Match |
|---|---|---|---|---|
| O&M company dashboard | `CompanyDetails` (O&M) | `modules/operations-and-maintenance/pages/CompanyDetails/` | Active (scoped route) | high |
| O&M site dashboard | `SiteDetails` (O&M) + Project Hub `OM` tab | `modules/operations-and-maintenance/pages/SiteDetails/` ; `modules/project-hub/pages/AssetManagementSiteDetails/tabs/OM/OM.tsx` | Active | high |
| Actual production gauge | `ActualProduction` | `src/components/charts/ActualProduction/ActualProduction.tsx` | Active | high |
| Past performance chart | O&M Overview widget (per prior audit) | `modules/operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/...` | Active (V2-first) | high |
| Devices summary table | Standalone O&M Devices tab (**dead**) + PH Devices table (**active**) | see §2 | Mixed | high |
| Actual vs projected power/irradiance | O&M Overview widget (per prior audit) | `modules/operations-and-maintenance/.../widgets/...` | Active (V2-first) | medium |
| Inverter performance heatmap/grid | `InvertersPerformance` | `modules/operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/InvertersPerformance/InvertersPerformance.tsx` | Active | high |
| Overview/Devices/Alerts/Settings tabs | Standalone O&M tabs (sub-routes now redirected to PH) | `modules/operations-and-maintenance/pages/SiteDetails/tabs/` | Mixed (redirected) | high |

### Screenshot #2 — Inverter detail (Overview/Alerts/Tasks tabs, device-details card, service-details card, actual/projected performance bars, metadata)

| Screenshot element | Existing component | Path | Status | Match |
|---|---|---|---|---|
| Inverter/device detail shell | **PH** `DeviceDetails` | `modules/project-hub/pages/DeviceDetails/DeviceDetails.tsx` | **Active** (Overview/Tasks tabs) | high |
| Device details card (manufacturer/model, last comm) | `GeneralDeviceInfoCard` | `.../DeviceDetails/tabs/Overview/components/GeneralDeviceInfoCard/` | Active | high |
| Service details card (warranty, availability, next service) | `ServiceDetailCard` | `.../DeviceDetails/tabs/Overview/components/ServiceDetailCard/` | Active | high |
| Technical/inverter-specific card | `TechnicalDetailCard` → `devices/Inverter/Inverter.tsx` | `.../DeviceDetails/tabs/Overview/components/TechnicalDetailCard/` | Active | high |
| **Performance chart (actual vs projected bars)** | **O&M** `Performance` (**orphaned**) | `modules/operations-and-maintenance/pages/DeviceDetails/tabs/Overview/components/Performance.tsx` | **Dead/orphaned** | high |
| **Alerts tab** | **O&M** `DeviceDetails` Alerts tab (**orphaned**) | `modules/operations-and-maintenance/pages/DeviceDetails/tabs/Alerts/Alerts.tsx` | **Dead/orphaned** | high |
| General-info card (orphaned variant) | O&M `GeneralInfo` | `modules/operations-and-maintenance/pages/DeviceDetails/tabs/Overview/components/GeneralInfo.tsx` | Dead/orphaned | high |

> **Key insight:** screenshot #2 is a **hybrid**. The metadata cards already exist and are active in Project Hub; the **performance bars** and the **Alerts** tab exist only in the **orphaned O&M Device Details** component. Recovery = bring the orphaned performance chart + alerts into (or alongside) the active PH detail page, rebinding data to V2.

### Screenshot #3 — Site devices table (category filters, status/performance/type/capacity/last-reported/lifetime/warranty, search, download CSV, grouped)

| Screenshot element | Existing component | Path | Status | Match |
|---|---|---|---|---|
| Site devices table (active) | **PH** `Devices` tab table | `modules/project-hub/pages/AssetManagementSiteDetails/tabs/Devices/Devices.tsx` | Active | high |
| Site devices table (legacy) | **O&M** `Devices` tab table | `modules/operations-and-maintenance/pages/SiteDetails/tabs/Devices/Devices.tsx` | Dead (redirected to PH `om`) | high |
| Search | PH table `SearchAndActions` | (in PH Devices) | Active | high |
| Column toggle | PH `ColumnsModal` | (in PH Devices) | Active | high |
| **Category filter tabs** (inverters/meters/weather/gateways/data captures) | **none** | — | **Missing** | high |
| **Download CSV** | `SearchAndActions` export button (defined, **not enabled** here) | (component supports `showExport`) | **Present-but-disabled** | medium |
| **Grouped/expandable rows** | **none** | — | **Missing** | high |

### Screenshot #4 — Asset Management All Sites / Pipeline / Schedule / Input Form

| Screenshot element | Existing component | Path | Status | Match |
|---|---|---|---|---|
| All Sites table | **PH** Projects table | `modules/project-hub/pages/AssetManagement/components/Sites/Sites.tsx` (`/project-hub/sites`) | Active | high |
| All Sites table (portfolio variant) | My Portfolio Sites | `modules/my-portfolio/pages/PortfolioPage/components/Sites.tsx` (`/portfolio`) | Active | high |
| Pipeline tab | Acquisitions deal pipeline (Kanban + `DealsListView`) | `modules/acquisitions/pages/SalesHome/SalesHome.tsx` (`/acquisitions`) | Active | high |
| Input Form tab | PH Overview cards (Key Dates / Ownership / Asset Overview) | `modules/project-hub/pages/AssetManagementSiteDetails/tabs/Overview/Overview.tsx` | Active | high |
| **Schedule tab** (construction schedule) | **none** (only telemetry refresh `ScheduleDialog`) | `.../tabs/Telemetry/ScheduleDialog.tsx` | **Missing** (different concept) | medium |
| Filters / search / export / "add new site" | PH `SitesTable` controls + Import wizard | `.../AssetManagement/components/Sites/` | Active (export = import-only; no row export) | medium |
| Lifecycle columns (status/stage/ownership/system size/mech completion/NTP/LNTP) | scattered across Site fields + `deals` | see §3, §5 | Active (split sources) | medium |

> **Key insight:** the unified "All Sites + Pipeline + Schedule + Input Form **tabbed**" screen is a *prior-version composition* that no longer exists as one surface. Every piece except a construction **Schedule** view exists today — but in three different modules (Project Hub, Acquisitions, Project Hub Overview). Recovery here is a **composition/navigation** decision, not a rebuild, and a Schedule view would be genuinely new (defer).

---

## 2. Frontend route/component inventory

> Routes confirmed against `frontend/rea-investment-fe/src/App.tsx` this sprint (high confidence on the device-detail region; remainder corroborated by exploration).

### 2.1 Standalone O&M module (`modules/operations-and-maintenance/`)

| Component | Route | Parent | Reachable? | Dead? | API | Notes |
|---|---|---|---|---|---|---|
| `AllCompanies` | `/operations-and-maintenance` (+ scoped) | OM module container | Yes | No | OM companies list | Company list |
| `CompanyDetails` | `/operations-and-maintenance/scope/company/...` | OM container | Yes | No | OM company endpoints | Uses `ActualProduction` gauge |
| `SiteDetails` | `/operations-and-maintenance/scope/project/:projectId` | OM container | Yes | No | OM site endpoints | Hosts Overview widgets incl. heatmap |
| `SiteDetails/tabs/Overview/widgets/InvertersPerformance` | (within site overview) | `SiteDetails` | Yes | No | `siteInvertersPerformanceData(siteId)` | **Heatmap grid (active)** |
| `SiteDetails/tabs/Devices/Devices.tsx` | `companies/:companyId/sites/:siteId/devices` | `SiteDetails` | **Redirected** | **Yes** | `operationsAndMaintenance.devicesBySite` | `DeprecatedRouteRedirect targetTab="om"` (App.tsx ~441) |
| `DeviceDetails/DeviceDetails.tsx` | `companies/:companyId/sites/:siteId/device/:deviceId/(overview\|alerts)` | **commented out** | **No** | **Yes (orphaned)** | `operationsAndMaintenance.getDeviceById(deviceId)` | App.tsx ~455–473 `{/*TODO: Device for O&M*/}` |
| `DeviceDetails/tabs/Overview/components/Performance.tsx` | (inside orphaned detail) | orphaned `DeviceDetails` | No | **Yes (orphaned)** | via `getDeviceById` | **Actual-vs-Projected bars (`ag-charts-react`)** |
| `DeviceDetails/tabs/Alerts/Alerts.tsx` | (inside orphaned detail) | orphaned `DeviceDetails` | No | Yes (orphaned) | device alerts | Alerts tab |
| `DeviceDetails/loader.ts`, `handle.ts` | — | — | No | Yes (orphaned) | `createDeviceDetailsLoader`/`Handle` | Referenced only in commented-out routes |

### 2.2 Shared chart components (`src/components/charts/`)

| Component | Path | Reachable? | API/source | Notes |
|---|---|---|---|---|
| `ActualProduction` | `src/components/charts/ActualProduction/ActualProduction.tsx` | Yes | (fed by O&M overview data) | Semi-doughnut gauge (Low/Mediocre/Good/Outstanding) |

### 2.3 Project Hub (`modules/project-hub/`)

| Component | Route | Parent | Reachable? | Dead? | API | Notes |
|---|---|---|---|---|---|---|
| `AssetManagement/components/Sites/Sites.tsx` | `/project-hub/sites` | `PHRoot` | Yes | No | `assetManagement.sites` (via `SitesTable`) | **All-projects table** |
| `AssetManagementSiteDetails/tabs/OM/OM.tsx` | `/project-hub/projects/:siteId` (OM tab) | `PHSiteDetails` | Yes | No | OM V2 endpoints | **Primary O&M surface; re-imports standalone widgets** |
| `AssetManagementSiteDetails/tabs/Devices/Devices.tsx` | `/project-hub/projects/:siteId` (Devices) | `PHSiteDetails` | Yes | No | `assetManagement.devices(siteId, …)` → `GET /api/sites/{id}/devices/` | **Active devices table** (search + column toggle; CSV defined-but-off; no category tabs; flat) |
| `AssetManagementSiteDetails/tabs/Overview/Overview.tsx` | `/project-hub/projects/:siteId` (Overview) | `PHSiteDetails` | Yes | No | `assetManagement.siteInfo` / `updateSiteInfo` | **Input-form cards** (KeyDates, Ownership, AssetOverview) |
| `AssetManagementSiteDetails/tabs/Telemetry/ScheduleDialog.tsx` | (Telemetry tab dialog) | Telemetry tab | Yes | No | `telemetryV2.getSiteScheduler`/`updateSiteScheduler` | Refresh scheduler (NOT construction schedule) |
| `DeviceDetails/DeviceDetails.tsx` | `/project-hub/companies/:companyId/sites/:siteId/devices/:deviceId/(overview\|tasks)` | `PHModuleContainer` | Yes | No | `assetManagement.deviceById(siteId, deviceId)` + `updateServiceDetail`/`updateTechnicalDetails` | **Active device detail (Overview/Tasks)**; App.tsx ~576–590 |
| `DeviceDetails/tabs/Overview/components/{GeneralDeviceInfoCard, ServiceDetailCard, TechnicalDetailCard, DeviceActionsPanel, DocumentList}` | (within detail) | PH `DeviceDetails` | Yes | No | as above | Cards from screenshot #2 (no perf chart, no alerts tab) |

### 2.4 Acquisitions & Portfolio

| Component | Route | Reachable? | API | Notes |
|---|---|---|---|---|
| `acquisitions/pages/SalesHome/SalesHome.tsx` (+ `DealsListView.tsx`) | `/acquisitions` | Yes | `dealsApi.getPipeline`/`createDeal`/`transitionStage` | **Pipeline (Kanban + List)**; 13-stage flow; NTP/mech/substantial/PTO fields |
| `my-portfolio/pages/PortfolioPage/components/Sites.tsx` | `/portfolio` (Projects tab) | Yes | portfolio sites | Portfolio all-projects table |

### 2.5 Navigation/redirect shims (relevant)

- `components/common/DeprecatedRouteRedirect` (App.tsx import line 30). Used extensively to forward legacy standalone O&M sub-routes to Project Hub tabs:
  - `companies/:companyId/sites/:siteId` → `om` (App.tsx ~430)
  - device/site sub-routes → `om` / `tasks` / `overview` (App.tsx ~437–453, ~553–565, ~594)
- Active PH device-detail routes: App.tsx ~576–590 (`PHDeviceDetails.createHandle/createLoader/Component`).

---

## 3. Backend / API inventory

> Source: backend exploration of `backend/ilios-server/app/...`, corroborated against the prior audit and reconciled in review. **Canonical mounted prefixes:** the O&M router is mounted at `/api/operations-and-maintenance/...` (an `/api/om/...` alias was seen during exploration but the long form is canonical), and the asset-management devices router (`devices_router`) is mounted at `/api/sites/{site_id}/devices`. Confirm exact prefixes against the router registration before any wiring.

| Feature | Endpoint (canonical) | File | Tables/models | Data source | Status |
|---|---|---|---|---|---|
| Device detail (active, PH-consumed) | `GET /api/sites/{site_id}/devices/{device_id}` | `app/routers/assets_management/devices.py` (`devices_router`, mounted at `/api/sites/{site_id}/devices`) | `devices`, `device_documents`, `device_technical_details`, `telemetry_device_mapping`, `site_additional_fields` (via `get_availability_metrics`) | Metadata/service/warranty = Postgres; **MTBF/MTTR + last-reported = BigQuery** (`get_availability_metrics`, `get_devices_last_reported`); **V2 liveness = `TelemetryReadingCRUD`** for V2 sites | Active; BQ liveness **flag-gated** (`legacy_telemetry_enabled`) |
| Device series (V2) | `GET /api/telemetry/v2/sites/{site_id}/device-series` | `app/routers/telemetry/v2.py` | `telemetry_device_interval_rollups` | **V2-native** | Active |
| Inverter performance grid | `GET /api/operations-and-maintenance/sites/{site_id}/inverters-performance-chart` | `app/routers/operations_and_maintenance/sites.py` | `devices`, `telemetry_device_mapping` (+ rollups / BQ) | **V2:** `build_v2_inverter_tiles` over `telemetry_device_interval_rollups` (performance **N/A** — no per-device baseline). **Legacy:** `TelemetryDeviceBigQuery` for performance % | Active; BQ path **flag-gated** |
| Site devices table | `GET /api/operations-and-maintenance/sites/{site_id}/devices` (O&M, legacy) and `GET /api/sites/{site_id}/devices/` (PH/asset-mgmt, active) | `app/routers/operations_and_maintenance/sites.py` ; `app/routers/assets_management/devices.py` | `devices`, `alerts`, `telemetry_device_mapping` | Status/warranty = Postgres; **last-reported = BigQuery** (`get_devices_last_reported`) or **`telemetry_readings`** (V2 sites) | Active; BQ path **flag-gated** |
| Site dashboard / lifecycle | `GET /api/assets-management/sites/{site_id}/details` | `app/routers/assets_management/sites.py` | `sites`, `site_additional_fields`, `documents`, `entity_relationships` | **Postgres** (stage/status/size/milestones via SAFL; ownership via `entity_relationships`) | Active |
| Acquisitions pipeline | `GET /api/acquisitions/pipeline` | `app/routers/sales/deals.py` | `deals` (SalesDeal) | **Postgres** (`lifecycle_state`, `sales_stage`, `system_size`, `notice_to_proceed_date`, `mechanical_completion_date`, …) | Active |
| Expected/baseline (V2) | `GET /api/telemetry/v2/sites/{site_id}/expected-baselines` | `app/routers/telemetry/v2.py` | `telemetry_expected_baselines`/`_points`, `project_facts` | **V2-native** | Active |

**Read-only services available for indicators (reuse, do not rebuild):**
- `app/services/weather/weather_readiness_service.py` — weather readiness blocking_reasons/indicators/warnings glossary.
- `app/services/.../device_eligibility_diagnostics_service.py` — per-device eligibility/mapping/semantics with `blocking_level`.
- reconciliation service (status ladder) — DD provenance → baseline status with `blocking_level`, `required_action`, `missing_dependencies[]`.

---

## 4. Active vs dead / unlinked code findings

### 4.1 Genuinely dead / orphaned (exists on disk, not reachable)

| Item | Path | Why not visible | Recovery lever |
|---|---|---|---|
| **O&M Device Details page** (+ loader/handle) | `modules/operations-and-maintenance/pages/DeviceDetails/` | Routes **commented out** in `App.tsx` (~455–473, `{/*TODO: Device for O&M*/}`) | Reuse-as-reference; harvest perf chart + alerts into active PH detail |
| **O&M device "Actual vs Projected" Performance chart** | `…/DeviceDetails/tabs/Overview/components/Performance.tsx` | Lives inside the orphaned page | Reuse visual shell; rebind to V2 `device-series` |
| **O&M device Alerts tab** | `…/DeviceDetails/tabs/Alerts/Alerts.tsx` | Lives inside the orphaned page | Reuse with alerts data |
| **O&M device GeneralInfo card (variant)** | `…/DeviceDetails/tabs/Overview/components/GeneralInfo.tsx` | Lives inside the orphaned page | Reference only (PH `GeneralDeviceInfoCard` is the live equivalent) |

### 4.2 Reachable only via redirect (legacy route → PH tab)

| Item | Legacy route | Redirects to | Live equivalent |
|---|---|---|---|
| Standalone O&M Devices tab | `companies/:companyId/sites/:siteId/devices` | PH `om` tab | PH `Devices` tab table |
| Standalone O&M site sub-routes | various (App.tsx ~430–453, ~553–565) | `om`/`tasks`/`overview` | PH site-details tabs |

> **Clarification:** the legacy standalone O&M Devices route redirects to the Project Hub **`om`** tab (not to the PH **Devices** tab). The active PH **Devices** table is reachable independently as its own tab on the project-detail page (`/project-hub/projects/:siteId` → Devices) and is unaffected by the redirect.

### 4.3 Active (no recovery needed; rebinding/extension only)

`InvertersPerformance` heatmap; `ActualProduction` gauge; O&M Overview past-performance + actual-vs-projected widgets; PH `DeviceDetails` (cards); PH `Devices` table; PH Projects (All Sites) table; Acquisitions pipeline; PH Overview input-form cards; Telemetry `ScheduleDialog`.

### 4.4 Does not exist (would be new — defer)

- Construction **Schedule** tab/table (Gantt/milestone schedule). Only the telemetry refresh scheduler exists.
- **Category filter tabs** + **grouped rows** on the devices table.
- A single **unified Asset-Management tabbed shell** combining All Sites + Pipeline + Schedule + Input Form.

---

## 5. Old data-model dependency findings

The brief's prohibited "old models" are: BigQuery, Firestore, legacy telemetry modules, SAFL-as-baseline, old DD characteristics, old project-summary fields, hardcoded expected/performance, fabricated zeros. Findings:

| Dependency | Where | Prohibited? | Disposition |
|---|---|---|---|
| **BigQuery — device last-reported** (`get_devices_last_reported`) | device detail + devices table + `assets_management/devices.py` | **Yes** | **Flag-gated** behind `legacy_telemetry_enabled`; V2 path uses `telemetry_readings`. Off → honest N/A. **No V2 fallback for non-V2 sites.** |
| **BigQuery — MTBF/MTTR availability** (`get_availability_metrics`) | device detail | **Yes** | Flag-gated; no V2 equivalent yet (V2 gap). |
| **BigQuery — inverter performance %** (`TelemetryDeviceBigQuery`) | `inverters-performance-chart` | **Yes** | Flag-gated; V2 path returns performance **N/A** (no per-device baseline). |
| Firestore | — | Yes | **None found** in these paths. |
| `site_additional_fields` (SAFL) for **display/lifecycle** | site dashboard | **No** (only prohibited as a *baseline* source) | Acceptable for descriptive/lifecycle display; must **never** become a V2 baseline source (already enforced). |
| `deals` (SalesDeal) | pipeline | **No** | Legitimate acquisitions domain model. |
| `entity_relationships` | ownership | **No** | Legitimate entity-directory model. |
| Hardcoded expected / fabricated zeros | O&M charts | **Yes** | Per prior audit: residual cosmetic fabricated-zeros remain in a few spots (tracked in `om_v2_alignment_audit.md` D5/D6/D7); honest N/A is the standing rule. |

**Ambiguity to resolve before implementation (low confidence):** exploration disagreed on whether lifecycle/milestone fields (mechanical completion, NTP, etc.) live on the **Site model** vs **SAFL** vs **deals**. Both "on Site model" and "via SAFL" were reported. Confirm the authoritative column locations before rebinding the All-Sites/lifecycle columns.

---

## 6. V2 rebinding map (old data dependency → V2-native source)

| Screen / widget | Old dependency | V2-native target | Notes / gap |
|---|---|---|---|
| Actual production gauge | (already V2) | `telemetry_site_interval_rollups` (actual) + `telemetry_expected_baseline_points` (expected) | No change needed; honest N/A when expected absent |
| Past performance chart | (already V2) | `telemetry_site_interval_rollups` | No change |
| Actual vs projected power/irradiance | (already V2) | site rollups (power) + baseline points (projected) + WeatherResolver/`weather_observations` (irradiance) | Irradiance gated by weather readiness/approval |
| Inverter heatmap | BigQuery perf % | `telemetry_device_interval_rollups` via `build_v2_inverter_tiles` | **Performance % = N/A** until per-device baseline exists |
| Site devices table (liveness) | BigQuery `get_devices_last_reported` | `telemetry_readings` (last reading per device) + device mappings | Non-V2 sites = honest N/A |
| Device detail metadata | Postgres (`device_technical_details`) | unchanged (Postgres) | Warranty/service legitimately Postgres |
| Device detail availability (MTBF/MTTR) | BigQuery `get_availability_metrics` | **none yet** | True V2 gap; show "unavailable" not zero |
| **Device detail performance (actual vs projected bars)** | `getDeviceById` (BQ-backed) | `GET /telemetry/v2/sites/{id}/device-series` (actual) | **Projected = N/A** (no per-device baseline) → render actual-only with explicit "projected unavailable" |
| Device "status"/eligibility | — | device eligibility diagnostics + `telemetry_device_mapping` + readings | Reuse diagnostics service |
| All Sites lifecycle columns | Site/SAFL/deals (Postgres) | Site fields + `project_facts` (for "current assumptions"-type fields) | Keep descriptive fields in Postgres; only fields that are *assumptions* should read `project_facts` |
| Pipeline | `deals` (Postgres) | unchanged | Legitimate |
| Input-form cards | `site_additional_fields`/site info | unchanged for display; `project_facts` for promoted assumptions | No SAFL-as-baseline |

**Do NOT** propose BigQuery/Firestore/legacy telemetry as a replacement for anything above.

---

## 7. Screen-by-screen recovery plan

For each surface: (1) code exists? (2) relink / rebind / rebuild? (3) reuse components, (4) preserve patterns, (5) V2 binding changes, (6) missing endpoints, (7) minimal steps, (8) risks, (9) test plan.

### 7.1 O&M company overview
1. Exists (active). 2. **Rebind only** (already V2-first). 3. `CompanyDetails`, `ActualProduction`. 4. Company KPI header + gauge. 5. Ensure company aggregation reads V2 site rollups (per prior audit, already does). 6. None. 7. Verify aggregation precedence; replace any residual fabricated zero with N/A. 8. Low. 9. Aggregation smoke test; no-BQ assertion.

### 7.2 O&M site overview
1. Exists (active). 2. **Rebind only**. 3. `SiteDetails` overview widgets. 4. Widget grid + gauge + heatmap. 5. Already V2-first. 6. None. 7. Confirm honest N/A states. 8. Low. 9. Site-4 smoke.

### 7.3 O&M actual production (gauge)
1. Exists (active). 2. Reuse as-is. 3. `ActualProduction`. 4. Semi-doughnut color bands. 5. None. 6. None. 7. N/A handling when expected absent. 8. Low. 9. Visual smoke.

### 7.4 O&M past performance
1. Exists (active, V2). 2. Reuse as-is. 3. Overview widget. 4. Line/bar style. 5. None. 6. None. 7. — 8. Low. 9. Series smoke.

### 7.5 O&M actual vs projected power / irradiance
1. Exists (active, V2). 2. Rebind/verify. 3. Overview widget. 4. Dual-series chart. 5. Irradiance via WeatherResolver/weather_observations gated by readiness/approval. 6. None (verify weather readiness wired). 7. Add weather-readiness indicator (see §9). 8. Medium (weather gating). 9. Weather-readiness indicator test.

### 7.6 O&M inverter performance grid / heatmap
1. Exists (active). 2. **Rebind**. 3. `InvertersPerformance`. 4. Colored tile grid (Good/Low/None). 5. Tiles from `telemetry_device_interval_rollups`; **performance % = N/A** without per-device baseline → keep neutral coloring + tooltip. 6. (future) per-device baseline. 7. Ensure neutral state is clearly labeled, not zero. 8. Medium (don't imply 0%). 9. Heatmap N/A-state test.

### 7.7 O&M site devices table
1. Exists (active PH table; dead O&M table). 2. **Rebind + extend** the PH table; **do not relink** the dead O&M table. 3. PH `Devices` table, `SearchAndActions`, `ColumnsModal`. 4. AG Grid `BaseTable`, server-side rows. 5. Liveness via `telemetry_readings`; status via eligibility diagnostics. 6. None for data; **enable** existing `SearchAndActions` export; **add** category filter tabs (new UI on existing table). 7. (a) bind liveness to V2, (b) enable CSV export, (c) add category filter control, (d) add eligibility/mapping status chips. 8. Medium (CSV scale, server-side filter params). 9. Filter/search/export tests; no-BQ assertion.

### 7.8 O&M inverter / device detail page
1. **Exists split**: active PH cards + **orphaned** O&M perf chart & Alerts tab. 2. **Rebind + harvest**: keep active PH `DeviceDetails`, **port** `Performance.tsx` (visual shell) and Alerts tab into it, rebinding to V2. 3. PH `DeviceDetails`, `GeneralDeviceInfoCard`, `ServiceDetailCard`, `TechnicalDetailCard`; orphaned `Performance.tsx` (shell). 4. Tabs + cards + `ag-charts-react` bars. 5. Actual from `device-series`; **projected = N/A** (no per-device baseline) → actual-only with explicit "projected unavailable"; availability/MTBF = "unavailable" (no V2 source). 6. Per-device baseline endpoint (future); confirm `device-series` covers needed metrics. 7. (a) add Performance section to PH Overview tab bound to `device-series`, (b) optionally add Alerts tab, (c) explicit unavailable states. 8. **Medium-High** (must not fabricate projected/availability). 9. Device-detail data tests; no-fabricated-zero tests; orphaned-route stays unmounted.

### 7.9 Asset Management All Sites table
1. Exists (active). 2. **Rebind selected columns**. 3. PH `Sites.tsx` / `SitesTable`. 4. AG Grid table + status chips + import wizard. 5. Lifecycle columns from Site/SAFL (display) — confirm source first (§5); assumptions-type fields from `project_facts`. 6. None. 7. Confirm column sources; optionally add row CSV export. 8. Low-Medium. 9. Column-source tests; permission tests.

### 7.10 Asset Management Pipeline tab
1. Exists (active). 2. Reuse as-is. 3. Acquisitions `SalesHome` + `DealsListView`. 4. Kanban + list. 5. None (deals Postgres). 6. None. 7. Optionally surface pipeline within an Asset-Mgmt shell (navigation/composition). 8. Low. 9. Pipeline table tests.

### 7.11 Asset Management Schedule tab
1. **Does not exist** (only telemetry refresh scheduler). 2. **Defer/rebuild** (out of recovery scope). 3. None to reuse. 4. — 5. — 6. Would need new model/endpoint for construction schedule/milestones (data-modeling sprint). 7. Defer. 8. High (new surface + data model). 9. N/A for this sprint.

### 7.12 Asset Management Input Form tab
1. Exists (active). 2. Reuse as-is. 3. PH Overview cards (`KeyDates`, `Ownership`, `AssetOverview`). 4. Editable cards w/ section save. 5. Display Postgres; promoted assumptions via `project_facts`. 6. None. 7. Optionally relabel "Information Cards" ↔ "Input Forms" terminology. 8. Low. 9. Form save tests.

---

## 8. Look-and-feel preservation requirements

Document the existing visual system and require its reuse (no new design language).

- **Layout:** module container + left module sidebar + breadcrumb + context bar; site/company drill-down via tabbed detail pages (Project Hub `…SiteDetails/tabs/*`).
- **Tabs:** MUI tabs; Project Hub tab set is canonical (Overview / OM / Devices / Telemetry / Reconciliation / Tasks).
- **Cards:** MUI cards with section headers + inline edit/save (see `GeneralDeviceInfoCard`, `ServiceDetailCard`, `KeyDates`, `Ownership`, `AssetOverview`).
- **Tables:** **AG Grid via `BaseTable` wrapper**, **server-side row model**, `SearchAndActions` (search + export controls), `ColumnsModal` (column toggle). **Do not introduce a new table library.**
- **Charts:** `ag-charts-react` for bar/series (e.g., device `Performance.tsx`); existing chart components for gauges (`ActualProduction` semi-doughnut). **Do not introduce a new chart library.**
- **Heatmap:** `InvertersPerformance` colored tile grid (Good / Low / None banding). Reuse its coloring scale.
- **Device status icons:** existing chip/icon set (connection-status chip, device-health icon chip, alerts indicator icon).
- **Filters/search/export:** `SearchAndActions` (search input + "Export as" button) + `ColumnsModal`. Category filters, if added, must match this control styling.
- **Typography/spacing/navigation/breadcrumbs/side-nav/top action area:** governed by the existing theme + `utils/breadcrumbs.ts` (CANONICAL_ROUTES/BREADCRUMB_LABELS) + module sidebar + context bar.
- **Indicators:** reuse the reconciliation **`StatusCell`** grammar (status chip + blocking chip + "Next: …" caption + missing-dependency chips + tooltip) for any missing-dependency surfacing.

**Hard requirements (restate for implementers):** do not create new screen designs where legacy components exist; preserve the Ilios look and feel; reuse current design-system components where legacy is stale; **no new chart library, table library, color palette, route pattern, or standalone screen** unless none exists.

---

## 9. Missing-dependency / next-action indicator plan

Reuse existing read-only services (`weather_readiness_service`, `device_eligibility_diagnostics_service`, reconciliation ladder) and the reconciliation `StatusCell` UI grammar. Each indicator: label, explanation, recommended action/target, blocking level.

| Indicator | Label | Explanation | Recommended action → target | Blocking level | Source service |
|---|---|---|---|---|---|
| Baseline not available | "No active baseline" | No active expected baseline for this site | Promote facts → create draft → activate baseline (Reconciliation/Telemetry) | blocks expected | reconciliation/baseline |
| Draft baseline not active | "Draft baseline not activated" | A draft exists but isn't active | Activate baseline (Telemetry) | blocks expected | baseline |
| Accepted DD value not promoted | "Accepted, not promoted" | Accepted DD term not yet in project_facts | Promote to current assumptions (Data Room) | blocks baseline | reconciliation |
| Design points missing | "No design estimate points" | Baseline lacks design points | Generate design points | lowers confidence | baseline |
| Weather profile missing | "No weather profile" | No source profile for (site, role) | Create/activate weather source profile | blocks expected | weather readiness |
| Weather source unapproved | "Weather source not approved" | Profile exists, not approved | Approve weather source | lowers confidence | weather readiness |
| Missing irradiance | "No irradiance input" | No usable irradiance series | Map/declare irradiance device | blocks expected | weather readiness + eligibility |
| Missing cell/module temp | "No cell/module temperature" | No temperature input | Map/declare temperature device | lowers confidence | weather readiness + eligibility |
| Irradiance plane unknown | "Irradiance plane unknown" | Plane semantics undeclared | Declare irradiance_plane | lowers confidence | eligibility (weather semantics) |
| Temperature type unknown | "Temperature type unknown" | ambient vs cell undeclared | Declare temperature_type | lowers confidence | eligibility |
| Calibration unknown/expired | "Calibration unknown" | calibration_status unknown/expired | Declare/refresh calibration | informational/lowers confidence | eligibility |
| Device exists but not mapped | "Device not mapped" | Device present, no telemetry mapping | Map device (Telemetry mapping) | blocks reporting | eligibility diagnostics |
| Mapped but no telemetry | "Mapped, no readings" | Mapped device has no usable telemetry | Check provider/credentials/catalog | blocks reporting | eligibility diagnostics |
| Metric catalog unsupported | "Metric unsupported" | Provider field not in metric catalog | Extend metric catalog | lowers confidence | telemetry catalog |
| Gateway, children unmapped | "Gateway children unmapped" | Gateway present, child devices unmapped | Map child devices | blocks reporting | eligibility diagnostics |
| Meter not used for site actual | "Meter not site-actual" | Meter present but not driving site actual | Confirm meter role (informational) | informational | eligibility diagnostics |
| Expected available, weather unverified | "Weather unverified" | Expected exists but weather source unverified | Verify/approve weather source | lowers confidence | weather readiness |
| Historical weather imported, unapproved | "Imported, not approved" | Backfill present, not approved | Approve weather source | lowers confidence | weather readiness |
| Document but no accepted values | "No accepted values" | Doc uploaded, nothing accepted | Accept extracted values (Data Room) | blocks baseline | reconciliation |
| Accepted, not in project_facts | "Not promoted to facts" | Accepted values not promoted | Promote to current assumptions | blocks baseline | reconciliation |
| project_facts not in draft baseline | "Facts not in baseline" | Facts exist but not used in draft | Create draft from facts | blocks baseline | reconciliation/baseline |

**Placement:** device-level indicators → device detail + devices table status chips; site-level → OM/Telemetry tab summary panel; DD/baseline → Reconciliation table (already implemented). Do not invent new indicator UI — reuse `StatusCell`.

---

## 10. Existing-code reuse classification

| Component | Classification | Why |
|---|---|---|
| `ActualProduction` gauge | **Reuse as-is** | Active, V2-fed where used |
| O&M past-performance / actual-vs-projected widgets | **Reuse with V2 binding** | Active, V2-first; verify N/A states |
| `InvertersPerformance` heatmap | **Reuse with V2 binding** | Active; performance % = N/A gap |
| PH `DeviceDetails` + cards (`GeneralDeviceInfoCard`, `ServiceDetailCard`, `TechnicalDetailCard`) | **Reuse as-is / with V2 binding** | Active canonical detail; add performance section |
| Orphaned O&M `Performance.tsx` (actual vs projected bars) | **Reuse visual shell only** | Good chart shell; rebind to `device-series`; host page is abandoned |
| Orphaned O&M `DeviceDetails` Alerts tab | **Reuse with data** | Useful; port into active detail |
| Orphaned O&M `DeviceDetails` page/loader/handle/GeneralInfo | **Deprecated but useful reference** | Superseded by PH; do not relink |
| Standalone O&M `Devices` table | **Deprecated but useful reference** | Redirected; PH table is canonical |
| PH `Devices` table (+ `SearchAndActions`, `ColumnsModal`) | **Reuse with V2 binding + extend** | Add category filters, enable CSV, V2 liveness |
| PH `Sites` (All Sites) table | **Reuse as-is / column rebind** | Active; confirm lifecycle column sources |
| Acquisitions pipeline (`SalesHome`, `DealsListView`) | **Reuse as-is** | Active; legitimate deals model |
| PH Overview input-form cards | **Reuse as-is** | Active |
| Telemetry `ScheduleDialog` | **Do not reuse for construction Schedule** | Different concept (refresh scheduler) |
| Construction Schedule view | **Do not reuse (none exists)** | Defer to data-modeling sprint |

---

## 11. Implementation phase plan

> Phased, additive, reuse-first. Each phase: risk / files likely touched / backend? / frontend? / tests / non-goals.

**Phase 1 — Verify & document current reachability (no behavior change)**
- Risk: very low. Files: none (audit follow-through). BE: no. FE: no.
- Tests: route reachability snapshot; confirm orphaned O&M detail stays unmounted.
- Non-goals: no relinking yet.

**Phase 2 — Rebind O&M site/company overview widgets to V2 (confirm honest N/A)**
- Risk: low. Files: O&M overview widgets, company aggregation. BE: maybe (verify). FE: yes.
- Tests: aggregation smoke, no-BQ assertion, no-fabricated-zero.
- Non-goals: no new widgets.

**Phase 3 — Site devices table: V2 liveness + enable CSV + category filters + status chips**
- Risk: medium. Files: PH `Devices` table, `SearchAndActions` usage, devices endpoint params. BE: yes (liveness/filter params). FE: yes.
- Tests: filter/search/export, V2 liveness, no-BQ.
- Non-goals: no grouped rows unless trivially supported; no new table lib.

**Phase 4 — Inverter/device detail: harvest performance chart + alerts into active PH detail, V2-bound**
- Risk: medium-high. Files: PH `DeviceDetails` Overview tab (+ ported `Performance` shell), `device-series` consumption. BE: maybe (confirm device-series metrics). FE: yes.
- Tests: device-detail data, projected/availability = explicit "unavailable" (no fabricated zero), orphaned route remains unmounted.
- Non-goals: do not build per-device baseline; do not relink orphaned route.

**Phase 5 — Asset Management All Sites: confirm + rebind lifecycle columns**
- Risk: low-medium. Files: PH `Sites`/`SitesTable`. BE: maybe (column source confirmation). FE: yes.
- Tests: column-source, permissions.
- Non-goals: no Schedule tab; no new unified shell.

**Phase 6 — Missing-dependency indicators across recovered surfaces**
- Risk: medium. Files: device detail, devices table, OM/Telemetry summary panels (reuse `StatusCell`). BE: reuse existing read-only services. FE: yes.
- Tests: indicator presence/blocking-level per gap.
- Non-goals: no new indicator UI grammar.

**Phase 7 — Weather provenance + device diagnostics surfacing**
- Risk: medium. Files: OM/Telemetry tab panels. BE: reuse readiness/eligibility services. FE: yes.
- Tests: weather-readiness + eligibility indicator tests.
- Non-goals: no resolver/import changes.

**Phase 8 — Export/download polish (only where existing code supports it)**
- Risk: low-medium. Files: tables using `SearchAndActions`. BE: maybe (server-side export). FE: yes.
- Tests: export tests.
- Non-goals: no new export framework.

**Phase 9 — Defer unsupported legacy-only fields & Schedule view**
- Risk: n/a (deferral). Document gaps (per-device baseline, MTBF/MTTR V2, construction Schedule, LNTP) for a later data-modeling sprint.

---

## 12. Risks and non-goals

**Risks**
- **Fabricated projected/availability:** device-level "projected" and MTBF/MTTR have no V2 source — must render explicit "unavailable", never zero or a guessed value.
- **Heatmap perception:** neutral/N/A tiles must not read as "0% performance."
- **Lifecycle column source ambiguity (§5):** confirm Site vs SAFL vs deals before rebinding columns.
- **Relinking the orphaned O&M detail instead of harvesting it:** would resurrect a BQ-backed `getDeviceById` path; harvest the shell into the active PH detail instead.
- **Server-side filter/export scale:** category filters + CSV must respect server-side paging.
- **Permission gating:** asset-management/O&M permissions may hide surfaces for standard users; verify gates, avoid silent redirects.

**Non-goals (hard constraints — restated)**
- No code, migrations, new routes, relinking, new screens, UI redesign, or data-model changes in *this* sprint (this is an audit).
- Do not change expected math, telemetry ingestion, WeatherResolver, device eligibility, baseline lifecycle, or DD parsing/prompts.
- Do not touch plaintext secrets.
- Do not reintroduce BigQuery / Firestore / legacy telemetry as a data source.
- Do not introduce a new chart/table library, color palette, route pattern, or standalone screen where an existing component applies.

---

## 13. Recommended next-sprint prompt

> Implementation sprint: **"O&M / Device-Detail Drill-Down V2 Rebinding (reuse-first)."**
>
> Goal: recover the prior-version O&M drill-down experience by **reusing existing components** and **rebinding to V2-native data** — no new screens, no new libraries, no BigQuery/Firestore.
>
> Do, in order:
> 1. **Devices table (PH `tabs/Devices/Devices.tsx`):** bind device liveness to `telemetry_readings` (V2), **enable the existing `SearchAndActions` CSV export**, add **category filter tabs** (inverter / production meter / weather station / gateway / data capture) styled to match `SearchAndActions`, and add **eligibility/mapping status chips** sourced from `device_eligibility_diagnostics_service`. No new table library; keep AG Grid `BaseTable` server-side.
> 2. **Device detail (PH `pages/DeviceDetails`):** add a **Performance section** to the Overview tab by **porting the visual shell of the orphaned** `modules/operations-and-maintenance/pages/DeviceDetails/tabs/Overview/components/Performance.tsx` and binding **actual** to `GET /api/telemetry/v2/sites/{id}/device-series`. Render **projected and availability/MTBF as explicit "unavailable"** (no per-device baseline / no V2 availability source yet — never fabricate zero). Optionally port the orphaned **Alerts** tab. **Do not relink** the commented-out O&M device route.
> 3. **Missing-dependency indicators:** reuse the reconciliation **`StatusCell`** grammar and the existing read-only services (`weather_readiness_service`, `device_eligibility_diagnostics_service`, reconciliation ladder) to surface the §9 indicators on device detail, the devices table, and the OM/Telemetry summary panels.
> 4. **All Sites / lifecycle columns (PH `Sites.tsx`):** first **confirm the authoritative column source** (Site model vs `site_additional_fields` vs `deals`), then rebind display columns; read promoted assumptions from `project_facts` where applicable. Keep SAFL display-only (never a baseline source).
> 5. **Heatmap & gauge:** verify `InvertersPerformance` and `ActualProduction` show honest N/A states (no implied 0%).
>
> Constraints: additive, reuse-first; preserve Ilios look-and-feel; no expected-math / ingestion / resolver / eligibility / baseline / DD changes; no secrets; no BigQuery/Firestore/legacy telemetry; no construction **Schedule** view (defer to a data-modeling sprint along with per-device baseline and MTBF/MTTR V2 sources).
>
> Tests: route reachability + permissions; device-table filter/search/export; device-detail data + "unavailable" (no fabricated zero); indicator presence/blocking-level; no-BQ/Firestore grep; FE typecheck/build; backend targeted tests; **site 4 smoke**.

---

## Appendix I. Testing plan for future implementation

- **Route reachability:** active routes resolve; orphaned O&M device route stays unmounted; redirects forward correctly.
- **Permissions:** asset-management/O&M gates enforced; no silent permission redirect on recovered surfaces.
- **Surface smoke:** company overview, site overview, gauge, past performance, actual-vs-projected, heatmap, devices table, device detail, All Sites, pipeline, input-form cards.
- **V2 data binding:** device liveness from `telemetry_readings`; device performance from `device-series`; site/company aggregation from rollups; expected from baseline points.
- **No BigQuery/Firestore usage:** grep + runtime assertion on recovered paths (with `legacy_telemetry_enabled` off).
- **No fabricated zero:** projected/availability/performance render "unavailable"/N/A, not 0.
- **Missing-dependency indicators:** each §9 indicator appears with correct `blocking_level` for seeded gaps.
- **Device table filters/search/export:** category filter narrows server-side; search server-side; CSV export produces expected columns.
- **Inverter detail data:** actual series populated; projected explicitly unavailable; metadata/service cards intact.
- **Asset Management pipeline/schedule tables:** pipeline list/kanban render; lifecycle columns map to confirmed sources.
- **FE typecheck/build** and **backend targeted tests** green.
- **Site 4 (110 Shawmut) smoke:** mappings intact; recovered surfaces render with real V2 data.

---

*End of audit v1.0. Audit-only: no code, routes, migrations, relinking, UI, or data-model changes were made. All recovery work above is recommendation only and gated on a future implementation sprint.*
