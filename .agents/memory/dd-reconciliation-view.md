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
another type's presence test. Regression-guarded in
`tests/unit/due_diligence/reconciliation_test.py` (baseline-presence-per-target
cases, plus a catalog-canonical-name guard against drift from the points producer).

## Additive parse-state indicators on rows (display-only)
Reconciliation rows can carry read-only parse-state booleans (uploaded-not-parsed,
parse_failed, no-usable-fields, not-current-version, type-lacks-operational-schema)
computed from the row's source FILE via the parse-state service. They are
**display-only**: populated AFTER the status ladder runs and copied into response
fields only — they never feed status/blocking/needs_review/missing_deps/baseline.

**Why (two traps):**
- A row sourced to an *active/promoted* fact classifies the file as `promoted` in
  parse-state precedence, so the "problem" indicators (not_parsed/failed/no_usable)
  can only ever surface for **candidate-sourced** rows. Parity tests must use a
  CANDIDATE fact, not an active one, or the indicator never trips.
- The file lookup MUST be scoped to the site's live files (`file_to_document`, which
  excludes archived docs) before computing indicators, or a stale/cross-site
  `source_file_id` would leak another site's parse state onto this audit screen.
  Indicators are memoized per file_id (including the None/out-of-scope result).
