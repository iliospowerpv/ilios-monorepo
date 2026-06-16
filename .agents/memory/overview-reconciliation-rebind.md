---
name: Overview protected-field reconciliation provenance
description: Project Hub Overview protected fields read LIVE reconciliation truth; durable display constraints.
---

# Overview protected-field reconciliation provenance

Project Hub Overview "protected" fields (AssetOverview module/inverter/project_type + 4 ohmic losses,
KeyDates PTO, SiteLevelDetails system_size_dc/ac, year_one, degradation) display value + status sourced from
the reconciliation report (`GET /api/due-diligence/sites/{id}/reconciliation`, `Diligence:view` gated) via a
single tab-level context provider with a SAFE-DEFAULT context (cards never call `useAuth`, never throw without a
provider, degrade to static provenance labels for asset-only users). Display value precedence:
`active_fact_value > accepted_value > ai_extracted_value > legacy_value > card fallback`; `0`/`false` count as
present, `''`/null/undefined as absent.

**Durable constraint — reconciliation/`project_fact` values are TEXT.** They can carry units, commas, or other
non-numeric content (e.g. "1.2 MW"). Any numeric formatter that consumes a reconciliation value MUST be
NaN-safe: coerce, and if not finite, render the raw string verbatim — **never** emit literal "NaN".
`formatFloatValue` (lodash `round` + `Intl.NumberFormat`) returns the string "NaN" for non-numeric input, which
would be a visible regression for Diligence users vs. the prior static numeric render.

**Why:** the rebind replaces a guaranteed-numeric card value with a possibly-stringy live value; without the
guard a malformed/unit-bearing fact value shows "NaN" where a clean number used to be (violates zero-regression).

**How to apply:** when adding/altering any numeric protected Overview field, wrap its formatter with a finite
check that falls back to the raw string (see `formatLossValue` / `formatSystemSize`). Keep these fields
READ-ONLY — no edit path, no SAFL/BQ/fact writes; this surface is display-only over the reconciliation truth.
