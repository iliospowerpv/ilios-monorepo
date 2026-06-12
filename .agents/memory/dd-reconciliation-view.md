---
name: DD reconciliation view (read-only)
description: How the DD V2 assumptions reconciliation aggregator decides per-row "in baseline" status across the two distinct "expected" baselines.
---

# DD reconciliation view — relevant-baseline-per-target rule

The reconciliation service (`app/services/due_diligence/reconciliation_service.py`,
endpoint `GET /api/due-diligence/sites/{site_id}/reconciliation`) is a STRICTLY
read-only aggregator of the audit chain: doc → AI value → accepted/overridden →
active project_fact → draft baseline → design-estimate points → active
weather-adjusted baseline (+ legacy SiteAdditionalFieldList, display-only). It
performs zero writes/commits, never recomputes a baseline value (points read
verbatim via `list_for_baseline`), and never auto-creates/approves/activates.

## Rule
When deciding a row's `in_draft_baseline` / `in_active_baseline` status, the
presence check must use the baseline that field's target actually lives on:
- HEADER_COLUMN (physics nameplate) → the WEATHER-ADJUSTED baseline (wam draft/active).
- POINTS_MONTHLY / POINTS_ANNUAL (design production) → the DESIGN-ESTIMATE
  baseline (de draft/active).
- METADATA / NONE (GHI, P50/P90, catch-all) → never "in baseline".

**Why:** the two "expected" notions are separate end-to-end (see
`telemetry-expected-baseline-design.md`). The original implementation passed the
weather-adjusted baselines to the presence check for ALL targets; the
`baseline is None` short-circuit then forced stored design points to report
`active_fact` whenever no weather-adjusted baseline existed — silently hiding
that a design point was already present. Crossing the two baselines is the
bug-prone trap here.

**How to apply:** any new baseline_target must map to its own baseline pair
before the status ladder runs; never reuse one baseline-type's draft/active for
another type's presence test. Regression-guarded by H10/H10c in
`tests/unit/due_diligence/reconciliation_test.py`, and H17 guards the catalog
canonical names against drift from the Phase 3 points producer.
