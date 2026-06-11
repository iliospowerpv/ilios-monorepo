---
name: Telemetry V2 chart precedence & gaps
description: How O&M performance charts pick V2 rollups vs BigQuery, and why the "Expected" line is missing for V2 sites.
---

# O&M chart data source: V2 rollups vs BigQuery

The O&M performance charts use V2-first precedence: **V2 PostgreSQL rollups → BigQuery → empty**.
A site is treated as "V2 available" when it has ANY V2 rollups (a window-agnostic EXISTS check), not per-window.
When V2 is available the chart renders entirely from V2 and never falls back to (possibly stale) BigQuery.
All BigQuery calls in the chart path are wrapped try/except → graceful-empty, so BigQuery being down can never 500 the charts.

**Why:** V2 ingestion replaced the legacy GCP/BigQuery pull, but BigQuery data still exists for older sites. Precedence keeps newly-ingested sites (e.g. site 4 / 110 Shawmut) showing live data without removing BigQuery support.

## V2 has no expected baseline — show honest "N/A", never fabricate
V2 carries **actual telemetry only** (AC power, irradiance, cell temperature). There is **no projected/"expected" baseline metric and no daily rollup** in V2. Phase 1 makes every chart state honest instead of fabricating zeros.

Contract + behavior for V2-driven sites:
- A boolean `expected_baseline_available` flag is added to the actual-production, actual-vs-expected, and past-performance responses. It is `True` on every BigQuery / non-V2 path (including the try/except fallbacks) and `False` only behind `site_has_v2_rollups`. The FE defaults it `?? true`, so non-V2 rendering is untouched.
- `expected_kw` / `cumulative_expected_kw` are `None` (NOT 0.0) for V2; `round_to_scale_2` is now None-safe. FE shows "N/A" / "Baseline not available" + a neutral ring when the flag is False.
- The "Expected" line on actual-vs-expected is hidden for V2 (`visible`/`showInLegend=false`) with an explanatory caption; the AG line series also skips null y-values.
- past-performance returns `{}` data for V2 (FE shows a no-baseline message).
- V2 inverter tiles have a builder (`build_v2_inverter_tiles`): real actual kW (incl a legit `0.0`) with a **neutral** `performance="N/A"` status (no green/red, since there's no baseline). "Mapped" is keyed on `telemetry_mapping` (NOT `das_connection_active`) to stay consistent with the V2 not-responding logic and correct for V2 sites whose legacy DAS status isn't "connected".
- not-responding for V2 is derived from raw-reading recency (`settings.device_no_respond_threshold`, `total_seconds()`); a mapped telemetry-category device with zero readings counts as not responding.

**Why:** the dashboard previously fabricated 0% / 0-expected for V2 sites, which read as "underperforming" when there is simply no baseline to compare against. Honest N/A states avoid false negatives; never invent/derive an expected value.

**How to apply:** any new V2 chart/tile must surface actuals + honest N/A, gate "mapped" on `telemetry_mapping`, and never emit a non-null expected for V2. Restoring a real Expected line requires a genuine baseline metric in V2 (new ingestion + catalog work), not a chart fix.

## App-facing telemetry is V2-ONLY; BigQuery is a legacy-only fallback
The production-hardening cutover made BOTH `get_site_telemetry_health` and `get_site_telemetry_readiness` V2-only: when a site is "V2-backed" they resolve entirely from PostgreSQL and **never construct/call BigQuery**. BigQuery is consulted ONLY for legacy (non-V2) sites that have no native signal at all.
- "V2-backed" = `TelemetryReadingCRUD.latest_metric_ts(site_id) is not None` **OR** `site_has_v2_rollups(...)`. Use readings-OR-rollups in BOTH endpoints (health and readiness) so a site whose first ingestion landed readings but whose rollup hasn't run yet still skips BigQuery. (The O&M charts still gate on `site_has_v2_rollups` alone — health/readiness are intentionally broader because readings-from-PostgreSQL are strictly fresher; the rollups-only-no-readings direction is safe → explicit `no_data`.)
- Health `last_data_at` for a V2 site IS the latest native reading (naive-UTC → coerce to UTC); status uses the unchanged 30/120-min delay thresholds; `no_data` is an explicit state, never a hidden fabrication.
**Why:** BigQuery is no longer an app dependency. Any BigQuery read on a V2 path means a BQ outage or stale BQ data could make a live V2 site look broken/healthier/staler — exactly what the cutover removes. Charts, readiness, and health must all agree.
**How to apply:** any NEW telemetry visibility/health/"has data" gate must use the readings-OR-rollups V2-backed predicate (or `site_has_v2_rollups` for chart-precedence parity) and must NOT add a BigQuery read on a V2 path. Legacy BQ branches are scheduled for removal in a later phase (replace-first now, delete later).

## Company / investor / portfolio actual-production aggregation is V2-only
The V2-only cutover extends from per-site charts to the COMPANY, INVESTOR, and PORTFOLIO aggregation paths. Company/investor "actual production" (latest power + today energy) is aggregated directly from `telemetry_site_interval_rollups` (rollups carry both `company_id` and `site_id`) via `helpers/telemetry/v2_company_data.py` — never BigQuery. Latest power = DISTINCT ON per site (one query); today energy = Σ(avg_kw × bucket_hours) over each site's LOCAL day window (use `_site_local_day_start_utc`; sites can span timezones); company total = Σ over its accessible sites. Empty/unmapped sites contribute 0 (absent from the latest-power map); an empty company renders clean.
- expected/loss are `None` (NOT 0, NOT derived from actual). `expected_baseline_available` is mirrored at COMPANY level: schema default `True` so any non-V2/legacy response is untouched, `False` on the V2 aggregation path. FE shows "N/A"/"Baseline not available" + neutral marker. The numeric percent fields collapse to 0% when expected is None — **FE must gate on the flag, not the 0**.
- Investor = per-company aggregation across that company's sites; there is no formal Portfolio entity (`portfolio_hub_id` unset everywhere).
- ONE intentional BigQuery holdout remains on a non-actual path: `extend_company_sites_with_energy_attributes` (backs the `/{company_id}/sites` table) still reads `TelemetrySiteBigQuery`, deferred to a later phase. Don't mistake it for leakage.

**Why:** same as the chart cutover — a BQ outage or stale BQ must never make a live company look broken, and an expected baseline must never be invented. **How to apply:** any new company/portfolio "actuals" path uses `aggregate_company_actuals`; restoring expected/loss needs a real V2 baseline metric (future sprint), not a derived value.

## "Expected interval" on the Data Health card is scheduler-derived (not hardcoded)
`TelemetryHealthResponse` exposes `expected_interval_minutes: Optional[int]` + `expected_interval_label: str`; the FE renders the label. The label comes from `_resolve_expected_interval(db, site_id)`: resolve the site's CURRENT account (`resolve_current_account`) → `TelemetrySchedulerStateCRUD.get_by_site_account` → cadence via `CADENCE_TO_SECONDS`. Missing row → "Not scheduled"; row disabled → "Manual refresh only"; enabled → "{n} min".
**Why:** the old card showed a hardcoded "15 min" that lied whenever the scheduler cadence differed or was off. Reading the live scheduler row makes a cadence change reflect with no code change.
**How to apply:** never reintroduce a constant interval; derive from the scheduler row. The not_configured early-return skips the lookup and returns ("Not scheduled", None) directly (an unconfigured site has no account/row anyway).

## Telemetry read endpoints must coerce tz-aware timestamps
Any V2 telemetry read endpoint accepting `from`/`to` query datetimes must normalize them to UTC-naive (the storage convention) before comparing against `datetime.utcnow()` or the naive `bucket_start` column.
**Why:** storage is UTC-naive; a client passing standard ISO "...Z" (tz-aware) compared against a naive datetime raises TypeError → HTTP 500, and aware values can mis-window. The refresh/backfill endpoints already coerce; new series endpoints initially forgot and 500'd on ISO-Z input.
**How to apply:** coerce inside the shared window/clamp helper so every series endpoint benefits at once.
