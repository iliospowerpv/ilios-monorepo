---
name: Third-party weather provider framework (audit/design)
description: How external weather providers would plug into the native W0/W1/W2 domain without changing expected math; why free providers can't drive physics.
---

Full design: `docs/third_party_weather_provider_framework_audit.md` (original
audit) + `docs/third_party_weather_provider_framework_phase_a_d_implementation_plan.md`
(build plan). **Phases A–D are now SHIPPED context-only** (provider catalog +
keyless Open-Meteo adapter + credentialed accounts + gap-only idempotent import +
read-only external-weather-context endpoint + provider-admin/import FE); Phase E
(any physics use of external weather) remains DEFERRED and forbidden until the
governance + GHI→POA transposition design lands.

**Core insight (durable):** the native W0/W2 weather model is ALREADY
provider-agnostic at the storage/provenance layer. An external value is just a
`weather_observation` (batch_kind=`provider_pull`) tied to a `weather_source`
(type `external_modeled_provider`), governed by a `weather_source_profile` +
approval ledger. The enums `external_modeled_provider` / `provider_pull` already
exist. So adding a provider needs NO new value-storage primitives — the real gaps
are (1) a provider **adapter + credential + pull** layer (none exists for weather;
all native weather today is file/manual import), and (2) the **physics gate**.

**The physics gate (why "unavailable stays unavailable"):** expected math
(`expected_service._load_bucket_inputs` → `compute_expected_buckets`) consumes ONLY
POA W/m² + cell °F, via `WeatherResolver.resolve_window`'s `ResolvedWeatherBucket`.
W0 forbids GHI→POA and ambient→cell conversion. Nearly every external provider
(Open-Meteo, NOAA, Meteostat, Visual Crossing, Tomorrow.io) returns GHI + ambient →
lands as `irradiance_plane=ghi`/`temperature_type=ambient` → the resolver's POA-only
test refuses it → it can power provenance/readiness-context/cosmetic indicator but
NEVER expected math. Only solar-specialist/enterprise providers that natively emit
POA/GTI + modeled cell temp (Solcast GTI, SolarAnywhere, DTN/Vaisala) are even
candidates, and only via the EXISTING governed declaration/approval flow plus a
future GHI→POA transposition design (deferred WS-track; the only phase that could
ever change resolver behaviour).

**Reuse, don't reinvent:** mirror the Telemetry V2 provider stack —
`TelemetryProviderCatalog` → `weather_provider_catalog`; `ProviderAdapter` Protocol
→ `WeatherProviderAdapter`; `CredentialStore`/GCP Secret Manager (keys by reference,
durability gate `is_credential_store_durable`) → reuse verbatim for keyed accounts.
DB-as-cache + gap-only pulls + `dedupe_key` idempotency handle rate-limit/cost.

**Why it matters / how to apply:** when asked to "add a weather provider", do NOT
add a path that makes external GHI drive expected; build cosmetic/context/provenance
first (Phases A–D), keep resolver+expected byte-identical (golden tests), and gate
any physics use behind governance + transposition (Phase E).

**Phase D hardening (durable):**
- *Licensing gate is DEFAULT-DENY.* Only an explicit unrestricted allowlist
  (`public_domain`/`open_data`/`unrestricted`/`open`/empty) skips acknowledgement;
  every other class — incl. `free_noncommercial` (Open-Meteo) and any unknown/future
  string — requires an acknowledged per-company account, enforced in BOTH
  create-account and the pull-context resolver. `catalog.licensing_class` takes
  precedence over `capabilities_json` so stale capability metadata can't downgrade
  it. **Caveat:** blank/None is currently allowlisted (treated unrestricted) — a
  deliberate but debatable choice; make blank fail-closed only on product/legal call.
- *Rollout gap:* there is NO API/UI to enable a provider — `is_enabled` is read-only
  in routes, so turning a provider on is a manual DB flip. Flag this before any prod
  rollout; it's intentionally out of Phase-D scope.
- *Durability gate* (`_block_if_storage_not_durable`) fires ONLY when
  `environment_name` ∈ {production,prod,staging,stage,live}; dev/test keyless imports
  are unblocked. Keyless flows (no `secret_name`) never reach the gate.
- *Validating when auth is blocked:* drive the service/CRUD layer against the migrated
  dev DB on a NON-protected site (e.g. site 18), transiently flip `is_enabled` and
  re-disable in a finally. Proof obligations: persisted obs are ghi/ambient only,
  `is_modeled=True`, no poa/cell, `physics_usable_rows==0`; and
  `compute_site_expected_period_effective` + `WeatherResolver.resolve_window` are
  byte-identical before vs after the import (external source id never selected).
