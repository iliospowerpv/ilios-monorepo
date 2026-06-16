# iliOS O&M Existing Screens + V2 Data Alignment Audit

**Document Version:** 1.0
**Audit Date:** June 15, 2026
**Audit Type:** Read-Only Design / Architecture Review — **NO code, migrations, schema, or UI changes were made**
**Scope:** All existing Operations & Maintenance (O&M) and performance screens, their backend endpoints, and their alignment to the V2-native data stack (native telemetry rollups, expected baselines, project_facts, WeatherResolver provenance, device eligibility diagnostics, reconciliation).

> **This is a planning deliverable only.** It recommends *surgical* changes to **existing** screens/components for a future implementation sprint. It does not change expected math, ingestion, device eligibility, WeatherResolver, baselines, due-diligence parsing, secrets, and it does not reintroduce BigQuery/Firestore/legacy telemetry. Where a new panel is recommended, the existing host surface is named — no new standalone pages are proposed.

---

## Table of Contents

1. [Frontend Screen Inventory](#1-frontend-screen-inventory)
2. [Backend / API Inventory](#2-backend--api-inventory)
3. [Old-Model Dependency Findings](#3-old-model-dependency-findings)
4. [Look-and-Feel / Design-System Findings](#4-look-and-feel--design-system-findings)
5. [V2 Alignment Plan by Screen](#5-v2-alignment-plan-by-screen)
6. [Missing-Dependency Indicator Placement Plan](#6-missing-dependency-indicator-placement-plan)
7. [Navigation Findings](#7-navigation-findings)
8. [Weather / Device Readiness Placement](#8-weather--device-readiness-placement)
9. [Testing Plan](#9-testing-plan)
10. [Recommended Implementation Sprint Prompt](#10-recommended-implementation-sprint-prompt)
11. [Risks and Non-Goals](#11-risks-and-non-goals)

---

## Executive Summary

The O&M experience exists today as **two parallel front-end surfaces** that share the same widget components and (mostly) the same backend:

- **A) Standalone O&M module** (`/operations-and-maintenance/...`) — portfolio → company → site drill-down, gated by the `O&M (Production Monitoring)` permission.
- **B) Project Hub "OM" tab** inside Asset Management Site Details (`/project-hub/projects/:siteId`) — the **modern primary entry point**, which re-imports the standalone module's widgets and adds the Telemetry + Devices panels.

The backend has **already migrated most O&M chart endpoints to V2-native** PostgreSQL rollups/baselines with a **V2-first precedence** (`site_has_v2_rollups` → render from Postgres and never touch BigQuery). Legacy BigQuery paths remain only as a **flag-gated fallback** (`legacy_telemetry_enabled`, default **off**) and, when off, the system correctly returns **honest N/A / `null`** rather than fabricated zeros.

The **gaps that the future sprint should close are mostly presentational and navigational**, not computational:

1. **Two list paths lack V2 coverage** — the company "sites" table and the investor-dashboard "sites" table (both via `extend_company_sites_with_energy_attributes`). They are correctly gated by `legacy_telemetry_enabled` (off by default → **honest N/A**, never fabricated zeros and never stale BigQuery), but they have **no V2 rollup fallback**, so energy columns render N/A even for sites that *do* have V2 rollups. The code itself marks this deferred. Filling them from rollups/baselines is the main data-source opportunity.
2. **The OM tab uses a single generic "data is flowing" gate** and a single info Alert. It should adopt the **Path-B granular missing-dependency indicators** (baseline missing, weather unapproved, device mapped-but-no-telemetry, etc.) that already exist as services (`weather_readiness_service`, `device_eligibility_diagnostics_service`, reconciliation ladder).
3. **Residual fabricated-zero display** in one legacy backend branch (BQ exception while flag on) and one front-end formatter default. Low risk; tidy to `null`/N/A.
4. **Navigation fragmentation** between the two O&M surfaces, an inconsistent route-param shape, and a **silent redirect** on permission failure.

No structural rebuild is warranted. All recommendations are insert-a-panel / swap-a-data-source / add-a-badge / add-a-link changes inside existing surfaces.

---

## 1. Frontend Screen Inventory

All paths are relative to `frontend/rea-investment-fe/src/`.

### 1.1 Standalone O&M Module (surface A)

| Screen | File | Route | Parent | Purpose | Permission gating | Data source (API) | State | UI pattern |
|---|---|---|---|---|---|---|---|---|
| O&M All Companies | `modules/operations-and-maintenance/pages/AllCompanies/AllCompanies.tsx` | `/operations-and-maintenance/companies` | `ModuleContainer` | Portfolio-wide company list w/ system size, actual production, alerts | `O&M (Production Monitoring):view` (else redirect `/`) | `ApiClient.operationsAndMaintenance.companies()` | `useState` (search), `useMemo` (SSRM datasource) | AG Grid (`BaseTable`) + `AlertsIndicator`, `PowerProductionIndicator` |
| O&M Company Details | `modules/operations-and-maintenance/pages/CompanyDetails/CompanyDetails.tsx` | `/operations-and-maintenance/companies/:companyId` | `ModuleContainer` | Company tabs: Overview, Sites, Alerts, Tasks | `company_view`/`company_admin_full` | `companyDetailsQuery` (useQuery) | `useQuery`, `useEntityContext` | MUI `Tabs`, `Box`, `Typography` |
| O&M Company → Overview (Losses) | `modules/operations-and-maintenance/pages/CompanyDetails/tabs/Overview/widgets/Losses/Losses.tsx` | (tab) | CompanyDetails | Company energy-loss breakdown | inherits | company actual/expected + losses endpoints | `useQuery` | Chart.js |
| O&M Site Details | `modules/operations-and-maintenance/pages/SiteDetails/SiteDetails.tsx` (breadcrumbs: `…/SiteDetails/handle.ts`) | scoped: `/operations-and-maintenance/scope/project/:projectId`; legacy: `/operations-and-maintenance/companies/:companyId/sites/:siteId` (legacy → canonical via `DeprecatedRouteRedirect`) | `ModuleContainer` | Site tabs: Overview, Devices, Alerts, Tasks | `O&M:view` + site access | site-scoped queries | `useQuery` | MUI `Tabs` w/ icons + divider underline; breadcrumb links site name back to PH OM tab |
| Site Overview widgets | `modules/operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/*` | (tab) | SiteDetails Overview | See widget table below | inherits | per-widget (see §2) | `useQuery` | `WidgetContainer` styled + Chart.js |
| Site Devices | `modules/operations-and-maintenance/pages/SiteDetails/tabs/Devices/Devices.tsx` | (tab) | SiteDetails | Device list + status | `O&M:view` | `operationsAndMaintenance.getSiteDevices` | `useQuery` | AG Grid / MUI Table |
| Site Tasks | `modules/operations-and-maintenance/pages/SiteDetails/tabs/Tasks/Tasks.tsx` | (tab) | SiteDetails | Site O&M tasks | inherits | tasks API | `useQuery` | Tasks cluster |
| Module gate | `modules/operations-and-maintenance/ModuleContainer.tsx` | wraps all of the above | router | Auth + `O&M (Production Monitoring)` view gate | **silent** `<Navigate to="/" />` on failure | — | `useAuth` | Outlet |

### 1.2 Project Hub / Asset Management (surface B — primary)

| Screen | File | Route | Parent | Purpose | Permission gating | Data source (API) | State | UI pattern |
|---|---|---|---|---|---|---|---|---|
| AM Site Details (host) | `modules/project-hub/pages/AssetManagementSiteDetails/AssetManagementSiteDetails.tsx` | `/project-hub/projects/:siteId` | project-hub | Tabbed site detail (Overview, OM, Telemetry, Devices, Reconciliation, …) | `siteDetailsQuery` access; Reconciliation needs `Diligence:view`/system | `assetManagement.getSiteDetails` | `useQuery`, `useEntityContext` | MUI `Tabs` (icons + divider) |
| **OM tab** | `…/AssetManagementSiteDetails/tabs/OM/OM.tsx` | `/project-hub/projects/:siteId` (tab `om`) | AM Site Details | Performance dashboard + Telemetry + Devices | gated by `getTelemetryReadiness` (`is_connected && is_site_mapped && is_data_flowing`) | `ApiClient.connections.getTelemetryReadiness(siteId)` + child widgets | `useQuery`, `useFocusHighlight` | MUI `Grid` (20-col), `Alert`, `Divider`, embeds standalone widgets |
| Overview tab | `…/tabs/Overview/Overview.tsx` (+ `DraggableLayout`) | (tab) | AM Site Details | Draggable info-card dashboard | site access | site details + info-card queries | `useQuery` | `InformationCardBase`, drag-and-drop |
| Telemetry tab | `…/tabs/Telemetry/Telemetry.tsx` | (tab `telemetry`) | AM Site Details / OM tab | Readiness, health, connection mgmt, refresh, **eligibility diagnostics panel** | `useTelemetryAdminPermission` for admin actions | `connections.getTelemetryReadiness`, `connections.getTelemetryHealth`, eligibility-diagnostics | `useQuery`, `useState` | `Paper`, `Chip` (ReadinessStrip), `Alert`, `TelemetryWizard`, `RefreshTelemetryButton`, `EligibilityDiagnosticsPanel` |
| Devices tab | `…/tabs/Devices/Devices.tsx` | (tab) | AM Site Details | Device inventory + status | site access | devices API | `useQuery` | AG Grid (`BaseTable`) |
| Reconciliation tab | `…/tabs/Reconciliation/Reconciliation.tsx` | `/project-hub/projects/:siteId/reconciliation` | AM Site Details | Read-only fact→baseline provenance ladder | `is_system_user` OR `Diligence:view` (else `Alert` "Access restricted") | `reconciliation.getSiteReconciliation` | `useQuery` | `ReconciliationTable` + `StatusCell`/`StatusChip`, `ReadinessSummary`, `NoDataOverlay` |
| Company Performance tab | `modules/project-hub/pages/AssetManagementCompanyDetails/tabs/Performance/Performance.tsx` | `/project-hub/companies/:companyId` (tab) | AM Company Details | Company-level performance/production | company access | `operationsAndMaintenance` company endpoints | `useQuery` | Chart.js + cards |

### 1.3 Shared O&M / Performance Widgets (reused by both surfaces)

| Widget | File | Purpose | Data source | UI |
|---|---|---|---|---|
| Actual Production (gauge) | `modules/operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/ActualProduction/ActualProduction.tsx` | Actual vs expected energy gauge + current/cumulative toggle | `operationsAndMaintenance.getSiteDashboardProduction(siteId)` + `useSiteLatestTelemetry` | Chart.js `Doughnut`, `ToggleGroup` |
| Past Performance | `…/widgets/PastPerformance/PastPerformance.tsx` | Historical actual-vs-expected ratio trend | `…/past-performance-chart` | Chart.js line/bar |
| Actual vs Projected Power | `…/widgets/ActualProjectedPower/ActualProjectedPower.tsx` | Actual power + irradiance vs expected line | `…/actual-vs-expected-chart` | Chart.js |
| Inverters Performance | `…/widgets/InvertersPerformance/InvertersPerformance.tsx` | Per-inverter output/health tiles | `…/inverters-performance-chart` | MUI `Card` + Chart.js |
| Devices Overview | `…/widgets/Devices/Devices.tsx` | Device stats/health summary | `…/devices-overview-section` | cards |
| Losses (company) | `modules/operations-and-maintenance/pages/CompanyDetails/tabs/Overview/widgets/Losses/Losses.tsx` | Company loss breakdown | `…/loses-for-a-day-chart` | Chart.js |
| Top-level chart helper | `components/charts/ActualProduction/ActualProduction.tsx` | Shared chart rendering | (props) | Chart.js |
| Power indicator | `components/common/PowerProductionIndicator/PowerProductionIndicator.tsx` | Cell renderer for production | (props) | chip/indicator |

**Cross-surface coupling note:** the Project Hub OM tab (`tabs/OM/OM.tsx`) imports widgets directly out of the standalone O&M module via deep relative paths (`../../../../../operations-and-maintenance/...`). Any data-source change to a widget automatically affects **both** surfaces — this is a benefit for the sprint (single edit, two surfaces) but must be regression-tested on both.

---

## 2. Backend / API Inventory

All paths relative to `backend/ilios-server/`. Classification: **V2-native** (PostgreSQL rollups/baselines/facts), **Legacy** (BigQuery/Firestore behind `legacy_telemetry_enabled`), **Mixed** (V2-first precedence with legacy fallback), **N/A** (no telemetry data source).

### 2.1 O&M Site endpoints — `app/routers/operations_and_maintenance/sites.py`

| Route | Service/helper | Tables / sources | Class. | V2 reads | Notes |
|---|---|---|---|---|---|
| `GET /api/operations-and-maintenance/sites/{id}` | `get_authorized_site` | `Site` | N/A | — | Marked `# TODO periodically check usage, potentially can be deleted` |
| `GET …/{id}/devices` | `get_devices_last_reported` | `Device`, **BigQuery (flag-gated)** | **Legacy (gated; no V2 yet)** | — | Last-reported liveness is legacy BigQuery gated by `legacy_telemetry_enabled` (off → empty list, honest "no legacy signal"). **This endpoint has no native-readings fallback** (unlike `devices-overview-section`, which uses V2 raw-reading recency via `get_site_devices_info`) |
| `GET …/{id}/actual-production-chart` | `site_has_v2_rollups` → `apply_v2_actual_production`; else `get_production_chart_data_per_site` | `telemetry_site_interval_rollups`, `telemetry_expected_baselines` **OR** BigQuery | Mixed (V2-first) | rollups + baselines | **V2-first**: if V2 rollups exist, render Postgres, never touch BQ. Legacy off → `None` (honest). **Legacy-on BQ-exception fabricates `0.0` (lines ~145-148).** |
| `GET …/{id}/inverters-performance-chart` | `build_v2_inverter_tiles`; else `TelemetryDeviceBigQuery.get_devices_performance` | `telemetry_device_interval_rollups` **OR** BigQuery | Mixed (V2-first) | device rollups | V2 path renders neutral tiles (no per-device baseline). Legacy off → per-inverter `"N/A"`. Default obj seeds `performance: 0` before overwrite to N/A (cosmetic). |
| `GET …/{id}/past-performance-chart` | `build_past_performance_section`; else `TelemetrySiteBigQuery.get_site_past_performance` | `telemetry_site_interval_rollups`, `telemetry_expected_baselines` **OR** BigQuery | Mixed (V2-first) | rollups + baselines | V2: empty + `expected_baseline_available:false` when no active baseline. Legacy off → honest empty. |
| `GET …/{id}/actual-vs-expected-chart` | `build_actual_vs_expected_section`; else `TelemetrySiteBigQuery.get_site_actual_vs_expected_irradiance` | rollups, baselines **OR** BigQuery | Mixed (V2-first) | rollups + baselines | V2 overlays expected from native baseline; null + no-baseline flag when none. |
| `GET …/{id}/devices-overview-section` | `get_site_devices_info` | `Device`, `Alert` | N/A | — | Internal aggregates only |

### 2.2 O&M Company endpoints — `app/routers/operations_and_maintenance/companies.py`

| Route | Service/helper | Tables / sources | Class. | Notes |
|---|---|---|---|---|
| `GET /api/operations-and-maintenance/companies/` | `get_sites_latest_power`, `get_alerts_overview` | `Company`, `Site`, `Alert`, `telemetry_site_interval_rollups` | V2-native | Portfolio list latest power from rollups |
| `GET …/companies/{id}/sites` | `extend_company_sites_with_energy_attributes` | `Site`, `Alert`, **BigQuery (flag-gated)** | **Legacy (gated; no V2 yet)** | Energy columns → honest N/A when `legacy_telemetry_enabled` off (default); BigQuery only when on. **No V2 rollup fallback** (deferred per code comment) |
| `GET …/companies/{id}/actual-production-chart` | `get_company_actual_production_section_with_telemetry` | rollups, baselines | V2-native | |
| `GET …/companies/{id}/actual-vs-expected-production-chart` | `get_company_actual_vs_expected_production_section_with_telemetry` | rollups | V2-native (actuals) | |
| `GET …/companies/{id}/loses-for-a-day-chart` | `aggregate_company_actuals`, `compute_sites_expected_today` | rollups, baselines | V2-native | |

### 2.3 Telemetry health / device health / eligibility

| Route | Router | Service | Tables | Class. |
|---|---|---|---|---|
| `GET /api/telemetry/v2/sites/{id}/eligibility-diagnostics` | `telemetry/v2.py` | `device_eligibility_diagnostics_service.compute_site_eligibility_diagnostics` | `Site`, `Device`, `telemetry_readings`, `telemetry_site_interval_rollups` | V2-native (read-only) |
| `GET …connections/getTelemetryReadiness` / `getTelemetryHealth` | telemetry routers | readiness/health services | mappings, readings, rollups | V2-native |
| `GET /api/sites/{id}/devices` | `assets_management/devices.py` | `get_availability_metrics` | `Device`, `telemetry_readings` | Mixed |

### 2.4 Weather / Reconciliation / Investor dashboard

| Route | Router | Service | Tables | Class. |
|---|---|---|---|---|
| `GET /api/weather/sites/{id}/historical-readiness` | `weather.py` | `compute_weather_readiness` | `weather_observations`, `weather_source_profiles` | V2-native |
| `GET /api/due-diligence/sites/{id}/reconciliation` | `due_diligence/reconciliation.py` | `build_site_reconciliation` | `project_facts`, `telemetry_expected_baselines`, `telemetry_expected_baseline_points`, **SAFL (display-only)** | V2-native (SAFL comparison-only, never baseline source) |
| `GET /api/investor-dashboard/companies` | `investor_dashboard/companies.py` | `aggregate_company_expected`, `get_sites_latest_power` | rollups, baselines | V2-native |
| `GET /api/investor-dashboard/companies/{id}/actual-production` | `investor_dashboard/companies.py` | `get_company_actual_production_section_with_telemetry` | rollups, baselines | V2-native |
| `GET /api/investor-dashboard/sites` | `investor_dashboard/sites.py` | `extend_company_sites_with_energy_attributes` | `Site`, **BigQuery (flag-gated)** | **Legacy (gated; no V2 yet)** — same helper as §2.2 sites; honest N/A by default, no V2 fallback |

---

## 3. Old-Model Dependency Findings

| # | Dependency | Location | Active? | Surface | V2 replacement | Surgical? |
|---|---|---|---|---|---|---|
| D1 | **Company/investor "sites" table lacks V2 coverage** | `extend_company_sites_with_energy_attributes` (used by O&M `companies/{id}/sites` **and** `investor-dashboard/sites`) | Flag-gated by `legacy_telemetry_enabled` (default off → **honest N/A**); BigQuery only when flag on. **No V2 rollup fallback**, so energy columns are N/A even for V2 sites. Code comment marks it **deferred** | O&M Company Sites tab, Investor Dashboard | Per-site latest power/energy from `telemetry_site_interval_rollups` + expected from `telemetry_expected_baselines` (reuse `get_sites_latest_power`/company aggregation already used elsewhere) | **Surgical** (one helper, two call sites) — recommended data-source fill |
| D2 | **BigQuery — site charts** | `om/sites.py` actual-production / inverters / past-performance / actual-vs-expected | ACTIVE only as **flag-gated fallback** (`legacy_telemetry_enabled`, default off); V2-first precedence already in place | O&M site charts | Already V2 when rollups exist | No action needed except D5 cleanup |
| D3 | **BigQuery write — DD "characteristics"** | (removed from active DD flow) | **DEAD** (writes removed) | none | `project_facts` | Already done |
| D4 | **Firestore — DAS mapping sync** | `telemetry_helper.create_site_mapping_for_telemetry` | Inactive (legacy flag off) | Portfolio Admin (mapping) | V2 credential store / native mappings | Out of O&M scope; leave gated |
| D5 | **Fabricated zero (backend)** | `om/sites.py` ~lines 145-148 — BQ exception while legacy flag **on** sets `0.0` | Active only when legacy flag on + BQ throws | O&M Actual Production | Return `None` + `expected_baseline_available:false` (match the flag-off branch) | **Surgical** (low risk) |
| D6 | **Fabricated zero (frontend)** | `ActualProduction.tsx` `formatFloatValue` defaults to `0` for display (~line 152) | Active | Actual Production gauge | Render `—`/`N/A` when source is `null` (preserve null through to the formatter) | **Surgical** (low risk) |
| D7 | **Inverter tile seed `performance: 0`** | `om/sites.py` `get_inverters_performance_chart` default obj | Active (overwritten to `"N/A"` in off path) | Inverters Performance | Cosmetic; seed `"N/A"` | Optional tidy |
| D8 | **SiteAdditionalFieldList (SAFL) as baseline source** | `telemetry_expected.create_draft` (deprecated); reconciliation (display-only) | `create_draft` deprecated-but-active; reconciliation display-only | Telemetry setup / Reconciliation | `create-draft-from-facts` (facts→baseline bridge); SAFL stays display/comparison-only | Separate sprint (baseline lifecycle) — **do not touch in O&M sprint** |
| D9 | **Old project-summary / characteristics fields** | shared `Site`/legacy reporting templates | Legacy reporting only | shared services | `project_facts` (canonical) | Out of O&M scope |
| D10 | **Device last-reported lacks V2 coverage** | `get_devices_last_reported` (backs `GET …/{id}/devices`) | Flag-gated by `legacy_telemetry_enabled` (default off → empty list); BigQuery only when on. No native-readings fallback in this endpoint (cf. `devices-overview-section`, already V2) | O&M site Devices liveness | Derive last-reported recency from `telemetry_readings` (reuse the recency logic already in `get_site_devices_info`) | **Surgical** (one helper) — recommended data-source fill |

**Net:** there are **no active, un-gated old-model data reads** in the O&M surface. The legacy site-table path (**D1**) is flag-gated to honest N/A but lacks a V2 fallback — a **coverage gap, not a data leak**. The only residual cosmetic issues are the **fabricated-zeros D5/D6/D7**. Everything else is dead, correctly gated to honest N/A, or belongs to a different (baseline/DD) sprint.

---

## 4. Look-and-Feel / Design-System Findings

**Canonical patterns (reuse, do not reinvent):**

| Concern | Pattern / component | Canonical file |
|---|---|---|
| Page layout | `BaseLayout` (PageHeader + PageSidebar + Main) | `components/layout/BaseLayout/BaseLayout.tsx` |
| Page title | `Typography variant="h4"`, `fontWeight:600`, 34px | (theme) |
| Tabs | MUI `Tabs`/`Tab` w/ icons + divider underline | `…/AssetManagementSiteDetails/AssetManagementSiteDetails.tsx`, `…/operations-and-maintenance/pages/SiteDetails/SiteDetails.tsx` |
| Info cards | `InformationCardBase` (+ draggable) | `…/tabs/Overview/components/information-cards/…`, `DraggableLayout.tsx` |
| Dashboard widgets | `WidgetContainer` styled | `…/SiteDetails/tabs/Overview/Overview.style.tsx` |
| Tables | **AG Grid** via `BaseTable` (`ag-theme-quartz`) | `components/common/tables/BaseTable/BaseTable.tsx` |
| Key-value tables | MUI `Table` (small) | `…/information-cards/Ownership/Ownership.tsx` |
| Charts | Chart.js / `react-chartjs-2` | `…/widgets/ActualProduction/ActualProduction.tsx` |
| Chips / badges | MUI `Chip` + theme status colors; `ParsingStatusBadge`, reconciliation `StatusChip`/`StatusCell`, `AlertsIndicator` | `utils/styles/theme.ts`, `components/common/ParsingStatus/…`, `…/Reconciliation/…` |
| Alerts / empty states | MUI `Alert`; `NoDataOverlay` (tables); `MessageOverlay` (widgets) | `components/common/tables/components/NoDataOverlay/…` |
| Loading | `FullPageLoader`, `LoadingComponent`, `CircularProgress` | `components/common/FullPageLoader/…`, `…/LoadingComponent/…` |
| Typography / icons | `Lato`; **MUI Material Icons** exclusively | `utils/styles/theme.ts` |
| Spacing | 8px system via `sx`; headers `mb:24px`, grids `spacing={2}` | (theme) |
| Status palette | `efficiencyColors` (none/low/mediocre/good/outstanding) + status `success/warning/error` | `utils/styles/theme.ts` |
| Indicators | `WeatherIndicator`, `PowerProductionIndicator`, `EfficiencyRateBar` | `components/common/…` |

**Recommendations for V2 enhancements to fit the style:**
- **Reuse, don't replace:** all chart widgets, `BaseTable`, `InformationCardBase`/`WidgetContainer`, `Chip`, `Alert`, `NoDataOverlay`, the reconciliation `StatusCell` chip+caption pattern (it is the house style for "status + blocking level + next action").
- **New missing-dependency indicators must reuse the reconciliation `StatusCell` visual grammar** (status chip + blocking chip + "Next: …" caption + optional tooltip). This already exists and is on-brand; do **not** invent a new badge system.
- **Insert new read-only panels as `Paper`/`WidgetContainer` blocks** within an existing tab's `Grid`, separated by the existing `Divider` rhythm (the OM tab already uses `<Divider sx={{ my: 4 }} />` between sections).
- **Do not introduce a new layout, color ramp, font, or chart library.** Use `efficiencyColors`/status colors + `Chip` for any new state expression.
- **Where Replit must not invent layout:** the OM tab, Telemetry tab, and Reconciliation tab already define the column/divider structure — new content slots into their existing `Grid`/`Divider` scaffolding only.

---

## 5. V2 Alignment Plan by Screen

Disposition codes: **KEEP**, **DATA-SWAP** (replace data source only), **BADGE** (add metadata/status badges), **INDICATOR** (add Path-B missing-dependency indicators), **LINK** (add navigation), **DRILL** (add read-only drill-down), **DEFER**.

| Screen / widget | Disposition | V2-native target | Notes |
|---|---|---|---|
| O&M All Companies list | **KEEP** | rollups (already) | latest power already V2 |
| O&M Company → **Sites table** | **DATA-FILL** | `telemetry_site_interval_rollups` + `telemetry_expected_baselines` (give `extend_company_sites_with_energy_attributes` a V2 source; today it returns honest N/A by default) | Main data opportunity (D1); backend-only, FE shape unchanged — fills currently-N/A energy columns for V2 sites |
| O&M Company → Overview / Losses | **KEEP** | rollups + baselines (already) | |
| Company **Performance** tab (Project Hub) | **KEEP** (+ optional BADGE) | company V2 endpoints | optionally show "expected unavailable" when baselines missing |
| OM tab — Actual Production widget | **KEEP** + **INDICATOR** | `…/actual-production-chart` (V2) | replace single generic Alert gate with granular indicators (§6); fix D6 zero-display |
| OM tab — Past Performance | **KEEP** | V2 past-performance | already honest empty + no-baseline flag |
| OM tab — Actual vs Projected Power | **KEEP** | V2 actual-vs-expected | expected null when no baseline |
| OM tab — Inverters Performance | **KEEP** + **BADGE** | device rollups (neutral tiles) | optionally badge "no per-device baseline" instead of bare neutral; fix D7 seed |
| OM tab — Devices Overview | **KEEP** | devices-overview-section | |
| OM tab — readiness gate | **INDICATOR** | replace `is_data_flowing` boolean Alert with Path-B indicator list | core UX upgrade |
| Telemetry tab | **KEEP** + **DRILL** | eligibility-diagnostics (present), weather readiness (add) | already hosts EligibilityDiagnosticsPanel; add weather provenance panel (§8) |
| Devices tab | **KEEP** + **BADGE** | eligibility diagnostics | optional per-device mappable/driving/semantics chips |
| Reconciliation tab | **KEEP** | facts/baselines (already) | model for indicator UX; no change |
| Site charts backend fabricated-zero | **DATA-SWAP**/cleanup | `None`/N/A (D5) | low-risk backend tidy |

---

## 6. Missing-Dependency Indicator Placement Plan

These reuse existing read-only services — **no new computation, no expected-math change**: `device_eligibility_diagnostics_service` (eligibility/mapping/semantics), `weather_readiness_service` (weather provenance/inputs), and the reconciliation ladder (baseline/fact promotion). All render with the reconciliation `StatusCell` grammar.

| Indicator | Host surface | Suggested label | Short explanation | Recommended action / nav | Blocking level |
|---|---|---|---|---|---|
| Active baseline missing | OM tab (above charts) + Telemetry tab | "No active expected baseline" | Expected/loss can't be computed | "Promote a baseline" → Reconciliation/Telemetry setup | **blocks expected** |
| Draft baseline exists, not active | OM tab / Telemetry | "Draft baseline not activated" | A draft exists but isn't driving expected | "Activate baseline" → Telemetry setup | **blocks expected** |
| Accepted value not promoted | Reconciliation (exists) + surfaced on OM | "Accepted, not promoted" | A DD value is accepted but not in active assumptions | "Promote in Data Room" | **blocks baseline** |
| Design points missing | Telemetry / OM | "Design estimate points missing" | No design-estimate curve to compare | "Generate design points" | lowers confidence |
| Weather profile missing | Telemetry weather panel | "No weather source profile" | No source feeds weather-adjusted expected | "Add/activate weather profile" | **blocks expected** (for weather-adjusted) |
| Weather source unapproved | Telemetry weather panel | "Weather source unapproved" | Imported weather not yet approved | "Approve weather source" | lowers confidence |
| Missing irradiance | Telemetry weather panel | "No irradiance input" | POA/GHI not available | "Map an irradiance sensor" | **blocks expected** (physics) |
| Missing cell/module temperature | Telemetry weather panel | "No module temperature" | Temp correction unavailable | "Map a temperature sensor" | lowers confidence |
| Irradiance plane unknown | Telemetry weather panel | "Irradiance plane unknown" | Plane not declared; no conversion assumed | "Declare plane (POA/GHI…)" | lowers confidence |
| Temperature type unknown | Telemetry weather panel | "Temperature type unknown" | Ambient vs cell not declared | "Declare temperature type" | lowers confidence |
| Calibration unknown/expired | Telemetry weather panel | "Calibration unknown/expired" | Sensor calibration not verified | "Update calibration status" | informational/lowers confidence |
| Device exists but not mapped | Telemetry (EligibilityDiagnosticsPanel — exists) / Devices | "Device not mapped" | Device present, no telemetry mapping | "Map device" → wizard | informational |
| Device mapped, no usable telemetry | Telemetry / Devices | "Mapped, no data" | Mapping exists but no readings | "Check connection/refresh" | **blocks reporting** |
| Metric catalog unsupported | Telemetry | "Metric not in catalog" | Provider field not mapped to a metric | "Extend metric catalog" | lowers confidence |
| Gateway present, children unmapped | Telemetry / Devices | "Gateway children unmapped" | Gateway visible but no mapped child devices | "Map child devices" | informational |
| Meter present, not used for site actual | Telemetry / Devices | "Meter not driving actual" | Meter mappable but doesn't drive site actual | informational only | informational |
| Expected available, weather source unverified | OM tab / Telemetry | "Expected shown — weather unverified" | Expected exists but weather provenance is `legacy_das_unverified` | "Verify weather semantics" | lowers confidence |
| Historical weather imported, not approved | Telemetry weather panel | "Imported weather pending approval" | Backfilled weather awaiting approval | "Approve import" | lowers confidence |

**Primary insertion point:** the **OM tab's existing readiness gate** (currently a single `Alert`) becomes a compact indicator strip/list summarizing the most severe blockers, with a "details" deep-link to the **Telemetry tab** (weather/device/eligibility detail) and **Reconciliation tab** (baseline/fact detail). Detailed per-item indicators live in those existing tabs — **no new page**.

---

## 7. Navigation Findings

The app is mid-migration to a **"Scoped Lens"** navigation pattern: newer **scoped routes** (`/operations-and-maintenance/scope/project/:projectId`, `…/scope/company/:companyId`; `/project-hub/scope/project/:projectId`) coexist with **canonical** (`/project-hub/projects/:siteId`) and **legacy** (`/operations-and-maintenance/companies/:companyId/sites/:siteId`) routes. `DeprecatedRouteRedirect` components in `App.tsx` map legacy `:siteId` routes onto the canonical project routes, so most inconsistency is already mitigated. Net: navigation is **better than first assumed** — the gaps are narrow.

| Finding | Status | Detail | Recommended fix (future sprint, not now) |
|---|---|---|---|
| Two O&M surfaces sharing widgets | Working (intentional) | Standalone module + Project Hub OM tab; `NavMenu` routes "O&M" to the **PH OM tab** (`/project-hub/projects/:projectId/om`) when a project is selected | Keep; optionally document which surface is canonical for which task (portfolio roll-up vs per-site) |
| **Site-level O&M → Project Hub back-link** | ✅ Already works | `…/SiteDetails/handle.ts` `crumbsBuilder` links the site-name breadcrumb back to the PH OM tab via `CANONICAL_ROUTES.PROJECT_HUB_PROJECT_TAB` | No change |
| **Company-level O&M → Project Hub back-link** | ⚠️ Gap | O&M Company Details breadcrumbs link only to the O&M home, **not** to the Project Hub company page | Add a breadcrumb/quick-link to the PH company page using existing `BREADCRUMB_LABELS.PROJECT_HUB` + breadcrumb component |
| Route-param naming inconsistency | Mostly mitigated | Scoped routes use `:projectId`; canonical/legacy use `:siteId`. `DeprecatedRouteRedirect` bridges legacy→canonical | Standardize param naming over time; low priority given redirects |
| **Silent permission redirect (standalone O&M)** | ⚠️ Gap | `operations-and-maintenance/ModuleContainer.tsx` → `<Navigate to="/" replace />` on missing `O&M (Production Monitoring):view`; no explanation | Show an explicit "Access restricted" `Alert` (the **PH Reconciliation tab already does this**) instead of a silent bounce. Note: `NavMenu` *does* disable items with a permission tooltip, so the silent bounce is mainly a direct-URL edge case |
| Deep-link / context preservation | ✅ Works | Both surfaces sync URL → `useEntityContext`; `NavMenu` carries the selected project context across modules; OM tab uses `useFocusHighlight` for focus deep-links | Verify focus deep-links resolve on OM/Telemetry tabs; document any gaps |

All navigation items are **documented only**; no nav changes are implemented in this audit.

---

## 8. Weather / Device Readiness Placement

Using **existing** surfaces only — no standalone weather page (none is warranted; the Telemetry tab already hosts readiness content):

| Content | Host (existing) | How |
|---|---|---|
| Weather provenance (source, profile, effective period, confidence, approval) | **Telemetry tab** — new read-only `Paper` panel below the readiness strip | Reuse `weather_readiness_service` output; render with `StatusCell` chips |
| Weather missing-input reasons (irradiance/temp/plane/type/calibration) | **Telemetry tab** weather panel | indicator list (§6) |
| Semantics verified vs `legacy_das_unverified` | **Telemetry tab** weather panel + optional OM-tab confidence note | chip: verified / unverified |
| Device eligibility diagnostics | **Telemetry tab** — `EligibilityDiagnosticsPanel` (**already present**) | no new surface |
| Mappable but non-driving devices (meters/loggers/gateways) | **Telemetry tab** EligibilityDiagnosticsPanel + optional **Devices tab** chips | "mappable / not driving expected" chip |
| Meter / logger / gateway diagnostics | **Telemetry tab** EligibilityDiagnosticsPanel | indicator rows |
| Weather-capable device semantics (declare plane/type/calibration) | **Telemetry tab** (device row action) | additive declare control (read-only display in this sprint unless declare API is in scope) |
| Calibration status | **Telemetry tab** weather panel | chip (unknown/valid/expired) |

**Single recommended addition:** one **read-only "Weather & Provenance" panel inside the existing Telemetry tab**, mirroring the existing `EligibilityDiagnosticsPanel`. Everything else already has a home.

---

## 9. Testing Plan (for the future implementation sprint)

**Frontend component tests**
- OM tab renders indicator strip from a mocked readiness/diagnostics payload (each blocking level → correct chip/label/next-action).
- ActualProduction renders `—`/`N/A` (not `0`) when source values are `null` (D6 regression).
- Inverters tiles render neutral/"N/A" (not `0`) when no per-device baseline (D7).
- New Telemetry weather panel renders each weather indicator state.
- Reconciliation `StatusCell` reuse unchanged (snapshot guard).

**Route / navigation tests**
- Standalone O&M permission failure shows explicit "Access restricted" (not silent redirect).
- Project Hub OM/Telemetry/Reconciliation deep links preserve `siteId` context.
- Canonical O&M route helper produces correct URLs.

**Backend endpoint tests**
- Company `sites` table returns rollup/baseline-derived energy (D1) and **does not call BigQuery** (grep + mock assert).
- `actual-production-chart` legacy-on BQ-exception returns `None` + `expected_baseline_available:false` (D5), never `0.0`.
- V2-first precedence unchanged: site with rollups never touches BigQuery (existing tests stay green).

**No-mutation tests (read-only panels)**
- Eligibility diagnostics, weather readiness, reconciliation endpoints perform **zero writes/commits** (assert no INSERT/UPDATE; transaction rollback check).

**V2-native data-source tests**
- New/changed endpoints read only `telemetry_site_interval_rollups` / `telemetry_device_interval_rollups` / `telemetry_expected_baselines(_points)` / `project_facts` / weather provenance tables.

**Old-model regression tests**
- Grep guard: no new BigQuery/Firestore imports in O&M routers/services.
- `legacy_telemetry_enabled` default-off path returns honest N/A everywhere.

**Visual / look-and-feel guardrails**
- New panels use `Paper`/`WidgetContainer` + `Chip` + `Divider` (lint/snapshot); no new chart lib or color outside `theme.ts`.

**Site 4 / 110 Shawmut smoke test**
- Load OM + Telemetry + Reconciliation for site 4; confirm charts render from V2, indicators compute, and **no mapping/data is mutated**.

**Permission tests**
- `O&M (Production Monitoring):view`, `Diligence:view`, `telemetry-admin`, company-visibility — each gate enforced; explicit messaging on denial.

---

## 10. Recommended Implementation Sprint Prompt

> **Sprint: O&M V2 Data Alignment (surgical, existing screens only).**
> Modernize the existing O&M screens to V2-native data and add Path-B missing-dependency indicators **without** creating new pages, redesigning O&M, or changing expected math, ingestion, device eligibility, WeatherResolver, baselines, DD parsing, or secrets. No BigQuery/Firestore/legacy reintroduction. Respect the existing Ilios UI (BaseTable/AG Grid, Chart.js, MUI Tabs/Cards/Chips, `theme.ts`, reconciliation `StatusCell` grammar). All new panels insert into existing tabs (OM, Telemetry) as `Paper`/`WidgetContainer` blocks separated by the existing `Divider` rhythm.
>
> **Phase 1 — No-regret navigation (FE only, low risk):** Replace the standalone O&M `ModuleContainer` silent redirect with an explicit "Access restricted" Alert; add a `CANONICAL_ROUTES.OM` helper + breadcrumb cross-links between standalone O&M and the Project Hub project; verify deep-link context. *Tests:* route/nav + permission.
> **Phase 2 — Data-source fill (backend, medium risk):** Give `extend_company_sites_with_energy_attributes` (O&M company sites + investor-dashboard sites) a V2 source from `telemetry_site_interval_rollups` + `telemetry_expected_baselines`. Today it is flag-gated to honest N/A by default (no BigQuery unless the legacy flag is on) but has no V2 fallback, so energy columns are blank even for V2 sites; this phase populates them from Postgres while keeping the response shape identical. Fix residual fabricated zeros (D5 backend, D6/D7 frontend) to honest `null`/N/A. *Tests:* backend endpoint + no-BigQuery grep + zero-display regression. *Must not change:* V2-first precedence, response schemas.
> **Phase 3 — Missing-dependency indicators (FE, medium):** Replace the OM tab's single `is_data_flowing` Alert with a Path-B indicator strip sourced from existing readiness/eligibility/weather-readiness/reconciliation services; deep-link details to Telemetry + Reconciliation tabs. Reuse `StatusCell`. *Tests:* per-blocking-level rendering. *Backend:* none (read-only services exist).
> **Phase 4 — Weather provenance panel (FE, low):** Add one read-only "Weather & Provenance" panel in the existing Telemetry tab (mirror `EligibilityDiagnosticsPanel`) showing source/profile/approval/semantics/calibration + missing-input indicators. *Backend:* none.
> **Phase 5 — Device diagnostics surfacing (FE, low):** Surface mappable-but-not-driving meters/loggers/gateways and weather-device semantics via the existing EligibilityDiagnosticsPanel + optional Devices-tab chips. *Backend:* none.
> **Phase 6 (defer):** Reporting/export of V2 performance + baseline lifecycle (facts→draft→active) and SAFL retirement — **separate sprint**.
>
> *Done when:* O&M company/investor sites tables read V2 (no BigQuery); no fabricated zeros; OM tab shows granular Path-B indicators; Telemetry tab shows weather provenance + device diagnostics; navigation explicit & consistent; site 4 intact; all new + existing telemetry/weather tests pass; backend boots clean; FE builds; architect ok.

**Suggested sequencing / risk table**

| Phase | Risk | Files likely touched | Backend? | FE? | Must not change |
|---|---|---|---|---|---|
| 1 Nav | Low | `ModuleContainer.tsx`, `utils/breadcrumbs.ts`, breadcrumb component | No | Yes | routes' meaning, permissions |
| 2 Data-swap | Medium | `helpers/.../extend_company_sites_with_energy_attributes`, `om/companies.py`, `investor_dashboard/sites.py`, `om/sites.py` (D5), `ActualProduction.tsx` (D6) | Yes | Yes | response schemas, V2-first precedence, expected math |
| 3 Indicators | Medium | `tabs/OM/OM.tsx`, new indicator component (reuse StatusCell) | No | Yes | reconciliation service, layouts |
| 4 Weather panel | Low | `tabs/Telemetry/Telemetry.tsx`, new panel | No | Yes | WeatherResolver, import |
| 5 Device diag | Low | `EligibilityDiagnosticsPanel`, Devices tab | No | Yes | eligibility classifier, drives_expected |
| 6 Reporting/baseline | Deferred | — | — | — | — |

---

## 11. Risks and Non-Goals

**Risks**
- **Data-swap shape drift (D1):** replacing the BigQuery sites-table helper must preserve the exact response schema or it breaks both the O&M company Sites tab and the Investor Dashboard. Mitigate with contract tests and identical field names.
- **Shared-widget blast radius:** the Project Hub OM tab imports widgets from the standalone module; a single widget edit changes both surfaces — regression-test both.
- **Indicator overload:** surfacing all J-list indicators at once can overwhelm; show a summarized most-severe strip on OM, full detail in Telemetry/Reconciliation.
- **Permission nuance:** weather/eligibility detail is telemetry-admin + company-visibility gated; ensure non-admins still see read-only summaries without errors.
- **Legacy flag interplay:** any cleanup of D5 must keep behavior identical when `legacy_telemetry_enabled` is off (already honest N/A) and only change the on+exception branch.

**Non-Goals (explicitly out of scope)**
- No new screens/routes/pages; no O&M redesign; no new layout/color/font/chart library.
- No change to expected calculation math, telemetry ingestion, device eligibility (`drives_expected` frozen to `{inverter, module, weather_station}`), WeatherResolver source priority, or historical weather import.
- No new external weather providers; no plaintext secret handling.
- No reintroduction of BigQuery/Firestore/legacy telemetry; the legacy fallback stays gated and off.
- No baseline lifecycle changes, SAFL retirement, or DD parsing changes (separate sprint).
- No data model / migration changes in this alignment work beyond what each phase's surgical data-swap strictly requires (Phase 2 is read-path only — no schema change).

---

*End of audit. This document is advisory; implementation is deferred to the sprint defined in §10.*
