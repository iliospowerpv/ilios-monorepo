# V2 Actual Production Curve Integrity — Telemetry → O&M Chart Trace

**Audit site:** Site 4 / “110 Shawmut” / company 6
**Audit window:** O&M *Actual vs Expected* line chart, default 7‑day hourly window (the chart on which the flat line is reported)
**Audit date:** 2026‑06‑21
**Scope:** AUDIT ONLY. No code, migration, endpoint, UI, data‑repair, rollup, or provider change was made. Every query and script run for this audit was strictly read‑only.

> **Durable telemetry invariant (restated):** Actual production shown in iliOS must be traceable to V2 raw readings and V2 rollups, with metric semantics, interval boundaries, units, timezone, and aggregation method explicitly identified. This audit confirms that invariant **holds** for Site 4 actuals.

---

## 1. Executive summary

**The “flat actual line” is real on screen, but it is NOT an actual‑telemetry defect.** Site 4’s actual production data is healthy and fully traceable end‑to‑end:

- Raw V2 readings (`telemetry_readings`, provider metric `KW` → normalized `site_power_ac_kw`) vary correctly: ~300+ kW at midday, ~‑0.06 kW (parasitic tare) overnight.
- V2 hourly rollups (`telemetry_site_interval_rollups`, `agg=avg`, `1h`) trace a textbook solar curve (≈0 → 292 kW → 0 across a local day).
- The backend chart‑builder reads exactly that series for the **actual** line and emits it correctly.

The flat appearance is a **rendering side‑effect of the EXPECTED series**, not the actual series. The 7‑day window straddles the baseline supersede boundary (2026‑06‑20 16:33:48). The historical portion of the window (June 14–20) is computed **period‑effectively from the superseded baseline #3**, which is physically invalid (`thermal_coefficient_pct = 350`, i.e. 3.5 /°C instead of −0.35 %/°C). With Site‑4 cell temperatures always below the 25 °C reference, that coefficient drives the temperature factor strongly negative, and because the expected formula has **no lower clip** (only an upper `min(expected, AC nameplate)`), expected power for those buckets collapses to large negative values.

**Measured, on the live read path (read‑only run of the production chart‑builder):**

| Series | min | max |
|---|---:|---:|
| **actual** (kW) | −0.07 | **306.76** |
| **expected** (kW) | **−39,368.59** | 462.00 |

Of 168 hourly points, **144 come from invalid baseline #3** (`baseline_id` counts `{3: 144, 4: 24}`). The chart’s shared Y‑axis must therefore span roughly **−39,369 … +462 kW**; the genuine 0–307 kW actual curve is compressed into < 1 % of the axis height and reads as a flat line near the top.

**Root cause (single, precise):** a *baseline‑validation gap* in period‑effective expected stitching. `build_actual_vs_expected_section` validates only the **current active** baseline on read; `compute_site_expected_period_effective` then computes **superseded** baselines for historical buckets **without** the same fail‑closed physics validation. This is exactly the non‑blocking caveat flagged when the baseline‑physics‑validation feature shipped (“historical period‑effective stitching validates only the current active baseline; a superseded‑but‑invalid baseline in the window could still compute”). It has now manifested in production for Site 4.

**Nothing in the actual pipeline needs repair, and no backfill is required.** Expected is computed on read, so once invalid segments are validated/suppressed on read (same policy already applied to the active baseline), the chart self‑heals with no data mutation.

---

## 2. Exact chart and endpoint traced (Audit A)

| Aspect | Finding |
|---|---|
| Route / page | O&M Site Details → Overview: `/operations-and-maintenance/sites/:siteId` (also surfaced in Project Hub site views) |
| Chart component | `ActualProjectedPower.tsx` (line chart) — `frontend/rea-investment-fe/src/modules/operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/ActualProjectedPower/ActualProjectedPower.tsx` |
| Chart library | `AgChartsReact` from `ag-charts-react`; x‑axis `type: 'time'`, two line series (`actual`, `expected`) sharing one Y‑axis, joined on `xKey: 'period'` |
| API endpoint | `GET /api/operations-and-maintenance/sites/{site_id}/actual-vs-expected-chart` |
| Request params | `site_id` (path) only. Window, granularity, metric, and timezone are all decided **server‑side** (the FE sends none). |
| Backend handler | `get_site_actual_vs_expected_chart` → `app/routers/operations_and_maintenance/sites.py` (line ~245) → `build_actual_vs_expected_section` in `app/helpers/telemetry/v2_chart_data.py` |
| Window / granularity | Server‑fixed: `end = utcnow()`, `start = end − 7 days`; bucket `CHART_BUCKET_SIZE = "1h"` |
| Metric selection | Server‑fixed: actual = `site_power_ac_kw`; overlay = `irradiance_wm2`; expected = period‑effective WAM baseline calc |
| What is plotted | **Interval‑average instantaneous AC power (kW)** per hour for *actual*; modeled instantaneous AC power (kW) for *expected*. Not energy, not cumulative, not daily. |
| Gap / fill behavior (FE) | None. The FE passes `actual`/`expected` through as‑is; AG Charts skips `null`. No `\|\| 0`, no forward‑fill, no LOCF on the **line** series. |

**Companion surfaces confirmed (not the reported chart, but verified consistent):**
- Doughnut summary `ActualProduction.tsx` → `GET .../actual-production-chart` → `apply_v2_actual_production`. This path uses **only the current active baseline** and is therefore *not* affected by the invalid superseded baseline; its actuals are correct.
- `GET .../past-performance-chart` → `build_past_performance_section`. Same period‑effective stitching → **same latent defect** for the daily % chart (see §10).

---

## 3. Provider raw telemetry sample (Audit B)

`telemetry_readings` is the V2 native raw store (the faithful, as‑ingested provider values; no BigQuery/Firestore involved). Site‑level production arrives as provider metric **`KW`** from external device `127726`, normalized to `site_power_ac_kw`, unit **kW**, sampled roughly every 3–4 minutes. Provider semantics: **instantaneous AC power**, not energy and not a cumulative counter.

**Representative day 2026‑06‑15 — DAYTIME (local ≈13:00 EDT):**

| UTC ts | Local ts (America/New_York) | provider_metric | value | unit | ext. device |
|---|---|---|---:|---|---|
| 2026‑06‑15 17:00:59 | 2026‑06‑15 13:00:59 | KW | 316.312 | kW | 127726 |
| 2026‑06‑15 17:04:20 | 2026‑06‑15 13:04:20 | KW | 297.923 | kW | 127726 |
| 2026‑06‑15 17:07:39 | 2026‑06‑15 13:07:39 | KW | 324.181 | kW | 127726 |
| 2026‑06‑15 17:11:03 | 2026‑06‑15 13:11:03 | KW | 323.212 | kW | 127726 |
| 2026‑06‑15 17:14:19 | 2026‑06‑15 13:14:19 | KW | 324.057 | kW | 127726 |

**Representative day 2026‑06‑15 — NIGHT (local ≈02:00 EDT):**

| UTC ts | Local ts | provider_metric | value | unit |
|---|---|---|---:|---|
| 2026‑06‑15 06:01:10 | 2026‑06‑15 02:01:10 | KW | −0.0644 | kW |
| 2026‑06‑15 06:04:29 | 2026‑06‑15 02:04:29 | KW | −0.0632 | kW |
| 2026‑06‑15 06:07:50 | 2026‑06‑15 02:07:50 | KW | −0.0601 | kW |
| 2026‑06‑15 06:11:10 | 2026‑06‑15 02:11:10 | KW | −0.0674 | kW |

**Reading:** Daytime values vary by interval (~298–324 kW); nighttime values are a small **genuine** negative tare (≈ −0.06 kW, parasitic/sensor offset), correctly preserved (not zeroed, not nulled). Provider data is **not** flat. Whole‑site readings inventory: 16,829 rows, range −0.221 … 394.904 kW, 2026‑05‑11 → 2026‑06‑21.

---

## 4. Normalized V2 reading sample (Audit C)

Normalization is a 1:1 identity here — same value, same unit, same timestamp — only the metric key is normalized:

| provider_metric | normalized_metric | unit | rows | range |
|---|---|---|---:|---|
| `KW` | `site_power_ac_kw` | kW | 16,829 | −0.221 … 394.904 |
| `KwAC` | `device_power_ac_kw` | kW | 65,085 | 0.0 … 67.171 |
| `Sun` | `irradiance_wm2` | W/m² | 16,819 | 0.0 … 1386.9 |
| `Temp1` | `cell_temperature_f` | °F | 16,819 | −3.9 … 70.3 |

- `metric_ts` is stored **naive‑UTC** (the daytime/night samples above match real solar hours once shown in site‑local time → no shifting).
- Values remain variable; **no duplication and no carry‑forward** observed. There is no last‑value/LOCF behavior at the reading layer.
- `cell_temperature_f` is stored in **Fahrenheit** (critical for §6).

---

## 5. Interval‑rollup sample (Audit D)

`telemetry_site_interval_rollups`, `normalized_metric = site_power_ac_kw`, `bucket_size = 1h`, `agg = avg`. Representative **local** day 2026‑06‑15 (America/New_York; local midnight = 04:00 UTC):

| Local bucket | UTC bucket | site_power_kw | sample_count | completeness |
|---|---|---:|---:|---:|
| 00:00 | 04:00 | −0.063 | 18 | 1.00 |
| 02:00 | 06:00 | −0.065 | 18 | 1.00 |
| 05:00 | 09:00 | 1.402 | 18 | 1.00 |
| 06:00 | 10:00 | 16.881 | 18 | 1.00 |
| 07:00 | 11:00 | 74.534 | 18 | 1.00 |
| 08:00 | 12:00 | 109.935 | 18 | 1.00 |
| 11:00 | 15:00 | 214.869 | 18 | 1.00 |
| 12:00 | 16:00 | 244.938 | 18 | 1.00 |
| **13:00** | 17:00 | **291.981** | 18 | 1.00 |
| 15:00 | 19:00 | 250.660 | 18 | 1.00 |
| 17:00 | 21:00 | 119.300 | 18 | 1.00 |
| 19:00 | 23:00 | 38.577 | 18 | 1.00 |
| 20:00 | 00:00(+1) | 1.162 | 18 | 1.00 |
| 22:00 | 02:00(+1) | −0.068 | 18 | 1.00 |

**Aggregation choice is correct.** Power is an *instantaneous* quantity; averaging ~18 sub‑readings per hour yields interval‑average kW — the right semantics for a power curve. Rollup inventory (site 4):

| metric | bucket | agg | unit | rows | min | max | avg |
|---|---|---|---|---:|---:|---:|---:|
| `site_power_ac_kw` | 1h | avg | kW | 939 | −0.074 | 390.696 | 102.84 |
| `device_power_ac_kw` | 1h | avg | kW | 652 | 0.0 | 65.841 | 24.90 |
| `irradiance_wm2` | 1h | avg | W/m² | 939 | 0.0 | 1028.2 | 247.81 |
| `cell_temperature_f` | 1h | avg | °F | 939 | −3.70 | 65.93 | 23.97 |

Device rollup spot‑check (inverter `311`, local 13:00) = **59.52 kW** (~near its 66 kW nameplate). Nighttime device buckets are simply **absent** (honest), while the site bucket carries the small parasitic tare.

**Conclusion (D):** Rollups vary correctly through day/night, nighttime is correctly ≈0, no daily value is copied across intraday buckets, no cumulative counter is involved. The rollup layer is healthy.

---

## 6. Metric‑semantics analysis (Audit E)

| Candidate metric | Provider | Normalized | Unit | Behavior | Correct agg | Chart usage | Used correctly today? |
|---|---|---|---|---|---|---|---|
| Instantaneous site AC power | `KW` | `site_power_ac_kw` | kW | variable | avg (per interval) | **actual line** | ✅ Yes |
| Per‑inverter AC power | `KwAC` | `device_power_ac_kw` | kW | variable | avg | inverter tiles / device card | ✅ Yes |
| Irradiance | `Sun` | `irradiance_wm2` | W/m² | variable | avg | expected‑model input + overlay | ✅ Yes |
| Cell temperature | `Temp1` | `cell_temperature_f` | **°F** | variable | avg | expected‑model input | ✅ stored °F, converted once in formula |

**No cumulative‑energy metric is being rendered as power, and no metric is copied across buckets.** The chart correctly plots interval‑average instantaneous power. The only semantics subtlety is temperature **units**: readings are Fahrenheit; the expected formula performs the single canonical `°F → °C` conversion (`(°F − 32)/1.8`) and applies the %/°C coefficient against the 25 °C STC reference. That conversion is correct in code. The defect is **not** the conversion — it is the **coefficient value** stored on baseline #3 (see §8/§11).

---

## 7. Timezone / daylight audit (Audit F)

| Layer | Timezone behavior | Correct? |
|---|---|---|
| Provider timestamp | delivered/stored as naive‑UTC | ✅ |
| Raw reading `metric_ts` | naive‑UTC | ✅ |
| DB storage | naive‑UTC (no tz column on readings/rollups) | ✅ |
| Rollup `bucket_start` | naive‑UTC, epoch‑anchored | ✅ |
| Site timezone | `sites.timezone = America/New_York` (IANA) | ✅ |
| “Today” boundary | `_site_local_day_start_utc` converts site‑local midnight → naive‑UTC for the rollup query | ✅ |
| Daily grouping (past‑performance) | `_site_local_date(ts, tz)` groups buckets by **site‑local** date | ✅ |
| FE request tz | none sent (server decides) | n/a |
| FE display tz | `parseUtc` (append `Z`) then render in the **viewer’s browser** locale | ✅ (documented app‑wide convention) |

**Answers to the required timezone questions:**
- Local overnight is represented correctly (local 00:00–04:00 ≈ −0.06 kW; see §5).
- UTC→local conversion is **not** shifting data into wrong hours (raw 17:00 UTC = 13:00 EDT lands at solar midday, as expected).
- Buckets are grouped by **site‑local** date where date grouping matters (today boundary, daily past‑performance) — **not** by UTC date.
- DST: the audit window is entirely within EDT (UTC‑4); no DST transition occurs in it, so DST does not affect this chart path. (General DST correctness is delegated to `zoneinfo`, which is DST‑aware.)

**Timezone is not a contributor to the flat line.** One cosmetic note: because the line chart displays in the *viewer’s* browser timezone (not necessarily site‑local), a viewer outside America/New_York will see the curve’s clock labels shifted — this is the documented app‑wide convention and is unrelated to the flat line.

---

## 8. Backend chart‑builder audit (Audit, file‑level)

`build_actual_vs_expected_section` (`app/helpers/telemetry/v2_chart_data.py`):

1. `end = utcnow()`, `start = end − 7d`.
2. Validates the **active** baseline on read (`_evaluate_active_baseline`). For Site 4 the active baseline is **#4 (valid)** → `is_blocking = False`, so the builder proceeds (it does **not** enter the `baseline_invalid` short‑circuit).
3. Calls `compute_site_expected_period_effective(start, end)`.
   - `get_baselines_effective_in_window` returns **both** #3 (active_from 2026‑05‑11 → active_to 2026‑06‑20 16:33:48) and #4 (active_from 2026‑06‑20 16:33:48 → open).
   - For **each** baseline it runs `compute_site_expected` over the baseline’s clipped sub‑window. **There is no per‑segment physics validation** — the superseded #3 is computed verbatim.
4. The expected per bucket comes from `_expected_power_breakdown`:
   - `thermal_coefficient = thermal_coefficient_pct / 100` → for #3 = **3.5 /°C**.
   - `cell_temperature_c = (cell_temperature_f − 32)/1.8`; Site‑4 cell temps are −3.9…70.3 °F (≈ −19.9…21.3 °C) — **always below** the 25 °C reference → `delta_c < 0`.
   - `temperature_factor = 1 + 3.5 × delta_c` → strongly **negative** (≈ −30 to −60 at midday).
   - `expected = dc_nameplate(646 kW) × system_derate × irradiance_factor × temperature_factor`.
   - **Upper clip only:** `min(expected, AC nameplate=462)`. There is **no `max(0, …)` floor**, so large negative expected values pass straight through.
5. The `actual` field is the rollup value, `0.0`‑filled only when a bucket is missing (rare here; completeness ≈ 1.0). Gap regions append actual points with `expected=None`. Nulls/zeros preserved correctly.

**Live read‑only run of the builder for Site 4 (production code, no mutation):**

```
expected_state: available          baseline_selection_mode: period_effective
n_points: 168                      baseline_id counts: {3: 144, 4: 24}
ACTUAL   min=-0.07   max=306.76
EXPECTED min=-39368.59  max=462.00
-- most NEGATIVE expected --
  2026-06-20 15:00  exp=-39368.6  act=304.95  bl=3
  2026-06-19 15:00  exp=-38768.0  act=255.04  bl=3
  2026-06-20 16:00  exp=-37618.9  act=269.19  bl=3
  2026-06-16 14:00  exp=-36530.0  act=291.34  bl=3
-- most POSITIVE expected --
  2026-06-21 15:00  exp=462.0    act=306.76  bl=4   (clipped to AC nameplate, correct)
```

Baseline physics (DB, read‑only):

| id | status | thermal_coefficient_pct | power_tolerance_min_pct | module W×qty | inverter kW×qty | pto_date |
|---|---|---:|---:|---|---|---|
| 3 | superseded | **350.0** | 5.0 | 340 × 1900 | 66 × 7 | 2026‑05‑11 |
| 4 | active | **−0.35** | 0.0 | 340 × 1900 | 66 × 7 | 2026‑05‑11 |

**The builder emits the actual series correctly; it emits a poisoned expected series for the 144 historical (#3) buckets.**

---

## 9. Frontend transformation audit (Audit G)

Checked `ActualProjectedPower.tsx` and helpers against the required failure list:

| Suspect transform | Present? | Note |
|---|---|---|
| `\|\| 0` / null→0 on the line series | **No** | `actual`/`expected` passed as‑is; `period: new Date(period)` |
| Forward‑fill / LOCF | **No** | none |
| Fallback to latest actual repeated across buckets | **No** | none on the line chart |
| Map/reduce reusing one value for all timestamps | **No** | 1:1 mapping over `data[]` |
| Labels disconnected from value timestamps | **No** | `xKey: 'period'`, time axis |
| Actual/expected merge errors | **No (merge)** | two series, shared `period` key |
| Daily aggregate used for hourly labels | **No** | hourly throughout |
| Stale memo / cache key | **No functional impact** | `useQuery staleTime 15m`; correct site‑keyed cache |
| `resolveExpectedState` gating | Works as designed | hides expected only for non‑`available`/`partial` states |

**The single FE‑side contributor is structural, not a bug per se:** both series share **one Y‑axis** with AG Charts auto‑domain. When the backend feeds expected values of ≈ −39,000 kW, the auto‑domain becomes ≈ [−39,369, +462]. The actual curve (0–307) then occupies < 1 % of the plot height → visually flat. The FE faithfully renders what the backend sends; it does not fabricate or flatten the actual data itself.

Note the doughnut widget (`ActualProduction.tsx`) does use `?? 0` and clamps `>100 → 100`, but that is the **summary** widget fed by the active‑baseline‑only path; it is not the reported line chart and is not affected.

---

## 10. Expected‑versus‑actual separation findings (Audit H)

| Requirement | Status |
|---|---|
| Actual comes from V2 rollups only | ✅ `site_power_ac_kw`/`irradiance_wm2` rollups; no BigQuery/Firestore/legacy |
| Expected comes from period‑effective baseline calc only | ✅ `compute_site_expected_period_effective` |
| Actual does not inherit expected | ✅ separate fields; actual range 0–307 is intact |
| Expected does not overwrite actual | ✅ confirmed (actual healthy in the same payload) |
| Nulls and genuine zeros preserved independently | ✅ (with one caveat below) expected `None` preserved; genuine actual zeros/tare preserved |

> **Caveat (actual null handling):** the response schema makes `actual`/`irradiance` **non‑optional**, so the builder renders a *missing* actual bucket as `0.0` (`actual_power_kw is None else 0.0`), not `null`. This is a schema‑compat zero‑fill for **absent** buckets only — genuinely *measured* zeros/tare (e.g. the −0.06 kW night values) are real readings and are preserved as‑is. For Site 4 this is moot: completeness ≈ 1.0, so the proven root cause involves no missing actual buckets. A future fix should not conflate “missing → 0.0” (current behavior) with “measured 0”. Expected, by contrast, is genuinely `None` for missing/invalid.

**The two series are correctly separated.** The problem is entirely *within* the expected series (invalid #3), not a cross‑contamination between series. The same latent defect also affects `build_past_performance_section` (daily %): #3’s negative expected energy will distort or produce nonsensical daily ratios for June 14–20, because that builder shares `compute_site_expected_period_effective` and likewise validates only the active baseline. (Not the reported chart, but flagged for the same fix.)

---

## 11. Root‑cause classification (Audit I)

Using the required 10‑way classification:

- **PRIMARY — (7) Backend chart‑builder issue (baseline‑validation gap):** `compute_site_expected_period_effective` computes the **superseded, physically‑invalid** baseline #3 for historical buckets **without** the fail‑closed physics validation that `build_actual_vs_expected_section` already applies to the active baseline. Combined with the formula’s **absent lower clip**, #3 emits expected ≈ −39,000 kW.
- **CONTRIBUTING — (8) Frontend rendering:** the shared auto‑scaled Y‑axis lets those absurd expected values dominate the domain and compress the actual curve into a flat line.
- **RULED OUT (verified healthy):** (1) provider data, (2) raw ingestion, (3) normalized readings, (4) rollup aggregation, (5) metric‑semantic mismatch, (6) timezone/bucket, (9) cache/query invalidation. (10) not applicable — cause is known.
- **Actual pipeline:** **no defect.**

| Confirmed cause | Location | Evidence | Severity | User impact | Repair type |
|---|---|---|---|---|---|
| Invalid superseded baseline computed in period‑effective expected | `app/services/telemetry/expected_service.py::compute_site_expected_period_effective` (no per‑segment validation) | 144/168 points `bl=3`; expected min −39,368.6 | **High** | Actual curve appears flat; chart unreadable/misleading | **Code change, read‑only** (no data mutation) |
| Expected formula has no lower bound | `expected_service.py::_expected_power_breakdown` (`min` clip only) | negative expected passes through | Medium (amplifier) | enables extreme negatives | Code change (formula‑adjacent — out of scope to change math here; see options) |
| Shared auto‑scaled Y‑axis | `ActualProjectedPower.tsx` | domain ≈ [−39369, 462] | Medium (amplifier) | flattens actual visually | FE code change (defense‑in‑depth) |

---

## 12. Repair options ranked by risk (Audit I)

**Option A — Validate each baseline segment on read in period‑effective stitching (RECOMMENDED; lowest risk).**
Apply the *same* fail‑closed `validate_baseline(..., read_time)` already used for the active baseline to **every** segment inside `compute_site_expected_period_effective`. A segment whose baseline is `is_blocking` contributes `expected = None` (honest gap) for its buckets, exactly as the active‑baseline `baseline_invalid` path does. The actual line is unaffected and renders normally.
- Read‑only (no DB writes), no formula‑math change, no baseline mutation, no backfill.
- Directly closes the previously documented caveat.
- Surface a per‑segment / per‑point flag so the FE can caption “expected unavailable for this period (baseline invalid)”.

**Option B — Add a physically‑sane lower bound to expected (defense‑in‑depth; touches formula).**
A `max(0, …)` floor would prevent negative expected. **Deliberately out of scope** for a read‑only sprint because it changes the expected formula; only adopt under the formula‑math governance used for the WAM model, and only as a secondary guard — it would *mask* an invalid baseline rather than surface it. Option A is preferred precisely because it keeps the “invalid → honest N/A” contract.

**Option C — Frontend axis hardening (defense‑in‑depth; cosmetic).**
Give expected its own Y‑axis, or clip the rendered domain to plausible bounds, so a single bad series can never flatten the other. Useful resilience, but it masks the real issue; do it only *in addition to* Option A.

**Option D — Data action on baseline #3 (NOT recommended / not needed).**
#3 must remain immutable and superseded. No backfill or correction is required because expected is computed on read; Option A makes the chart correct without touching #3.

---

## 13. Historical‑data implications (Audit I)

- **Actuals:** none. `telemetry_readings` and both rollup tables are intact and correct for the full history (2026‑05‑11 → 2026‑06‑21); no repair, re‑ingest, or backfill needed.
- **Expected:** computed **on read**, never persisted as a curve, so there is nothing stored to backfill or correct. Option A fixes all historical windows retroactively the next time they are rendered.
- **Period‑effective contract preserved:** activating #4 already (correctly) did not rewrite #3’s period. Option A only changes *whether an invalid segment renders a number*, not which baseline owns which period.

---

## 14. Test plan (Audit J)

Validation dataset (already exercised in this audit; reuse for regression):
- One full **local** day with daylight + night: 2026‑06‑15 (America/New_York).
- A daytime interval that must vary: local 13:00 (≈292 kW hourly rollup; raw ~298–324 kW).
- A nighttime interval that must be ≈0/absent: local 02:00 (≈ −0.06 kW tare).
- Raw‑vs‑final comparison: provider `KW` raw → `site_power_ac_kw` rollup → chart `actual`.

Proposed tests for the implementation sprint (Option A):
1. **Unit (period‑effective):** a window covering one valid + one invalid baseline → buckets owned by the invalid baseline have `expected is None`; buckets owned by the valid baseline compute normally; **actual is unchanged** for all buckets.
2. **Unit (no axis poisoning):** assert max/min expected over the window are within plausible bounds (e.g. `−ε ≤ expected ≤ AC nameplate`) once invalid segments are suppressed.
3. **Regression (active‑invalid path untouched):** the existing `baseline_invalid` behavior for an invalid **active** baseline still short‑circuits as today.
4. **Builder integration:** `build_actual_vs_expected_section` for a Site‑4‑like fixture returns `expected_state = partial` (valid recent segment + suppressed historical segment) with actual intact.
5. **Past‑performance parity:** `build_past_performance_section` over the same window yields `None` (honest gap) for days under the invalid segment, never a fabricated/negative %.
6. **F/C guard:** retain the existing temperature‑unit equivalence tests (the conversion is correct; the coefficient was the fault).

---

## 15. Recommended implementation sprint

**Title:** Period‑effective expected — per‑segment fail‑closed validation (close the superseded‑invalid‑baseline gap).

- **Goal:** Stop superseded/invalid baselines from emitting expected values in historical windows; render them as honest `None`/“baseline invalid for this period”, leaving actuals fully intact. Restores the Site‑4 actual curve with zero data changes.
- **Primary change:** Option A in `compute_site_expected_period_effective` (and propagate a per‑segment invalid flag to `build_actual_vs_expected_section` and `build_past_performance_section`), plus a small FE caption for the suppressed historical expected.
- **Optional hardening:** Option C (FE axis isolation) as defense‑in‑depth. Defer Option B unless formula‑math governance approves a lower clip.
- **Constraints to carry forward:** no change to raw readings, rollups, ingestion, WeatherResolver, baseline lifecycle, or the expected **formula math**; no BigQuery/Firestore/legacy fallback; preserve nulls and genuine zeros; keep period‑effective ownership semantics.
- **Definition of done:** for Site 4’s 7‑day window, expected ∈ [≈0, 462] kW (no −39k), `expected_state = partial`, actual curve renders its true 0–307 kW shape; tests in §14 pass; `#3` remains immutable and superseded.

---

### Appendix — audit method (read‑only)
- DB inspected via read‑only SQL (`telemetry_readings`, `telemetry_site_interval_rollups`, `telemetry_device_interval_rollups`, `telemetry_expected_baselines`).
- The production chart‑builder `build_actual_vs_expected_section(db, site_4)` was executed read‑only (no commit/flush; the function performs zero writes) to capture the exact `actual`/`expected` ranges and `baseline_id` distribution cited in §1/§8.
- No raw readings, rollups, baselines, credentials, ingestion, formula math, WeatherResolver, or baseline lifecycle were modified. No backfill was run.
