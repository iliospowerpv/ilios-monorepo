---
name: Expected-baseline readiness input resolution
description: Why a site shows "draft not ready / no active baseline / design points 0/12" — the input-source map behind the weather-adjusted expected baseline. Full audit in docs/.
---

# Expected-baseline readiness inputs

Full written audit: `docs/expected_baseline_readiness_input_audit.md` (areas A–L, code-cited).

**The non-obvious conclusion:** the three observed blockers ("draft weather-adjusted
baseline not ready", "no active baseline", "design-estimate points 0/12") collapse to
**two mechanical causes + one UX gap**, not three independent problems:

1. **Non-numeric active facts** — `module_wattage`/`inverter_wattage` are stored verbatim
   as text-with-unit (`{"v":"340 Wp"}`, `{"v":"66 kWac"}`). The readiness evaluator coerces
   with bare `float()` (strips only commas/whitespace), so they become `None` → counted as
   MISSING. That's why the same field shows up in BOTH the "missing" and the "non-numeric"
   lists — one defect, surfaced twice.
2. **Five required physics constants have no fact source at all** — of the 9
   `REQUIRED_PHYSICS_FIELDS`, only the 4 module/inverter wattage+quantity are fact-backed
   (`FACT_FIELD_TO_COLUMN`). `thermal_coefficient_pct`, `power_tolerance_min_pct`,
   `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct` are
   reviewer-supplied-only (no extraction, no canonical mapping, no reconciliation row).
3. **UX gap** — `evaluate_readiness` calls the evaluator with `reviewer_values=None`, so
   those 5 constants are ALWAYS "missing" in the panel and there is no in-panel way to
   supply them or to normalize the text-with-unit facts.

**Durable gotchas worth remembering (not easily grepped):**
- **Unit asymmetry:** `module_wattage` is in **W**, `inverter_wattage` is in **kW** (per the
  `dc_nameplate_kw = w*qty/1000`, `ac_nameplate_kw = w*qty` formula). `_unit_warnings`
  flags implausible magnitudes but NEVER converts. Stripping `Wp`/`kWac` is a *safe*
  normalization; a `Wac`-on-an-inverter value would need a W→kW conversion and must be
  confirmed, never auto-applied.
- **PTO None ⇒ the ENTIRE expected curve is suppressed** (every bucket `pre_pto`,
  `expected=None`), not just "before PTO". **PTO is now REQUIRED for
  `weather_adjusted_model`** — missing `pto_date` ⇒ not ready, listed in `missing_fields`,
  blocker `REVIEWER_SUPPLIED_NEEDED`/`BLOCKS_DRAFT` (so a WAM draft can never be created
  with a NULL PTO that would suppress the whole curve). Other baseline types keep PTO
  informational (`PRE_PTO_EXPECTED_SUPPRESSED`/`BLOCKS_EXPECTED`, non-blocking). **Why:** a
  WAM baseline with no PTO is useless (expected is NULL for every bucket) yet used to look
  "active" — the perpetual "needs reviewer input" / empty-O&M symptom on Site 4.
  Also a naming gap: EPC config extracts `PTO`→canonical `pto`, but the bridge expects a
  reviewer-supplied `pto_date` — extracted PTO does not flow to the baseline today.
- **Activation effective-from is PTO-anchored on FIRST activation only.** When a WAM
  baseline is activated and there is NO prior active row AND `pto_date` is set, `active_from`
  is backdated to PTO (date→naive-UTC midnight) so the trailing O&M window is covered;
  a *replacement* activation instead uses `now` and closes the prior row at `active_to=now`
  (history is never rewritten). **Why:** `active_from=now` on a freshly-activated baseline
  left the post-PTO comparison window uncovered, so O&M showed no expected/comparison data.
- **Optional losses default to 0% and soiling to 1.0** (optimistic) with only a free-text
  warning — no structured "default applied" indicator anywhere.
- **Design-estimate points 0/12 is a SEPARATE pipeline** (`baseline_points_service`), driven
  by monthly/annual production facts; it never distributes an annual total into months and
  assumes kWh `unit_verified=false`. Fixing the 9 physics inputs does NOT populate the 12
  points, and vice-versa — they are two independent "expected" notions.

**Recommended fix order (audit Section K):** Phase 1 actionable readiness trace; Phase 2
normalize-at-readiness (smallest blast radius, raw fact never mutated); durable home =
acceptance-time confirm. Never auto-normalize in `_coerce_number`; never auto-convert units.

**As-built invariants (the actionable Baseline Readiness panel — keep these true):**
- **Confirm-only normalization needs BOTH anchors.** A reviewer normalization confirmation is
  only honored when it carries `source_fact_id` AND `raw_value` (both schema-REQUIRED and
  re-checked in the service). Missing either, or a stale `source_fact_id`/drifted `raw_value`,
  or a `confirmed_value` that disagrees with the server recompute → the field is rejected and
  stays MISSING (no draft). **Why:** you must prove the reviewer confirmed the *current* fact's
  *current* text; an unanchored confirmation could silently apply against a fact that changed
  underneath them. **How to apply:** any new normalizable field or new caller MUST send both
  anchors, and the rejection-on-missing-anchor path is covered by tests — keep it that way.
- **Facts are never mutated.** Normalization is recorded only in the baseline's effective value
  + provenance (`project_fact_normalized` source: raw/normalized/from→to unit/method/fact_id/
  confirmed_by/at). `project_facts` rows are read-only here; no auto-promote, no auto-activate.
- **FE draft gate = `useTelemetryAdminPermission()`** (platform-bypass OR `Telemetry.admin` OR
  legacy `Settings Page`.edit), kept in lockstep with the backend `telemetry_admin_required`
  dependency. Don't hand-roll the permission check in the panel/Reconciliation — drift from the
  backend gate is the bug. Non-admins get a graceful read-only note, not a hard error.
