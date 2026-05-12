# iliOS Operations Runbook

This runbook is for an engineer or trusted operator who needs to deploy, verify,
roll back, or recover the iliOS production deployment.

It is intentionally specific to the current production setup:
- **Production URL:** `https://app.iliospower.com` (custom domain) and
  `https://ilios-monorepo.replit.app` (Replit-managed domain).
- **Hosting:** Replit Deployments (VM target), one container, two Gunicorn workers.
- **Database:** Replit-managed PostgreSQL (Helium), accessed via `DATABASE_URL`.
- **Frontend:** React (CRA/Webpack) build, served by the FastAPI backend from
  `frontend/rea-investment-fe/build/` at `/`.

> Last reviewed: 2026-05-12 — Phase 0 hardening sprint.

---

## 1. Production Deployment Checklist

Before clicking **Redeploy** in the Publishing pane, verify:

1. ✅ Workspace dev backend is green (`Backend` workflow shows no errors).
2. ✅ All required env vars are present in the **production** scope. From the
   workspace, run a check via the env-vars tool: every name in the table in
   §2 below should be set in `production`.
3. ✅ **Demo flags are off in production:**
   `DEMO_TELEMETRY`, `DEMO_MODE`, `USE_DEMO_DATA`, `ENABLE_DEMO` must be
   absent or `false` in the `production` env scope. (The backend now hard-fails
   on boot if any of these are truthy in production.)
4. ✅ The DB schema matches code: from a workspace shell, run
   `cd backend/ilios-server && alembic current` and `alembic heads` and
   confirm the same revision id. If different, run `alembic upgrade head`
   against production **before** publishing the new code. There is no
   automatic migration step in the deploy pipeline.
5. ✅ The frontend builds clean locally:
   `cd frontend/rea-investment-fe && CI=true npm run build`.
6. ✅ `secret_key` has not been changed since last deploy. Rotating
   `secret_key` will invalidate every encrypted credential stored in
   `finance_integrations.encrypted_credentials` — see §10.

Then click **Redeploy**.

---

## 2. Environment Variable Checklist

The full list lives in `backend/ilios-server/app/settings.py` (the `Settings`
class). At minimum the following must be set in the **production** env scope
(some, like `mailgun_api_key`, are kept as Replit Secrets and flow into both
scopes automatically):

| Variable | Notes |
|---|---|
| `secret_key` | Encrypts `finance_integrations.encrypted_credentials`. Do not rotate without §10. |
| `api_key` | Internal API auth. |
| `environment_name` | Must be `production` for prod-mode guards to engage. |
| `invitation_url` / `password_reset_url` | Should point at the prod frontend URL. |
| `system_user_password` | Auto-created system user; treat as a high-value secret. |
| `mailgun_*` | Email sending. |
| `*_function_url` | GCP Cloud Functions for chatbot, file parse, telemetry. |
| `pbi_*` | PowerBI tenant/client/secret/workspace. |
| `gcp_project_id` | Numeric. |
| `rombus_api_key` | Camera integration. |
| `ml_api_key` | DocAI. |
| `DATABASE_URL` | Auto-provisioned by Replit Helium PG. |
| `DEFAULT_OBJECT_STORAGE_BUCKET_ID`, `PRIVATE_OBJECT_DIR`, `PUBLIC_OBJECT_SEARCH_PATHS` | Replit Object Storage. |
| `REDIS_URL` | Cache. |

Optional env vars added in this sprint:
| Variable | Default | Purpose |
|---|---|---|
| `CORS_ALLOWED_ORIGINS` | (empty) | Comma-separated origins. If unset, prod defaults to `https://app.iliospower.com,https://ilios-monorepo.replit.app`. |
| `TELEMETRY_V2_CREDENTIAL_BACKEND` | `auto` | `gcp` for GCP Secret Manager, `in-memory` for ephemeral. Production currently runs `in-memory` — see §11. |

---

## 3. How to Confirm a Production Boot

After clicking Redeploy, in the Publishing logs look for, in order:

1. `starting up user application`
2. `INFO::app.main::Storage provider: replit`
3. `INFO::app.main::Environment: production (production_mode=True)`
4. Either `INFO::app.main::Production safety checks: PASSED` (good) or a
   `RuntimeError: PRODUCTION SAFETY: ...` (deploy will not become healthy).
5. `INFO::app.main::CORS allowed origins: [...]` — confirm the list contains
   `https://app.iliospower.com`.
6. `[INFO] Listening at: http://0.0.0.0:5000`
7. `[INFO] Application startup complete.` (twice — one per worker)

If you only see `========== SETTINGS INIT FAILED ==========`, the env vars are
wrong; fix them in the production env scope and Redeploy.

---

## 4. How to Confirm DB Migration Status

From a workspace shell (this connects to the dev DB by default):

```bash
cd backend/ilios-server
alembic current     # latest applied revision in *current DATABASE_URL*
alembic heads       # latest revision in code
alembic history --verbose | head
```

To check the production DB, set `DATABASE_URL` to the prod value first (use
the workspace's database tool to read it; do not commit it to a file), then
re-run `alembic current`. The two values must match before a code deploy that
depends on a new migration.

To apply pending migrations to production:

```bash
DATABASE_URL='<prod url>' alembic upgrade head
```

---

## 5. How to Run Smoke Tests

After every publish:

```bash
# Anonymous-only check (just /health):
python backend/ilios-server/scripts/smoke_test_prod.py

# Full check including login:
export ILIOS_SMOKE_USERNAME='your.test.user@example.com'
export ILIOS_SMOKE_PASSWORD='...'
python backend/ilios-server/scripts/smoke_test_prod.py
```

The script never prints credentials or tokens. Exit code `0` means all
required checks passed; `1` means at least one failed.

To smoke a specific URL:

```bash
python backend/ilios-server/scripts/smoke_test_prod.py --base-url https://ilios-monorepo.replit.app
```

---

## 6. How to Roll Back Code

1. In the Replit workspace, open the **History** sidebar.
2. Find the checkpoint just before the bad change. Each deploy creates a
   checkpoint with a message like `Published your App`.
3. Click **Restore** on that checkpoint to roll the code back.
4. Click **Redeploy** in the Publishing pane to push the rolled-back code
   to production.

Code rollback does **not** roll back database changes. If the bad deploy ran
a migration that needs reverting, see §7.

---

## 7. How to Think About DB Rollback

Replit-managed Postgres (Helium) takes automated snapshots. There is no
in-app "restore Company X to yesterday at 3pm" tool; recovery is at the
whole-database snapshot level.

Working approach for the current data volume (no real customer data yet):

1. Stop further writes by toggling deploy Privacy to **Private** if needed.
2. Open the Replit DB tool and request a point-in-time snapshot or use the
   most recent automatic snapshot.
3. Restore the snapshot to a *new* DB and inspect.
4. Once verified, swap `DATABASE_URL` in the production env scope to point
   at the restored DB and Redeploy.

For Alembic-only rollbacks of a single migration:

```bash
DATABASE_URL='<prod url>' alembic downgrade -1
```

Be aware that downgrades are only as safe as the migration's `downgrade()`
function. Review the migration before downgrading.

---

## 8. How to Grant or Revoke Global Admin

Use the dedicated script:

```bash
cd backend/ilios-server
python scripts/grant_global_admin.py --list
python scripts/grant_global_admin.py --grant alice@example.com
python scripts/grant_global_admin.py --revoke alice@example.com
```

Set `DATABASE_URL` to the prod URL to operate on production. `max_global_admins`
is enforced by `Settings` (default 3). The script handles the count check.

---

## 9. How to Avoid Running Demo Seed Scripts in Production

The four demo scripts in `backend/ilios-server/scripts/`
(`seed_demo_environment.py`, `seed_demo_deal.py`, `seed_demo_telemetry.py`,
`backfill_demo_document_tasks.py`) call `_prod_guard.refuse_in_production()`
at the top of `__main__`. If `environment_name` is `production|prod|staging`
or `DATABASE_URL` looks production-like, the script exits with code `2` and
a clear message — no DB writes happen.

To deliberately override (emergency only):

```bash
python scripts/seed_demo_environment.py --allow-prod --confirm-prod-data-write
```

Both flags must be present. There is no single-flag override.

---

## 10. What Happens if `secret_key` is Rotated

`secret_key` is the symmetric key used to encrypt
`finance_integrations.encrypted_credentials` (and any future encrypted column
that derives its key from settings).

If you rotate `secret_key`:

- Existing rows in `finance_integrations` cannot be decrypted; the integration
  tests will fail with a decrypt error and `last_error` will populate.
- Customers will need to **re-connect** every integration that stored credentials
  with the old key.
- There is no automatic re-encryption migration. If you must rotate, plan a
  dedicated maintenance window with a re-encryption script that decrypts with
  the old key and re-encrypts with the new key before changing the env value.

Rule of thumb for this sprint: **do not rotate `secret_key`.**

---

## 11. Telemetry V2 Credential Testing & Storage

This section is two readiness checks rolled together: **(a)** is credential
*testing* wired end-to-end, and **(b)** is credential *storage* durable.
Today (a) is fixed; (b) is still in-memory.

### 11.a How credential testing works (V2 native path)

The user-facing **Test Credentials** button (Portfolio Admin → Telemetry →
provider account drawer) flows through the following path:

| Layer | File | Role |
|---|---|---|
| UI button | `frontend/.../telemetry/v2/ProviderAccountDrawer.tsx` | Calls `telemetryV2Api.testProviderAccount(accountId)` |
| API client | `frontend/rea-investment-fe/src/api/telemetryV2.ts` | `POST /api/telemetry/v2/provider-accounts/{id}/test` |
| Router | `backend/ilios-server/app/routers/telemetry/v2.py` (`test_provider_account`) | Loads creds from store, dispatches to adapter |
| Adapter resolver | `app/integrations/telemetry/registry.py` (`get_adapter`) | Imports the dotted-path class stored in `telemetry_provider_catalog.adapter_class` |
| **Native AlsoEnergy adapter** | `app/integrations/telemetry/native_also_energy_adapter.py` (`NativeAlsoEnergyAdapter`) | Calls `https://api.alsoenergy.com/Auth/token` directly. **No GCP Cloud Function involved.** |

Provider catalog rows are originally seeded by Alembic migration
`ff18_telemetry_v2_introduce.py`. The `also_energy` row was switched to the
native adapter by migration `ff21_telemetry_v2_native_also_energy_adapter.py`.

| Provider | Adapter class (current) | Required fields | Path |
|---|---|---|---|
| `also_energy` | `app.integrations.telemetry.native_also_energy_adapter.NativeAlsoEnergyAdapter` | `username`, `password` | **native** (direct REST) |
| `kmc` | `app.integrations.telemetry.kmc_adapter.KmcAdapter` | `token` | legacy CloudFunction (will be migrated next sprint) |

#### Native AlsoEnergy result categories
| Category | Trigger | UI message |
|---|---|---|
| `verified` | `POST /Auth/token` returns 2xx with `access_token` | "Credentials verified" |
| `rejected` | 400/401/403 from `/Auth/token` | "Provider rejected credentials (HTTP nnn)" |
| `rate_limited` | 429 from `/Auth/token` (Retry-After honoured) | "Provider rate-limited the token request" |
| `unavailable` | 5xx, malformed JSON, missing `access_token`, or transport error after retries | "Provider unavailable" / "Provider call failed: …" |
| `configuration_missing` | Stored credentials are empty or missing required fields | "No credentials are stored for this account…" / "Missing credential fields: …" |

Credential and access-token values are *never* logged. Token is reduced to
a fingerprint (`***xxxx(len=N)`) via `app.security.redaction.fingerprint`.

### 11.a.1 Phase 0C — auth response leak closed

`POST /api/auth/login` previously returned three distinguishable bodies
on failure (`We can't find account with such email`, `Account is not
fully set up`, `The password is incorrect`), enabling account
enumeration. As of this sprint all failure paths in
`AuthenticationHandler.authenticate_user` return the same body
`{"message": "Wrong credentials", "code": 400}`, including the
router-level lockout path. Per-IP rate-limit responses remain
`HTTP 429` with the generic `"Too many login attempts. Please try again
later."` message (intentional — distinguishable from credential
failure but contains no per-account information).

Internal reason categories (`account_not_found`, `account_not_setup`,
`bad_password`, plus `lockout` / `ip_rate_limit` set at the router
layer) are still recorded on the `auth_security_events` row so
operators retain forensic granularity. Reasons are passed inside the
process via `request.state.auth_failure_reason` and never appear in any
response payload, header, or log emitted to the client.

Verified end-to-end in dev: nonexistent email and known-account /
wrong-password produce byte-identical JSON responses with HTTP 400.

### 11.b Legacy Cloud Function status

The legacy `CloudFunctionAdapter` (`cloud_function_adapter.py`) and its
shim `cloud_function_telemetry_client.py` are **kept in the codebase**
unchanged. They are still referenced by:

* `KmcAdapter` (until KMC native adapter ships next sprint)
* The non-V2 telemetry endpoints under `app/routers/telemetry/telemetry.py`

V2 `also_energy` no longer depends on either. Rolling back to the legacy
adapter is one DB row update — see §11.b.1.

#### 11.b.1 Rollback to legacy AlsoEnergy adapter

Run the down-migration:

```
alembic downgrade ff20_auth_security_events
```

This restores `telemetry_provider_catalog.adapter_class` for `also_energy`
to `app.integrations.telemetry.also_energy_adapter.AlsoEnergyAdapter`.
Stored credentials in GCP Secret Manager (or in-memory in dev) are *not*
touched, so existing accounts continue to work after rollback. The
`NativeAlsoEnergyAdapter` class file is left in place so a re-`upgrade`
can flip back to native without redeploying code.

### 11.c Storage backend selection rules

`backend/ilios-server/app/integrations/telemetry/credential_store.py::_build_default_store`
picks one backend per process:

| Order | Source | Result |
|---|---|---|
| 1 | env `TELEMETRY_V2_CREDENTIAL_BACKEND=gcp` | force GCP (boots-fail if creds missing — intentional) |
| 2 | env `TELEMETRY_V2_CREDENTIAL_BACKEND=in-memory` | force in-memory (dev only) |
| 3 | `gcp_project_id` set AND `GOOGLE_APPLICATION_CREDENTIALS_JSON` set | auto-select GCP |
| 4 | `gcp_project_id` set AND `service_account_key_file_path` exists on disk | auto-select GCP |
| 5 | otherwise | in-memory fallback + warning |

`GCPSecretsManager.__init__` (`app/helpers/telemetry/secrets_manager.py`)
honours the same priority: inline JSON env var first, key file second,
ADC last. `GOOGLE_APPLICATION_CREDENTIALS_JSON` is the **preferred
production source** because no JSON ever lands on disk in the repo.

### 11.d Required production env vars for durable storage

To turn off the warning and unlock credential save/test in production:

| Env var / setting | Value | Notes |
|---|---|---|
| `gcp_project_id` | numeric GCP project id | already set in production |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | full service-account JSON, single-line | Replit Secret. **Never** committed. Service account needs `roles/secretmanager.admin` on the project (create / addVersion / access / delete). |
| `telemetry_v2_enabled` | `true` | Flips the boot guard from "warn" to "hard-fail" if the store is non-durable. |
| `TELEMETRY_V2_CREDENTIAL_BACKEND` | unset (preferred) or `gcp` | Leaving unset uses the auto-selector. Set `gcp` to make a misconfiguration crash-loud at boot. |

After setting, redeploy and confirm boot logs show
`Telemetry V2 credential backend: durable (GCP)`.

### 11.e Production startup behaviour

`_validate_configuration` in `app/main.py` enforces:

| State | Production with `telemetry_v2_enabled=true` | Production with `telemetry_v2_enabled=false` |
|---|---|---|
| Durable backend | boot OK; logs `durable (GCP)` | boot OK; logs `durable (GCP)` |
| In-memory fallback | **HARD FAIL**: `RuntimeError("PRODUCTION SAFETY: telemetry_v2_enabled=true but the telemetry V2 credential store is in-memory…")` | boot with loud `PRODUCTION WARNING` block; routes blocked at request time (see §11.f) |

Dev/non-production is never gated.

### 11.f Route-level safety net

`_block_if_storage_not_durable` in `app/routers/telemetry/v2.py`
returns **HTTP 503** with body
`"Telemetry credential storage is not enabled for production. Contact an administrator."`
when the backend is in-memory in a production env. It guards:

- `POST /v2/companies/{company_id}/provider-accounts` (create)
- `PATCH /v2/companies/{company_id}/provider-accounts/{id}` *only when
  the request body contains `credentials.fields`* (rotate)
- `POST /v2/provider-accounts/{id}/test`
- `POST /v2/provider-accounts/{id}/sync-sites`

Renaming, archiving, listing, and the credential-audit endpoint remain
available so operators can clean up safely. No credentials are ever
written or returned in error responses.

### 11.g Sync Sites gating

V2 Sync Sites is **not disabled at the route level**. The
`POST /api/telemetry/v2/provider-accounts/{id}/sync-sites` handler is
registered and reachable; what blocks customer-visible use today is a
combination of the production durability guard, the legacy adapter wired
to KMC, and the deliberate UI button gate. Layered gates, top-down:

- **Frontend** (`ProviderAccountDrawer.tsx`, `ProviderAccountsTable.tsx`):
  the Sync Sites button is `disabled` unless
  `credential_status === 'verified'` **and** `status === 'active'`.
- **Backend production durability gate** (`v2.py::_block_if_storage_not_durable`):
  in a production environment with a non-durable credential store the
  route returns HTTP 503 before any provider call. In dev (in-memory) the
  gate is skipped.
- **Backend adapter (KMC accounts)**: KMC still resolves to `KmcAdapter`
  → `CloudFunctionAdapter`; the legacy
  `cloud_function_telemetry_client.py` shim raises `ProviderUnavailable`
  for `list_sites`. The v2 sync handler records
  `last_sync_status=failed` and **does not** zero-out existing external
  site mappings.
- **Backend adapter (AlsoEnergy accounts)**:
  `NativeAlsoEnergyAdapter.list_sites()` is fully implemented and unit-
  tested. With the durability gate satisfied (or in dev), Sync Sites for
  an AlsoEnergy account will issue a real `GET /Sites` to
  `api.alsoenergy.com` and persist the returned external sites. Mapping
  preservation rules and the approval-workflow review for end-to-end
  customer enablement are scheduled for a follow-up sprint; until that
  review lands, do **not** invite external customers to use Sync Sites.

Operator behaviour today: clicking Sync Sites returns 503 in production
(non-durable storage); in dev or once durable storage is on, it invokes
the adapter and either succeeds (AlsoEnergy) or returns a "not wired up"
ProviderUnavailable (KMC). Existing mappings are never wiped on failure.

### 11.h How to verify the backend at boot

After every redeploy, scan the Publishing logs for one of:

- `Telemetry V2 credential backend: durable (GCP)` — ✅ go.
- `telemetry_v2_credential_backend=in-memory (no GCP credentials in environment)` — ❌ stop and configure §11.d.
- `RuntimeError: PRODUCTION SAFETY: telemetry_v2_enabled=true but the telemetry V2 credential store is in-memory` — ❌ deploy crash-looped on purpose; the previous revision is still serving. Add the missing env vars and redeploy.

### 11.i How to rotate provider credentials

1. UI path (preferred): Portfolio Admin → Telemetry → account row →
   **Update Credentials** → enter new values → **Save**. The router
   appends a new version to the same GCP secret resource; the previous
   version remains accessible by version number for rollback.
2. API path: `PATCH /api/telemetry/v2/companies/{company_id}/provider-accounts/{account_id}`
   with body `{"credentials": {"fields": {…}}}`. Same compensating
   cleanup behaviour: a failed DB commit on a brand-new mint deletes the
   orphan secret, but rotated-in-place versions are intentionally
   retained for audit.

The `secret_token_name` is **not** rotated; only the secret *version*
changes. Account-id ↔ secret-name mapping is stable for the life of the
account.

### 11.j How to handle credentials entered before durability

Use the **credential audit endpoint** to find them:

```
GET /api/telemetry/v2/companies/{company_id}/provider-accounts/credential-audit
```

(Telemetry-admin only.) Response shape:

```json
{
  "company_id": 12,
  "credential_backend_durable": true,
  "missing_credentials_count": 1,
  "items": [
    {"id": 7, "name": "AlsoEnergy prod",
     "credential_status": "verified",
     "has_stored_credentials": false,
     "needs_reentry": true}
  ]
}
```

`has_stored_credentials=false` means the GCP secret resource the row
points at returns an empty payload. Operator action:

1. For each `needs_reentry: true` row, open the account in the UI.
2. Click **Update Credentials** and re-enter the values from the
   customer's source-of-truth (1Password / vendor portal / etc.). Saving
   mints a fresh durable secret and re-routes `secret_token_name` to it.
3. Re-test. The audit endpoint will then return `needs_reentry: false`.

The endpoint never returns credential values — only the boolean
presence flag. No values are recoverable from an in-memory store after
restart; do **not** attempt recovery.

### 11.k What internal users should do after the durable backend is enabled

1. Stop treating the AlsoEnergy demo company as a test target — saved
   creds are now real and persistent.
2. Run the credential-audit endpoint once per company you previously
   touched. Re-enter for any `needs_reentry: true` row.
3. The Test Credentials button should now flip the chip Verified and
   stay there across redeploys. If a redeploy breaks it, the audit
   endpoint is the first diagnostic to run.

### 11.l Approval status

| Question | Answer |
|---|---|
| Is the wiring bug fixed? | Yes (commit `c6a7d46`) |
| Is the in-memory storage hole closed? | Yes — production refuses to silently accept lost credentials. Saves/tests return 503 until §11.d is configured; with `telemetry_v2_enabled=true` the deploy hard-fails instead of booting. |
| Are credentials durable when GCP is configured? | Yes — `GCPSecretManagerCredentialStore`, secret-per-account, version-on-rotate. |
| May internal users test credentials? | **Yes**, only after §11.d. While the env vars are missing the route returns 503 with the operator-friendly message. |
| May external customers attach real accounts? | Not yet — Sync Sites is still 501 (Phase 4). |
| Should existing pre-fix saved credentials be re-entered? | **Yes** — see §11.j. |
| Does Sync Sites work end-to-end? | **No** — gated server-side until Phase 4 wiring. |

### 11.m Operator actions for Invalid status

1. Open Portfolio Admin → Telemetry, click the offending account row.
2. Note the `Last error` value (the credential rejection detail surfaces
   here verbatim from the cloud function).
3. Click **Update Credentials**, re-enter values, **Save**, then **Test
   Credentials** again.
4. If Test returns HTTP 503 "Telemetry credential storage is not enabled
   for production": the deploy is on the in-memory backend. Configure
   §11.d and redeploy.
5. If the chip still flips to Invalid: confirm the
   `telemetry_token_function_url` is reachable from the deploy by
   inspecting the deployment logs for an `Invoking telemetry provider
   adapter provider=…` line. Absence of that log line means the request
   never left the app — usually a missing env var, not bad credentials.

---

## 12. Known Current Limitations

| Limitation | Status | Mitigation |
|---|---|---|
| **QuickBooks integration is not implemented.** Only generic `finance_integrations` plumbing exists. | Phase 3 | Do not promise or accept QBO connections. |
| **Telemetry V2 credentials default to in-memory until `GOOGLE_APPLICATION_CREDENTIALS_JSON` + `telemetry_v2_enabled=true` are set in the production env scope.** Until configured, credential save/test routes return HTTP 503 instead of silently dropping data. | Configurable | See §11.c–§11.f. |
| **Telemetry V2 Sync Sites** is still wired to a 501 from the v2 cloud-function shim; existing site mappings are preserved. | Phase 4 | See §11.g. |
| **JWT is stored in `localStorage`** on the frontend. | Phase 2 | Do not invite external users until cookie migration. |
| **No login rate limiting / account lockout.** | Phase 1 (next sprint) | Use strong passwords; small audience only. |
| **No external error reporting (Sentry).** | Phase 1 | Watch deployment logs in the Publishing pane. |
| **`set_predefined_data` runs on every boot** and re-creates the system user if missing. | Acceptable | `system_user_password` must be strong. |

---

## 13. Common Recovery Recipes

### Deploy worker keeps crash-looping with `SETTINGS INIT FAILED`
- Open the Publishing logs. The redacted banner names the failing field.
- Most common cause: a required env var is missing in the **production** scope
  (the `[userenv.shared]` section of `.replit` does not propagate to deploy
  workers). Add the missing var to the `production` env scope and Redeploy.

### Promote phase stuck for >5 minutes with no new container logs
- This is a Replit infra-side issue, not a code issue. The previous revision
  is still serving.
- Cancel the in-progress deploy and click Redeploy. If it hangs again,
  contact Replit support from the workspace Help button.

### `app.iliospower.com` 307-redirects to `replit.com/__replshield`
- Deployment Privacy is set to **Private**. Open the Publishing pane →
  Settings → Privacy and toggle to **Public** when ready for users.

### CORS blocked the production frontend after a deploy
- Check the boot log for `CORS allowed origins: [...]`. The list must contain
  the exact origin the browser is loading from (scheme + host, no trailing
  slash). If wrong, set `CORS_ALLOWED_ORIGINS` in the production env scope to
  the correct comma-separated list and Redeploy.

---

## 14. Production Secret Hygiene Pass

**Date:** 2026-05-12 (Phase 0 closeout sprint).

### What was rotated

The following three values in the **production** env scope were inherited from
the development scope as plaintext defaults shared between both environments
(visible in `.replit`). Because no real users, no real production data, and no
real external integrations existed at the time of this pass, they were rotated
in place using cryptographically strong random values generated locally and
written via the env-var tool. Values were never printed to logs or chat; only
SHA-256 fingerprint prefixes were used to confirm the rotation took effect.

| Key                      | Scope       | Before         | After          |
|--------------------------|-------------|----------------|----------------|
| `secret_key`             | production  | dev default    | rotated (CSPRNG, 64-hex) |
| `api_key`                | production  | dev default    | rotated (CSPRNG, base64url) |
| `system_user_password`   | production  | dev default    | rotated (CSPRNG, base64url + complexity suffix) |

The development scope was deliberately left unchanged so local workflows keep
working with the existing dev fixtures.

### What was NOT rotated this pass

- **Database credentials** (`DATABASE_URL`, `PG*`): managed by Replit; rotating
  them is outside the app's control and would require a Helium DB credential
  reissue.
- **Third-party API keys** (`mailgun_api_key`, `rombus_api_key`, `ml_api_key`,
  `pbi_client_secret`, OpenAI key, AG Grid license): rotating these requires
  coordinating with the upstream vendor and is out of scope for this sprint.
- **Hardcoded secrets in `backend/ilios-DocAI/notebooks/*.ipynb`** (Google API
  key, DB password committed in notebook source): these still require manual
  rotation outside the app deploy. They are flagged in the production
  readiness audit (§6) and remain a follow-up item.

### Required follow-up actions after rotation

1. **Redeploy production.** Env vars are loaded at boot via Pydantic Settings;
   the new values do not take effect until the next deploy cycle. Click
   **Redeploy** in the Publishing pane.
2. **Re-bootstrap the system user account in production.** Because
   `system_user_password` was rotated, any existing system-user DB row whose
   password hash was derived from the old value can no longer be authenticated
   against. If a system user already exists in the production DB, run the
   bootstrap/reset routine for that account against production once after the
   redeploy. (Skip if no system user has been created in prod yet.)
3. **Verify boot logs** show the new `production_mode=True` block and no
   safety-check failures (see §3).

### Consequences of any FUTURE `secret_key` rotation

`secret_key` is used by `cryptography.fernet` to encrypt
`finance_integrations.encrypted_credentials` (and any future symmetric-encrypted
column). If `secret_key` is rotated again **after** real finance integration
credentials have been stored:

- All previously stored encrypted credentials become unreadable and the
  affected integrations will fail to authenticate.
- The remediation is to disconnect and reconnect every affected integration
  after rotation, which forces re-entry of the upstream credentials.
- For this reason, **once the first real finance integration is connected in
  production, treat `secret_key` as immutable** and plan any future rotation
  as a coordinated maintenance window with explicit re-connection of every
  integration.

This pass was safe to perform because no real finance integrations were yet
connected in production.

### Reminder: notebook secrets are out of scope

Hardcoded credentials inside Jupyter notebooks under
`backend/ilios-DocAI/notebooks/` are not loaded by the FastAPI app and were not
touched by this pass. They must still be rotated manually at the upstream
provider (Google Cloud / DB owner) and scrubbed from notebook source as a
separate operational task before those notebooks are run against any
sensitive data.

---

## 15. Auth Abuse Protection (Phase 0B)

The `/api/auth/login` and `/api/users/account/password-recovery` endpoints
have application-level abuse protection. State is stored in the
`auth_security_events` table (migration `ff20_auth_security_events`) so the
policy survives process restart and is consistent across the two Gunicorn
workers — Redis is **not** required.

### Policies (configurable in `app/settings.py`)

| Setting | Default | What it caps |
|---|---|---|
| `login_rate_limit_per_minute` | 10 | Failed/limited login attempts per source IP per minute |
| `login_rate_limit_per_hour` | 50 | Failed/limited login attempts per source IP per hour |
| `account_lockout_threshold` | 5 | Failed logins per account in the window before lockout |
| `account_lockout_window_minutes` | 15 | Window in which failures are counted toward lockout |
| `account_lockout_cooldown_minutes` | 15 | Cooldown after threshold; extends from the most recent failure |
| `password_reset_per_ip_per_hour` | 5 | Password reset requests per source IP per hour |
| `password_reset_per_email_per_hour` | 3 | Password reset requests per email per hour |

To tighten or relax in production, override via env (e.g.
`LOGIN_RATE_LIMIT_PER_MINUTE=5`) and redeploy.

### Response shapes (deliberate, do not change without security review)

- **Login bad credentials, account-not-found, or account-locked:** all return
  `400 {"code": 400, "message": "Wrong credentials"}` so the response does
  not disclose whether the account exists or is in lockout.
  - **Pre-existing leak (NOT closed in Phase 0B):** the underlying
    `AuthenticationHandler` still returns the more specific
    `"We can't find account with such email"` for unknown emails when the
    request reaches it (i.e. before lockout/rate-limit kicks in). Closing
    this leak requires changing the handler itself and is out of scope for
    this sprint. Lockout and rate-limit responses are already generic.
- **Login rate-limited (per IP):** `429 {"code": 429, "message": "Too many
  login attempts. Please try again later."}` with `Retry-After: 60` (or 3600
  for the per-hour bucket).
- **Password reset (any outcome — no such email, not registered, email send
  failed, throttled, success):** always returns
  `200 {"code": 200, "message": "If an account exists, password reset
  instructions will be sent."}`. This is a deliberate behavior change vs
  pre-Phase-0B, where the endpoint returned 400/422 and leaked existence
  and registration state. Frontend's success path is unchanged; the new
  response just makes failure paths indistinguishable from success.

### Operator visibility

Every login attempt and every password-reset request writes a row to
`auth_security_events` (best effort — auditing failures never break legit
auth). Sensitive values (passwords, tokens, raw email of unknown accounts)
are never stored. For unknown identifiers the row carries an HMAC-SHA256
of the normalized email keyed by `secret_key` (the same value attempts
against the same identifier hash to the same bucket; the raw email is not
recoverable from a leaked table without the secret).

Inspect recent activity via the admin endpoint (requires
`is_global_admin=True` — same gate as `/api/admin/global-admins`):

```bash
curl -H "Authorization: Bearer <admin-token>" \
  "https://app.iliospower.com/api/admin/auth-security-events?limit=200"
```

Useful filters: `?event_type=login&outcome=locked`,
`?event_type=password_reset_request&outcome=throttled`.

Or query the DB directly:

```sql
-- Top offending IPs in the last hour
SELECT ip_address, count(*) AS attempts
FROM auth_security_events
WHERE event_type = 'login'
  AND outcome IN ('failure','rate_limited','locked')
  AND created_at > now() - interval '1 hour'
GROUP BY ip_address ORDER BY 2 DESC LIMIT 20;

-- Accounts currently locked or recently locked
SELECT normalized_identifier_hash, count(*) AS failures, max(created_at) AS last_failure
FROM auth_security_events
WHERE event_type='login' AND outcome='failure'
  AND created_at > now() - interval '15 minutes'
GROUP BY 1 HAVING count(*) >= 5;
```

### Manual remediation

To clear a stuck account before cooldown expires (e.g. legitimate user
self-locked while typing on phone), delete its recent failed-login rows:

```sql
DELETE FROM auth_security_events
WHERE event_type='login' AND outcome='failure'
  AND user_id = <USER_ID>;
-- or, if user_id is null because the account was looked up by hash only:
DELETE FROM auth_security_events
WHERE event_type='login' AND outcome='failure'
  AND normalized_identifier_hash = '<HASH>';
```

The hash for a given email is reproducible from a Python shell:

```python
import hmac, hashlib
from app.settings import settings
hmac.new(settings.secret_key.encode(), 'user@example.com'.strip().lower().encode(),
         hashlib.sha256).hexdigest()
```

A successful login from the same identifier also auto-clears its failed
rows.

### What this sprint did NOT cover

Out of scope (deliberately): MFA, JWT-to-cookie migration, broader RBAC
refactor, Sentry/external alerting, telemetry credential durability,
QuickBooks. The pre-existing "We can't find account with such email" leak
in `AuthenticationHandler` is documented above and tracked for a later
sprint.

---
*End of runbook.*
