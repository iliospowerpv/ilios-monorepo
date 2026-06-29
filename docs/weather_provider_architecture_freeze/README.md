# Weather Provider Framework — Architecture Freeze (Phase D.6)

> **Status: ARCHITECTURE FREEZE. PLANNING / DOCUMENTATION ONLY.**
> No production code is changed by this package. It freezes the architecture of the
> context-only Third-Party Weather Provider Framework (Phases A–D, built) plus the
> D.5 Operational Readiness design (designed, not yet built) so that any future
> **Phase E** (physics use of external weather) can be reviewed separately against a
> stable, documented baseline.

## What this package is

This is the authoritative, frozen description of the weather provider architecture
as it stands at the end of Phase D / D.5. It exists to:

1. Record **why** the architecture is shaped the way it is (ADRs), so future work
   does not silently undo a deliberate decision.
2. Make the **boundaries** explicit (diagrams), especially the hard line between
   external weather (context-only) and the physics/expected path (resolver).
3. Give operators **runnable procedures** (admin guide, runbooks, rollout checklist,
   DR guide) for the system as designed.
4. State exactly **what Phase E would have to satisfy** before it may cross the
   physics boundary (readiness assessment).

## The freeze in one sentence

External **provider** weather (e.g. Open-Meteo `ghi`/`ambient` pulls) is
**provenance/context only** — it is stored, audited, and displayed, but because it is
`ghi/ambient/unknown` it fails the resolver's POA-only / cell-only acceptance test and
is **not selected** for expected-energy or baseline math. That exclusion is the
architecture's central invariant. (The resolver does already consume *measured/approved*
POA/cell via DAS (W1) and approved historical profiles (W2); provider GHI/ambient pulls
are neither.)

## Build status legend

Throughout this package, each component is tagged:

- **[BUILT]** — implemented and merged in Phases A–D.
- **[DESIGNED]** — specified in the D.5 Operational Readiness plan
  (`../third_party_weather_provider_framework_phase_d5_operational_readiness_plan.md`),
  not yet implemented.
- **[FUTURE / PHASE E]** — explicitly out of scope and gated.

## Package contents

| File | Purpose |
|---|---|
| `README.md` | This index + freeze declaration + invariant summary. |
| `adrs.md` | Six Architecture Decision Records capturing the load-bearing decisions. |
| `system_diagrams.md` | Five structural diagrams (provider lifecycle, import lifecycle, provenance flow, resolver boundaries, operational governance). |
| `sequence_diagrams.md` | Six interaction diagrams (preview, import, retry, safe disable, replay, rollback). |
| `admin_guide.md` | Operator-facing guide to the framework's concepts and screens. |
| `runbooks.md` | Step-by-step procedures for routine and incident operations. |
| `rollout_checklist.md` | Ordered, gated production rollout with rollback. |
| `disaster_recovery_guide.md` | Backup/restore validation, replay, integrity, duplicate detection. |
| `phase_e_readiness_assessment.md` | Prerequisites, risks, scientific/data/governance gates before Phase E. |

## Frozen invariants (the contract Phase E must not break)

These are restated in every document because they are the whole point of the freeze:

1. **External provider weather is context-only.** Provider-pull observations stay
   `irradiance_plane ∈ {ghi, unknown}` / `temperature_type ∈ {ambient, unknown}`, are
   reported as `physics_usable_rows == 0` in the external-weather-context view, and are
   never expected-eligible. (ADR-0001)
2. **`WeatherResolver` is immutable in this track.** Its window resolution, source
   selection, and POA-only / cell-only physics test are not changed. (ADR-0002)
3. **Jobs and batches are separate.** Batches are immutable provenance; attempt
   lifecycle/retry lives in a separate job record. (ADR-0003)
4. **GHI is never POA.** No transposition; no ambient→cell. Unknown stays unknown.
   (ADR-0004)
5. **Replay is idempotent on observations**, but is *not* the same as reproducing
   batch lineage. (ADR-0005)
6. **Provider governance is explicit and audited**: default-off catalog, default-deny
   licensing, durability gate, platform-admin lifecycle, append-only audit. (ADR-0006)

## Authoritative source-of-truth references (code, [BUILT])

- Data model: `backend/ilios-server/app/models/weather.py`
  (migrations `ff32_weather_provenance_foundation`, `ff38_weather_provider_framework`).
- API + gates: `backend/ilios-server/app/routers/weather.py`.
- Resolver boundary: `WeatherResolver.resolve_window` →
  `expected_service._load_bucket_inputs` → `compute_expected_buckets` →
  `compute_site_expected_period_effective`.
- Prior design docs:
  `../third_party_weather_provider_framework_audit.md`,
  `../third_party_weather_provider_framework_phase_a_d_implementation_plan.md`,
  `../third_party_weather_provider_framework_phase_d5_operational_readiness_plan.md`.

## How to read it

- A reviewer approving/blocking **Phase E** should read `adrs.md` (esp. ADR-0001,
  -0002, -0004) and `phase_e_readiness_assessment.md`.
- An **operator** running the system should read `admin_guide.md`, `runbooks.md`,
  and `disaster_recovery_guide.md`.
- An **engineer** picking up D.5a implementation should read `system_diagrams.md`,
  `sequence_diagrams.md`, and the D.5 plan they reference.
