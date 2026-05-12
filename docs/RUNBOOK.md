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

## 11. What Happens if Telemetry V2 Credentials are In-Memory

The telemetry V2 credential store auto-selects between GCP Secret Manager
and an in-memory fallback (`backend/ilios-server/app/integrations/telemetry/credential_store.py`).
Production currently runs **in-memory** because no GCP service-account
credentials are configured in the production env scope.

Consequences:
- Any provider-account credentials saved through the V2 telemetry flow live
  only in the gunicorn worker's process memory.
- They are lost when the container restarts (for any reason: deploy, crash,
  Replit infra event).
- Customers would need to re-enter credentials after every restart — not
  acceptable for live use.

For now (Phase 0):
- Do **not** ask customers to attach real provider accounts.
- The boot log prints a `PRODUCTION WARNING` block when this state is detected.
- Demo telemetry on `is_demo=true` companies is unaffected.

A later **Phase 4** sprint will provision GCP service-account credentials and
flip this warning into a hard-fail.

---

## 12. Known Current Limitations

| Limitation | Status | Mitigation |
|---|---|---|
| **QuickBooks integration is not implemented.** Only generic `finance_integrations` plumbing exists. | Phase 3 | Do not promise or accept QBO connections. |
| **Telemetry V2 credentials are in-memory in production.** | Phase 4 | See §11. |
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
*End of runbook.*
