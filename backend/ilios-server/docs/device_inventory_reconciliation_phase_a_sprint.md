# Device Inventory Reconciliation Indicator — Phase A (Sprint Doc)

## 1. Purpose

A **site-level, strictly READ-ONLY** reconciliation that answers one question for a
project/site:

> Does the approved *documented* equipment inventory (active `project_facts`) agree
> with what telemetry has *discovered/observed* and with the reviewer-confirmed
> device mappings — and if not, what is the single most truthful headline status and
> the concrete next action?

It is an **assessment/inference surface only**. It never mutates data, never
auto-maps/creates/acknowledges/converts anything, and never drives expected or O&M
math. It surfaces a headline status (the G1→G8 ladder), secondary flags,
class-specific counts, mismatch records (with a stable `mismatch_signature`), and
recommended next actions.

## 2. Hard constraints honored

- **Zero mutation.** The service performs no writes/commits to `devices`,
  `telemetry_devices_mapping`, `telemetry_sites_mapping`, `project_facts`,
  `telemetry_*`, `weather_device_mappings`, or baselines. No auto-map / auto-create
  / auto-ack / auto-task / auto-convert.
- **Endpoint returns HTTP 200 for EVERY valid reconciliation state.** 4xx is reserved
  for auth / invalid-site / malformed input. A site with nothing configured is a
  *valid* `telemetry_not_connected` 200, not an error.
- **Active promoted facts are the SOLE authority for documented counts.** Candidates
  are review signals only (counted, never definitive).
- **`can_drive_expected` stays FROZEN** to `{inverter, module, weather_station}`. The
  service only *consumes* `classify_device`; it never widens the expected-driver set.
- **Modules are NEVER compared to telemetry device counts.** Module documentation is
  array/site-level; the module class-count row carries `discovered_count=None` and no
  module-vs-telemetry-device mismatch is ever emitted.
- **Recorded provenance (persisted) is kept distinct from reconciliation inference**
  (assessment, never definitive).
- **Weather remediation is a governed weather-semantics workflow** — never "map a
  weather device", never convert/assume POA/cell semantics.
- No change to O&M actual display, expected calc, weather mappings/eligibility,
  baseline status, the resolver, legacy paths, or the `Site` entity.

## 3. The G1 → G8 headline ladder (first-gate-wins, top-down)

The headline status is the **first** gate that matches, evaluated top to bottom:

| Gate | Status | Condition (summary) |
|------|--------|---------------------|
| G1 | `telemetry_not_connected` | No active site telemetry mapping. |
| G2 | `documented_inventory_incomplete` | Connected, but missing an active `inverter_quantity` OR `module_quantity` fact. |
| G3 | `telemetry_connected_no_devices` | Documented complete, but `discovered == 0` AND `mapped == 0`. |
| G4 | `telemetry_inventory_incomplete_or_stale` | (`inverter_qty > 0` documented AND `observed_inverter_count == 0`) **OR** (discovery stale AND readings not fresh). |
| G5 | `needs_reconciliation` | A **blocking** mismatch exists (Phase A: only `weather` `not_acknowledgeable_blocking`). |
| G6 | *(acknowledged)* | **Unreachable in Phase A** — there is no acknowledgement write path. |
| G7 | `partially_matched` | `open_actionable_mismatch_count > 0` (non-blocking follow-ups). |
| G8 | `matched` | Everything reconciles. |

Thresholds: `DISCOVERY_STALE_AFTER = 7d`, `READINGS_FRESH_WITHIN = 2d`.

> Note: the approved ladder is **G1–G8**. Earlier planning text referencing "G1–G10"
> is incorrect; G6 exists as a placeholder for a future acknowledgement state and is
> intentionally unreachable in Phase A.

## 4. Bug fixed during A8 — `project_facts.value` envelope unwrap

`project_facts.value` is a JSONB **`{"v": <scalar>}` envelope** (real Site-4 data is
`{"v": "7"}` / `{"v": "1900"}`, i.e. *wrapped strings*). The DD reconciliation service
already unwraps these via `_unwrap()`.

The inventory reconciliation service was reading the fact values **raw**
(`_coerce_int(inv_qty_fact.value)`, `_as_text(inv_model_fact.value)`), handing a
`dict` to the coercers, which therefore returned `None`. As a result
`documented_inverter_qty`, `documented_module_qty`, and `documented_inverter_model`
**silently read as missing on real data**.

This was masked during A7 because the Site-4 headline path reaches
`needs_reconciliation` via the **blocking weather** dependency, which does not depend
on the numeric documented count. The presence-only check that gates G2 (a fact simply
*existing*) also still passed, so the gap was invisible from the headline alone.

**Fix:** added an `_unwrap()` helper to the inventory service (mirroring the DD
service) and applied it at the three fact-value read sites.

**Intended verdict changes from the fix** (documented counts are now non-`None` on
real data):
- G4's `expected_inverters_documented` branch can now legitimately fire when inverters
  are documented but none are observed.
- An informational inverter quantity mismatch can now be emitted when documented vs
  observed inverter counts differ.
- `approved_aggregate` coverage and documented class-counts now populate correctly.

Re-validated on real Site 4: documented now reads `7` / `1900`, the headline is
**unchanged** (`needs_reconciliation` — blocking weather still wins), and the session
remains clean (no new/dirty/deleted).

## 5. A8 testing approach

`tests/unit/telemetry/device_inventory_reconciliation_test.py` (13 tests, all green):

- **Zero mutation (`TestZeroMutation`).** A whole-table fingerprint (every column of
  every row, read fresh via `expire_all`) of the nine tables the service touches —
  `devices`, `telemetry_devices_mapping`, `telemetry_sites_mapping`, `project_facts`,
  `telemetry_external_sites`, `telemetry_external_devices`, `telemetry_sync_jobs`,
  `weather_device_mappings`, `telemetry_expected_baselines` — captured before/after
  `build_site_inventory_reconciliation` **and** `build_inventory_reconciliation_summary`,
  asserted byte-for-byte identical, plus `db.new/dirty/deleted` are empty. Covered for
  a rich Site-4-shaped site and for an empty site.
- **Ladder (`TestLadder`).** One synthetic site per gate: G1 (no mapping + inactive
  mapping), G2, G3, G4 (both the unobserved-inverter branch and the stale-discovery
  branch), G5 (blocking weather while a WA baseline is active), G7 (non-blocking
  follow-up), and G8 (matched). G6 is intentionally not tested (unreachable in
  Phase A).
- **Site-4-shaped (`TestSite4Shaped`).** Reproduces the validated 13-documented /
  13-discovered shape and asserts `needs_reconciliation`, the full
  `mismatch_category_counts` breakdown (`weather:1`, `missing_telemetry_counterpart:1`,
  `undocumented_telemetry_device:3`, `telemetry_freshness:1`), `open_actionable=5`, and
  the documented inverter/module counts (`7` / `1900`). A dedicated regression test
  pins the `{"v":...}` unwrap directly via the inverter/module documented counts.

Harness: dedicated test DB (`test_db_name` env), coverage `addopts` overridden for the
subset run, no `pytest-mock` (the service is pure-read). The suite builds its own
company/site/devices/mappings via CRUD + ORM and assigns the DAS provider to the test
company before creating a connection.

### Scope / known limitation
These tests prove the **service + summary** path is read-only and ladder-correct. They
do not exercise the HTTP wrapper itself; the endpoint only enforces auth/visibility and
delegates to the same builder. A future endpoint-level no-mutation smoke test is an
optional hardening item.

## 6. Validation evidence

- `device_inventory_reconciliation_test.py`: **13 passed**.
- `tests/unit/due_diligence/reconciliation_test.py` (consumes the same summary fn via
  DD `telemetry_reality`): **40 passed** — no regression from the `_unwrap` fix.
- Architect review (`evaluate_task`, with git diff): **PASS** — no blocking
  read-only/additive, module-comparison, or expected-driver violations; `_unwrap` fix
  judged correct and complete (no remaining raw `.value` reads).

## 7. Key files

- `app/schema/inventory_reconciliation.py` — enums + response/summary models.
- `app/services/telemetry/device_inventory_reconciliation_service.py` —
  `build_site_inventory_reconciliation`, `build_inventory_reconciliation_summary`, the
  G1–G8 ladder, and the `_unwrap` fact-envelope helper.
- `app/services/due_diligence/reconciliation_service.py` — populates DD
  `telemetry_reality` from the summary fn.
- `tests/unit/telemetry/device_inventory_reconciliation_test.py` — A8 tests.
