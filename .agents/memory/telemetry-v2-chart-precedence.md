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

## Known visualization gap (not a bug)
V2 carries **actual telemetry only** (AC power, irradiance, cell temperature). There is **no projected/"expected" baseline metric and no daily rollup** in V2.
Consequences for V2-driven sites:
- The "Expected" line on actual-vs-expected is intentionally `None` (AG line series skips null y-values).
- `expected_kw` / `cumulative_expected_kw` are set to `0.0` (not None) on the actual-production response — `round_to_scale_2` has no None-guard, and `calculate_actual_vs_expected` treats 0 as "no comparison" (returns 0%) rather than dividing by zero.
- past-performance and inverters-performance charts have **no V2 equivalent** and stay BigQuery-backed.

**How to apply:** If asked "why isn't the Expected/projected line showing for a V2 site?" — that's the expected gap, not a regression. Restoring it requires a real expected/baseline metric in V2 (new ingestion + catalog work), not a chart fix.

## Readiness gate must use the SAME V2 predicate as the charts
The telemetry readiness `is_data_flowing` flag originally derived ONLY from BigQuery `get_device_last_reported`, so V2-ingested sites (PostgreSQL rollups, no BigQuery) always read as "not flowing". This silently hid the Project Hub O&M Performance Dashboard, because its render gate is `is_connected && is_site_mapped && is_data_flowing` — the charts never even mounted, so their endpoints were never called. The same flag also drives the Telemetry tab "Data Flowing" chip.
Fix: in `get_site_telemetry_readiness` add a V2 fallback that sets `is_data_flowing=True` when `site_has_v2_rollups(db_session, site.id)` — reusing the EXACT predicate the chart endpoints use for V2-vs-BigQuery precedence. Guard with `if not is_data_flowing` so it only flips False→True, never overrides a BigQuery-true result.
**Why:** if the readiness gate and the chart precedence switch use different conditions, the gate can hide charts that would actually render (or vice versa). Tying both to `site_has_v2_rollups` makes them provably consistent. `has_rollups` (any rollup ever) is the right choice, not a recency bound: the legacy BigQuery check treats ANY last-report as "flowing" (no recency bound), so V2 is at parity; freshness is surfaced separately via the health strip + "Data as of" captions.
**How to apply:** any new render/visibility gate keyed on telemetry data existence must reuse `site_has_v2_rollups`, not invent its own check, or it will desync from the charts for V2 sites.

## Telemetry read endpoints must coerce tz-aware timestamps
Any V2 telemetry read endpoint accepting `from`/`to` query datetimes must normalize them to UTC-naive (the storage convention) before comparing against `datetime.utcnow()` or the naive `bucket_start` column.
**Why:** storage is UTC-naive; a client passing standard ISO "...Z" (tz-aware) compared against a naive datetime raises TypeError → HTTP 500, and aware values can mis-window. The refresh/backfill endpoints already coerce; new series endpoints initially forgot and 500'd on ISO-Z input.
**How to apply:** coerce inside the shared window/clamp helper so every series endpoint benefits at once.
