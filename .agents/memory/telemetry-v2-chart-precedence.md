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

## Readiness gate must use the SAME V2 predicate as the charts
The telemetry readiness `is_data_flowing` flag originally derived ONLY from BigQuery `get_device_last_reported`, so V2-ingested sites (PostgreSQL rollups, no BigQuery) always read as "not flowing". This silently hid the Project Hub O&M Performance Dashboard, because its render gate is `is_connected && is_site_mapped && is_data_flowing` — the charts never even mounted, so their endpoints were never called. The same flag also drives the Telemetry tab "Data Flowing" chip.
Fix: in `get_site_telemetry_readiness` add a V2 fallback that sets `is_data_flowing=True` when `site_has_v2_rollups(db_session, site.id)` — reusing the EXACT predicate the chart endpoints use for V2-vs-BigQuery precedence. Guard with `if not is_data_flowing` so it only flips False→True, never overrides a BigQuery-true result.
**Why:** if the readiness gate and the chart precedence switch use different conditions, the gate can hide charts that would actually render (or vice versa). Tying both to `site_has_v2_rollups` makes them provably consistent. `has_rollups` (any rollup ever) is the right choice, not a recency bound: the legacy BigQuery check treats ANY last-report as "flowing" (no recency bound), so V2 is at parity; freshness is surfaced separately via the health strip + "Data as of" captions.
**How to apply:** any new render/visibility gate keyed on telemetry data existence must reuse `site_has_v2_rollups`, not invent its own check, or it will desync from the charts for V2 sites.

## "Data Health" last-data must also read V2 readings (not BigQuery-only)
`get_site_telemetry_health` originally computed `last_data_at`/status ONLY from BigQuery `get_device_last_reported`, so V2/demo sites (readings in PostgreSQL, BigQuery bypassed) showed "No Data Yet / Last data: Never" even while the scheduler was actively writing readings.
Fix: read the newest native reading first via `TelemetryReadingCRUD.latest_metric_ts(site_id)` (naive-UTC → coerce to UTC), then merge BigQuery so BQ can only make it FRESHER; a BigQuery failure no longer blanks a V2-backed card (surface the error only when there is no native signal).
**Why:** health was the last BigQuery-only read surface — the charts and the readiness gate were already V2-aware, so the Data Health card disagreed with the charts (card said "Never" while charts rendered live data).
**How to apply:** treat health like the charts/readiness — V2-first then BigQuery; never let a BigQuery-only path decide "has data" for a native/demo site. Note the card's "Expected interval: 15 min" is a hardcoded label, NOT derived from the scheduler cadence.

## Telemetry read endpoints must coerce tz-aware timestamps
Any V2 telemetry read endpoint accepting `from`/`to` query datetimes must normalize them to UTC-naive (the storage convention) before comparing against `datetime.utcnow()` or the naive `bucket_start` column.
**Why:** storage is UTC-naive; a client passing standard ISO "...Z" (tz-aware) compared against a naive datetime raises TypeError → HTTP 500, and aware values can mis-window. The refresh/backfill endpoints already coerce; new series endpoints initially forgot and 500'd on ISO-Z input.
**How to apply:** coerce inside the shared window/clamp helper so every series endpoint benefits at once.
