---
name: V2 sites-table energy fill alignment
description: How the company/investor sites-table per-site energy attrs (actual/expected/cumulative) are filled from V2 PostgreSQL, and why the cumulative is stricter than the single-site dashboard.
---

# V2 sites-table energy fill — interval alignment rules

The company `/{id}/sites` and investor `/sites` tables fill 5 per-site energy attrs
(`actual_kw`, `expected_kw`, `cumulative_vs_expected`, `cumulative_7/30_days_vs_expected`)
from V2-native PostgreSQL rollups + baselines when the legacy flag is OFF
(legacy-ON keeps the BigQuery path untouched). 7d/30d stay honest `None` (no defensible
batched V2 multi-day expected exists).

## The rule
- `actual_kw` = the site's **latest TODAY** power bucket (never a prior day), so it is
  always aligned to today's `expected_kw`.
- `expected_kw` anchors to the expected power at the **same bucket as the latest ACTUAL
  power bucket** (`max(power_map)`), and only when that computed bucket is `ok` (strict,
  no cross-bucket borrowing) — NOT the power∪weather union's latest bucket.
- `cumulative_vs_expected` (today %) sums actual AND expected over only the **comparable
  set**: buckets that are `ok` AND have an actual power reading. `None` when no comparable
  bucket exists; a genuine 0 (real coverage, 0 production) stays `0`.

## **Why**
A bucket is `ok` when pto-valid + irradiance + cell_temp are present — it does NOT require
actual power, so an `ok` bucket can be weather-only and LATER than the latest actual power
bucket. Anchoring `expected_kw` to the union-latest bucket compared today's actual against
a later weather-only interval → mismatched intervals (architect FAIL). Anchoring to the
latest actual bucket + summing cumulative over the comparable set makes both sides
like-for-like over the same actual-covered intervals.

## Divergence from the single-site dashboard (intentional)
The instantaneous `expected_kw` uses the SAME strict alignment as the dashboard's
`_expected_power_for_bucket`, so the cell matches the drill-down. But the table's cumulative
today % is **intentionally stricter** than the dashboard: the dashboard
(`apply_v2_actual_production`) sums expected over ALL `ok` buckets vs actual over ALL power
buckets, which can differ in gappy data. The table has no `expected_state`/coverage caption
to explain a partial-day approximation, so it deliberately reports a like-for-like ratio
over actual-covered intervals only.

**How to apply:** Do NOT "fix" the table to match the dashboard by loosening to all-`ok`
expected sums or by anchoring `expected_kw` to the union-latest bucket — that reintroduces
the interval-mismatch bug. If product needs exact table↔drilldown parity, tighten the
dashboard or expose coverage metadata on both, never loosen the table.

The 3 carrier fields on `SiteExpectedToday` (`expected_power_at_latest_actual_kw`,
`comparable_actual_energy_kwh`, `comparable_expected_energy_kwh`) are additive and consumed
ONLY by this table fill; the company aggregate still uses the original union-latest
`expected_power_latest_kw` and is unchanged.
