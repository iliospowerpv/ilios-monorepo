---
name: Telemetry wizard GCP dependency
description: Why the site-level Telemetry Setup Wizard's Site/Device Mapping steps fail (spin/blank) in environments without GCP credentials.
---

# Telemetry Setup Wizard depends on GCP Secret Manager (legacy v1 path)

The **site-level** Telemetry Setup Wizard's "Site Mapping" and "Device Mapping" steps
call the **legacy v1** telemetry endpoints (e.g. `GET /api/telemetry/companies/{id}/connections/{id}/sites`).
That handler constructs `GCPSecretsManager()` → `SecretManagerServiceClient()` to read the
DAS provider token, which requires **GCP Application Default Credentials**. In any environment
without GCP ADC (notably dev, and prod until `GOOGLE_APPLICATION_CREDENTIALS_JSON` is set), this
raises `DefaultCredentialsError` and the endpoint returns **502**.

**Why this matters:** With the app's default React Query config (`new QueryClient()`, no
defaultOptions → `retry: 3` + exponential backoff), a failing fetch spins ~7s, then the step
historically rendered a blank dropdown because the query's `isError`/`error` were never read —
i.e. a *silent* failure that looks like "spins and shows nothing." Always surface query errors
in multi-step wizards; don't assume data-only rendering.

**Two telemetry systems coexist:**
- **Legacy v1** — `connections` + `get_connection_remote_sites`, live calls gated on GCP Secret Manager. Used by the site-level wizard.
- **V2** — `provider-accounts` + `external-sites`, DB-backed (`TelemetryExternalSite` table), works without live GCP. Used by portfolio-admin. Returns 200 even when v1 502s.

**How to apply:** If telemetry site/device mapping "doesn't work" in dev or a fresh prod, suspect
missing GCP ADC first (check logs for `DefaultCredentialsError`), not app logic. The strategic fix
to make the wizard work without GCP is to migrate its Site Mapping step onto the V2 `external-sites`
endpoint; the stopgap is configuring GCP credentials.
