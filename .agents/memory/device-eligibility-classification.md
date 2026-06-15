---
name: Device eligibility vs expected-driver split
description: The two-verdict telemetry device classifier — broad "mappable" vs frozen "drives_expected" — and why eligibility expansion must never widen the expected/health gate.
---

# Device eligibility vs expected-driver split

Telemetry device classification has TWO independent verdicts, and conflating them is the
trap:

- **mappable** (broad, meant to grow): may a device be linked to a provider/DAS device so
  its streams are stored and inspected? Covers the stable three PLUS meters, power/DAS
  loggers, gateways, and weather-source sensors — resolved by category, by an operator-set
  `device_role`, or by an explicit `*_capable` column. Gates ONLY mapping-validation and the
  eligible-devices surfaces.
- **drives_expected / can_drive_expected** (FROZEN): does the device feed the
  expected-vs-actual / O&M pipeline? Category-only `{inverter, module, weather_station}`. A
  role or capability override must NEVER widen it.

**Why:** "Device Eligibility Expansion" needed meters/loggers/gateways/weather sensors to
become mappable for inspection WITHOUT changing expected math or flipping any existing
site's health/readiness. Health and readiness counts therefore key off `drives_expected`,
NOT the broad mappable set. If you ever route a count or an expected calc through
`is_mappable`, expanding eligibility silently changes behavior for live sites.

**How to apply:**
- Use `drives_expected(device)` wherever an eligibility change must NOT alter behavior
  (health, readiness, expected). Use `is_mappable(device)` only for mapping-validation and
  the eligible-devices list.
- Weather measurement semantics (`irradiance_plane`/`temperature_type`/`calibration_status`)
  are NEVER guessed or converted — the classifier decides weather-source *capability* only;
  meaning is declared on `weather_device_mappings` and defaults to `unknown`.
- Classification columns on `devices` are nullable/additive and resolution is "explicit
  operator-set column wins, else derive from category/type". `mapped_status` stays derived.
- Role-only types (power_logger, das_logger, reference_cell, site_performance_virtual on a
  non-mappable category) are honored ONLY when `device_role` is set; there is no manual
  role-setter API/UI yet, so they are unreachable from normal provider sync until one
  exists. Meters/gateways/weather are reachable today via category.
- The classification backfill must stay non-destructive: fill NULL columns only, never touch
  telemetry mappings, and fingerprint protected-site (site 4 / 110 Shawmut) mapping ROWS
  before/after (not just counts), rolling back on any add/remove/edit.
