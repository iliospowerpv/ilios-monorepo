---
name: WA baseline physics validation gate
description: How expected-energy baselines are validated (fail-closed activation + validate-on-read baseline_invalid) and the constraints that shaped it.
---

Weather-adjusted (WA) expected-energy baselines are validated for physical
plausibility by a pure module (`baseline_physics_validation.validate_baseline`,
no DB writes). Two enforcement points:

- **Activation (write):** `TelemetryExpectedBaselineCRUD.activate` validates
  BEFORE supersede/commit. `hard_invalid` blocks outright (structured 409 via
  `JSONResponse` — NOT a plain HTTPException, whose detail gets str()'d);
  warning-only baselines require an explicit ack + a source note. On a block the
  draft AND the existing active row are left untouched.
- **Read (read-time):** the V2 expected/O&M read path validates the *current
  active* baseline on read. Blocking -> state `baseline_invalid`, expected
  suppressed to null/unavailable (**never a fabricated 0**), actuals preserved.
  This is validate-on-read: the invalid baseline shows as invalid WITHOUT being
  mutated (the trigger case, Site 4 #3 thermal=350, is surfaced this way).

**Why:** an invalid baseline (e.g. thermal_coefficient_pct=350 vs -0.35 %/°C)
must never silently drive a wrong "expected" or get auto-corrected. Replacement
is a NEW baseline that supersedes the old one; the immutable active row's physics
are never edited and history is never recomputed.

**How to apply / gotchas:**
- The formula math is frozen. `_expected_power_kw` is a thin wrapper over
  `_expected_power_breakdown(...).clipped_kw`; the smoke test reuses that ONE
  canonical F->C conversion site. Any change here must stay byte-identical.
- Temperature units are first-class: 25 °C == 77 °F -> factor 1.0; a
  %/°C-vs-°F-delta unit mismatch must be detected and fail (never assume unit).
- Read-path validation is reachable through seams `v2_chart_data._active_baseline`
  / `_evaluate_active_baseline` and `v2_company_data.is_active_baseline_blocking`.
  Many wiring/period-effective unit tests pass a FAKE `object()` baseline or
  `db_session=None`; when you add/extend read-path validation, isolate such tests
  by monkeypatching those seams (or give a lifecycle-only fixture valid physics) —
  the canonical valid field set lives in `baseline_physics_validation_test._baseline()`.
- Period-effective stitching now validates EVERY overlapping segment at read time,
  not just the current active baseline. A superseded-but-invalid segment inside the
  window is suppressed (per-bucket `baseline_invalid`: expected null, actual/weather
  preserved verbatim, owning `baseline_id` stamped) instead of computing physics, so
  an invalid history segment can no longer emit a garbage expected curve. Suppression
  is fail-closed and read-only: it never mutates baseline rows/readings/facts, never
  recomputes history, and ownership dedupe still goes through `_effective_baseline_at`
  (the suppressed bucket of a non-owning segment is dropped at the boundary).
  **Why:** the old "active-only" stitching let a superseded invalid baseline (Site 4
  #3 thermal=350) compute and blow up the chart — see the diagnostic symptom below.
- State semantics after suppression: valid+invalid segments coexisting →
  `expected_state=partial`; all-invalid / no-ok-and-invalid-dominant →
  `baseline_invalid`. The company active-only path (zero invalid segments) is
  unchanged. Invalid-segment provenance is exposed additively as
  `invalid_baseline_segments` (id + window + validation summary + policy version),
  surfaced through both O&M chart section builders — additive, never replaces actual.

**Diagnostic symptom (non-obvious), now MITIGATED:** before per-segment suppression,
the visible symptom was an *implausibly FLAT ACTUAL line* on the O&M actual-vs-expected
chart — NOT an obviously-wrong expected line. Both series share ONE auto-scaled
AG-Charts Y-axis, so an invalid superseded segment emitting unclipped huge values
(the formula has only an upper `min(expected, AC nameplate)` clip, no lower bound;
thermal=350 + sub-25°C cell temps → expected ≈ −39,000 kW) blew up the domain and
compressed the healthy actual curve into a flat sliver. Per-segment suppression now
emits null (not a garbage magnitude) for such segments, and the FE `finiteOrNull`
domain guard ignores non-finite/null expected — so a flat-actual chart should now be
rare. If it recurs, still check expected magnitude / invalid segments FIRST, NOT the
readings/rollup pipeline (which is fine). Full trace:
`docs/telemetry/v2_actual_production_curve_integrity_audit.md`.
