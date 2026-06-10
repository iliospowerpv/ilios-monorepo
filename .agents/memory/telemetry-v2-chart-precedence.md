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

## Telemetry read endpoints must coerce tz-aware timestamps
Any V2 telemetry read endpoint accepting `from`/`to` query datetimes must normalize them to UTC-naive (the storage convention) before comparing against `datetime.utcnow()` or the naive `bucket_start` column.
**Why:** storage is UTC-naive; a client passing standard ISO "...Z" (tz-aware) compared against a naive datetime raises TypeError → HTTP 500, and aware values can mis-window. The refresh/backfill endpoints already coerce; new series endpoints initially forgot and 500'd on ISO-Z input.
**How to apply:** coerce inside the shared window/clamp helper so every series endpoint benefits at once.
