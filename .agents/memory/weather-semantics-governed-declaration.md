---
name: Weather device semantics — governed declaration vs ingestion/provider assumptions
description: Why provider DAS metadata and the metric catalog are NOT governed semantic truth, and what a governed weather-semantics declaration must add over weather_device_mappings.
---

# Weather device semantics: three distinct layers — never conflate them

When deciding whether a weather device's readings are physics-usable (POA / cell
temperature) for the weather-adjusted expected model, three layers exist and only the
third is authoritative:

1. **Provider/DAS metadata** (e.g. AlsoEnergy `raw_metadata`): declares *device
   capability* only — `functionCode: "WS"` says "this is a weather station". It says
   **nothing** about irradiance plane (POA vs GHI), temperature type (cell vs ambient),
   or calibration.
2. **Ingestion metric catalog** (`telemetry_metric_catalog`): maps a raw provider field
   to a normalized metric and may even *name* one "POA" (AlsoEnergy `Sun→POA_Irradiance`,
   `Sun2→GHI_Irradiance`, `Temp1→cell_temperature_f`). This is an **ingestion-normalization
   assumption**, NOT a governed claim. It must never be treated as the truth that promotes
   `unknown → POA/cell`.
3. **Governed reviewer declaration** (`weather_device_mappings` + a future governance
   layer): the ONLY authority for physics-usability. Per-`(device, metric)`.

**Why:** the WeatherResolver (W1) already consumes `weather_device_mappings` and only
verifies a window when a mapping declares a single non-unknown physics-usable value with
full coverage. If layer 1 or 2 were allowed to stand in for layer 3, the "never guess /
unknown stays unknown" provenance contract collapses.

**How to apply:** any "weather semantics governance" work extends `weather_device_mappings`
ADDITIVELY (it already has plane/temperature_type/calibration_status enums, physics-usable =
plane `{poa}` / temp `{cell,module,modeled_cell}`). The governance gaps to fill: declarer
identity+timestamp, a **declaration_basis** enum that distinguishes `reviewer_assumption`
from `provider_confirmed`/`source_document`/`reviewer_source_note`, explicit status +
supersession (the table is append-only by contract but `get_current_for_device` is just
latest-id and `updated_at` implies edits are reachable — forbid value rewrites), evidence
refs, and a `needs_re_review` flag that is NEVER auto-cleared. Declaring semantics provides
inputs the resolver already reads — it does NOT change the formula, and it must never
auto-clear a blocking weather dependency (only a governed human declaration does).

Full design: `backend/ilios-server/docs/weather_device_semantics_governed_declaration_design.md`.
