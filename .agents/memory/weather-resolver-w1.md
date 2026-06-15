---
name: WeatherResolver W1 (DAS-only)
description: Read-only weather-input seam for expected_service; provenance must never over-promote unknown semantics.
---

# WeatherResolver (W1) — resolves weather physics inputs over EXISTING DAS only

`WeatherResolver(db).resolve_window(...)` is the read seam `compute_site_expected`
uses for the two physics inputs (`irradiance_poa_wm2`, `cell_temperature_f`). It
reads ONLY V2 telemetry site rollups and carries W0 provenance (source identity,
measurement semantics, confidence, profile policy). It is wired so the numbers
stay **byte-identical** to the prior direct rollup reads — provenance never feeds
the physics formula.

**Hard invariants (mirror W0):** read-only (no writes — not even
`expected_weather_provenance`), no provider/credential/BigQuery/Firestore/legacy/
secret coupling, NO GHI/DNI/DHI→POA and NO ambient→cell conversion, never
fabricate, never promote unknown→verified POA/cell.

## Conservative semantics verification (the non-obvious rule)
A window resolves to `semantics_verified` ONLY when the declaring
`weather_device_mappings` for a metric (a) declare exactly one distinct
non-`unknown` value (≥2 distinct = conflict → unknown), (b) their effective
periods' UNION FULLY COVERS the requested window, AND (c) no coexisting
`unknown`-valued mapping overlaps the window. Otherwise the `chosen` mapping is
still surfaced for source/calibration context but `value` stays `unknown`, so it
resolves as `legacy_das_unverified`.

**Why:** a mapping that only partially overlaps the window, or a POA mapping
coexisting with an `unknown` one, used to mark the WHOLE window verified —
silently promoting an unmapped sub-range to POA/cell. Mappings are device-level
but resolution is at the site rollup, so a coexisting unknown stream makes
attribution genuinely ambiguous; the safe call is unverified.

**How to apply:** keep this rule until a future resolver (W2+) can prove
device-level/source attribution for site rollups. `_periods_cover_window` does
the union/gap check (None bounds = open, abutting periods cover). Don't relax it
to mere overlap.
