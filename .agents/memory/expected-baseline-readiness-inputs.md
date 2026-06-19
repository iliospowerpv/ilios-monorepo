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
  `expected=None`), not just "before PTO". PTO is NOT a draft blocker (warning only).
  Also a naming gap: EPC config extracts `PTO`→canonical `pto`, but the bridge expects a
  reviewer-supplied `pto_date` — extracted PTO does not flow to the baseline today.
- **Optional losses default to 0% and soiling to 1.0** (optimistic) with only a free-text
  warning — no structured "default applied" indicator anywhere.
- **Design-estimate points 0/12 is a SEPARATE pipeline** (`baseline_points_service`), driven
  by monthly/annual production facts; it never distributes an annual total into months and
  assumes kWh `unit_verified=false`. Fixing the 9 physics inputs does NOT populate the 12
  points, and vice-versa — they are two independent "expected" notions.

**Recommended fix order (audit Section K):** Phase 1 actionable readiness trace; Phase 2
normalize-at-readiness (smallest blast radius, raw fact never mutated); durable home =
acceptance-time confirm. Never auto-normalize in `_coerce_number`; never auto-convert units.
