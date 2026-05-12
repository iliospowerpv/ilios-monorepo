# ILIOS Production Readiness & Roadmap
**Audit date:** 2026-05-12
**Audit scope:** Codebase-grounded review of the Ilios REA Investment Platform after first publish to `app.iliospower.com`.
**Audit goal:** Identify what is and is not ready for live users, real customer data, real QuickBooks connections, and external operational use. Recommend the next sprint.

> No real users or customer data exist in production yet. This report assumes a zero-data starting point and prescribes work in dependency order.

---

## 1. Current Production Architecture Snapshot

### 1.1 Frontend
- **Stack:** React 18 + TypeScript, Material UI, React Query, React Router, AG Grid, Webpack 5.
- **Entry point:** `frontend/rea-investment-fe/src/index.tsx`.
- **Build:** `npm run build` in `frontend/rea-investment-fe/` (Webpack production build to `build/`).
- **Token storage:** `localStorage` (`frontend/rea-investment-fe/src/api/token-manager.ts:15`).
- **HTTP client:** Axios; tokens injected as `Authorization: Bearer <jwt>` (`frontend/rea-investment-fe/src/api/http-client.ts:7`).
- **Build-time env vars:** `REACT_APP_AG_GRID_LICENSE_KEY` (baked into bundle, visible to anyone who downloads the JS).

### 1.2 Backend
- **Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Entry point:** `backend/ilios-server/app/main.py`.
- **Process model in production:** Gunicorn + Uvicorn workers, `--preload --workers 2 --timeout 120`, bound to `0.0.0.0:5000` (`.replit:65`).
- **Lifespan:** `@asynccontextmanager lifespan` (`main.py:120-125`) runs `_validate_configuration()` then `AppInitHelper(db).set_predefined_data()` on every start (creates the system user if missing — `app/helpers/initial_setup_helper.py:34-36`).
- **SPA serving:** `app/main.py:306-333` serves the React build at `/` with `/static` mount and a catch-all that returns `index.html` (with `os.path.normpath` traversal guard at line 331).

### 1.3 Database / ORM / Migrations
- **DB:** PostgreSQL (Replit-managed Helium in production; local dev DB in workspace).
- **Driver/scheme:** `postgresql+psycopg2://`. `app/settings.py:assemble_db_uri` now reads `DATABASE_URL` first, normalizes the scheme, then falls back to `db_*`/`PG*` fields, raising a clear error if none are present.
- **ORM:** SQLAlchemy with declarative base + standardized constraint naming (`app/db/base.py`).
- **Migrations:** Alembic. Config: `backend/ilios-server/alembic/env.py`. Latest head: `ff19_add_is_global_admin_to_users.py`.

### 1.4 Auth / Sessions / Cookies
- **Library:** Custom; PyJWT for tokens, bcrypt for password hashing (`app/helpers/authentication.py:26`, `:77`).
- **Login route:** `POST /api/auth/login` (`app/routers/auth.py:19`).
- **Server-side session row:** `sessions` table (`app/models/session.py`). JWT contains `sub = session_id`.
- **Token transport:** JWT returned in JSON response body, frontend stores in `localStorage`, sent as `Authorization: Bearer …`. **No HttpOnly cookie is set.**
- **CSRF:** No middleware; not strictly required because auth is header-based, not cookie-based.

### 1.5 Environment Variables & Mode Detection
- **Settings:** `backend/ilios-server/app/settings.py`. ~28 required config fields plus optional ones; mode is detected via `environment_name`.
- **Mode-aware code paths found:** `app/services/llm_stub.py:41,153-154` blocks the LLM stub when `environment_name in {"production","prod","staging"}`. `app/helpers/telemetry/demo_data.py` checks `is_demo_mode()` which requires `DEMO_TELEMETRY=true` AND `ENVIRONMENT != "production"`.
- **`.replit` env scopes:** `[userenv.production]` and `[userenv.development]` blocks (lines 76-132). The 23 vars previously in `[userenv.shared]` were moved to both prod and dev to fix the deployment crash-loop.
- **Production URL:** `app.iliospower.com` (verified custom domain) and `ilios-monorepo.replit.app`. Privacy currently set to **Private** (Replit auth shield in front of the app).

### 1.6 Background Jobs / Workers / Cron
- **In-process:** None. No Celery, RQ, or APScheduler in `ilios-server`.
- **Out-of-process (GCP):** `backend/rea-telemetry/telemetry/jobs/` contains Cloud Run Jobs for telemetry ingestion. `backend/ilios-DocAI/src/deployment/cloud_function/` contains Cloud Functions for document enrichment. Likely scheduled via GCP Cloud Scheduler. **None of these run inside the Replit deployment; they are external infrastructure.**

### 1.7 Third-Party Integrations Currently Wired
| Integration | Status in code | Files |
|---|---|---|
| OpenAI (Replit AI Integrations) | **Live** for in-app document parsing | `app/services/in_app_parsing_service.py` |
| Replit Object Storage | **Live** | `StorageService` abstraction; default `replit` provider |
| GCP Cloud Functions (legacy) | **Live**, used for chatbot, file parse, telemetry token/sites/devices | `*_function_url` settings |
| GCP Secret Manager (telemetry V2) | **Configured but currently falling back to in-memory** in production (no GCP creds in env). See §5. |
| Mailgun | Configured | `mailgun_*` settings |
| PowerBI | Configured (workspace + client + secret) | `pbi_*` settings, `app/routers/reporting/` |
| Rombus (camera/security) | Configured | `rombus_api_key` |
| Redis | Configured | `app/redis_cache/cache.py` (caching only, no rate limiting or sessions) |
| **QuickBooks Online** | **Not implemented** — only generic `FinanceIntegration` plumbing exists. See §4. |

### 1.8 Demo / Synthetic Data Handling
- `Company.is_demo` flag distinguishes demo data at the row level.
- `is_demo_mode()` gated by env var AND non-production.
- Seed scripts `backend/ilios-server/scripts/seed_demo_environment.py`, `seed_demo_deal.py`, `seed_demo_telemetry.py`, `backfill_demo_document_tasks.py` exist as standalone scripts (not auto-invoked) but **target `DATABASE_URL`** — meaning if anyone ran them inside the production container they would seed prod. There is no environment guard inside the scripts themselves.

---

## 2. Live User Readiness Audit

| # | Finding | Severity |
|---|---|---|
| 2.1 | **JWT stored in `localStorage`** (`token-manager.ts:15`). Vulnerable to XSS token theft. Not a blocker for first internal users, but must be addressed before external users. | **High** |
| 2.2 | **CORS wildcard** with credentials: `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]` (`app/main.py:139-142`). Browsers reject `*`+credentials, but the wildcard still expands the API attack surface for anonymous-credential-less calls. | **High** |
| 2.3 | **Auto-creates a system user on every boot** (`initial_setup_helper.py:34-36`). The system_user_password env var must be strong and rotated; if it leaks, anyone can authenticate as a system identity. | **High** |
| 2.4 | **Demo seed scripts not env-guarded.** `seed_demo_*.py` will happily write to whatever `DATABASE_URL` they see. A misclick in production is destructive. | **High** |
| 2.5 | RBAC is well-architected: `access_resolver.py` is the canonical resolver; `permission_guards.py:require_module_permission` is used widely. Routes use `Depends(get_authorized_site)` / `Depends(AuthorizedUser(...))`. | OK |
| 2.6 | **List endpoints** (e.g., `list_users` in `app/routers/users.py`) filter by `get_limited_companies_ids()` for non-global-admins, so cross-company leakage is mitigated — but the pattern is implemented per-router rather than via a query-level mixin, so any new router could omit it. No automated test that asserts company isolation across endpoints. | **Medium** |
| 2.7 | **Public endpoints:** only `/health` and `/api/auth/login`. No exposed admin endpoints lack auth. | OK |
| 2.8 | **Invitation flow exists** (`UserInvitation` model with `token`+`expires_at`) and **password reset exists** (`UserPasswordRecovery`). Email verification is implicit via `is_registered` flipping after invitation acceptance. | OK |
| 2.9 | **Errors surfaced to user** are generic 500 ("Internal Server Error") via `app/utils.py:32-40`. Validation errors include field paths (standard FastAPI). | OK |
| 2.10 | **No frontend `ErrorBoundary`** — frontend uses a route-level `ErrorLayout.tsx` / `GeneralError.tsx` only. A render-time exception in a deep component will white-screen instead of showing a friendly fallback. | **Medium** |
| 2.11 | **No rate limiting** on `/api/auth/login`. Brute-force credential stuffing is unmitigated. | **High** |
| 2.12 | **No login lockout** after N failed attempts. | **High** |
| 2.13 | **Hardcoded Google API key** `AIzaSy…rlI` in `backend/ilios-DocAI/notebooks/*.ipynb` (lines 14, 72, 22). Notebooks are not deployed to prod, but the key is in the git history. | **High** (manual rotation outside this sprint) |
| 2.14 | **Hardcoded DB password** `hijgos-wevpyk-7Bibbo` in `backend/ilios-DocAI/notebooks/file_enrichment_pipeline.ipynb:517,1761`. | **High** (manual rotation) |
| 2.15 | **Dev/demo behavior visible to prod users** if `DEMO_TELEMETRY=true` accidentally set. Currently appears unset in prod scope, but no test enforces it. | **Medium** |

**Verdict:** Not yet safe for external users. Safe for **a handful of trusted internal users** once §2.4 (seed-script env guard) and §2.11/2.12 (login rate limit + lockout) are addressed.

---

## 3. Production Data Readiness Audit

### 3.1 Tables & Tenant Scoping
| Domain | Table | Tenant column | Notes |
|---|---|---|---|
| Companies | `companies` | (root) | `is_archived`, `is_demo` columns present |
| Portfolios | `user_portfolio_access` | `portfolio_hub_company_id` | Portfolio Hub Boundary Model |
| Users | `users` | `parent_company_id`, `is_global_admin` | `is_system_user` flag |
| Access | `user_company_access` | `user_id`+`company_id` | Cascade delete on both |
| Sites/Projects | `sites` | `company_id` | `is_archived` indexed |
| Documents | `documents`, `document_keys`, `files` | inherited via site | `is_archived` |
| Finance | `finance_budgets`, `finance_actuals`, `finance_vendors`, `finance_accounts` | `company_id` | Hot-path columns lack explicit single-column indexes |
| Deals | `deals`, `sales_state_transitions` | via company/site | |
| Telemetry | `das_connections`, `telemetry_external_sites`, `telemetry_sites_mapping`, `telemetry_devices_mapping`, `company_das_providers`, `telemetry_provider_catalog` | `company_id` (where applicable) | |
| Contacts | `contacts` | `company_id`/`portfolio_id` | |
| Entities | `project_entities`, `entity_relationships` | `portfolio_id` | Unique on (portfolio_id, name) |
| Audit | `audit_logs` | `user_id` | Indexed on `created_at` and `user_id` |

### 3.2 Findings

| # | Finding | Severity |
|---|---|---|
| 3.1 | **No automated DB-level tenant isolation invariant.** Cross-company leakage is enforced only at the application layer. A row-level security (RLS) policy is not feasible quickly, but a fixture-based test suite that exercises every list/read endpoint as user-of-Company-A and asserts no Company-B data is returned would catch regressions. | **High** |
| 3.2 | **Soft-delete coverage is partial.** `is_archived` exists on `companies`, `sites`, `documents`. Deals, finance records, contacts, entities have hard-delete API paths only. | **Medium** |
| 3.3 | **DELETE endpoints** for `devices`, `documents`, `finance_budgets`, `boards`, `entities` are hard-delete and not wrapped by any "are you sure" interlock or audit row beyond `AuditingMiddleware` capture. | **Medium** |
| 3.4 | **Bulk operations** (`bulk_accept_ai_values`, `bulk_create_sites_weather`, `bulk_map_devices`) lack an explicit per-row count cap or transaction-rollback test. | **Medium** |
| 3.5 | **Missing indexes** on hot-path columns: `finance_actuals.company_id`, `finance_transactions.account_id`, `documents.site_id+is_archived` composite. | **Medium** |
| 3.6 | **Migration baseline:** Alembic is at `ff19_add_is_global_admin_to_users`. No automated check that prod schema matches HEAD. A `scripts/check_prod_schema.py` that runs `alembic current` and compares to head before declaring deploy success would close the gap. | **Medium** |
| 3.7 | **No backup/restore plan documented.** Replit Helium PG provides snapshots but there is no runbook for "how do I restore Company X's data to yesterday at 3pm". | **Medium** |
| 3.8 | **Audit log completeness:** `AuditingMiddleware` captures Login/Logout/Global Admin changes. Mutations to finance, deals, sites, documents are not uniformly logged. | **Medium** |
| 3.9 | **Predefined-data on every boot** (`set_predefined_data`) creates the system user if missing. This is idempotent and safe but means a wrong env var in prod could spawn the system user with a wrong password. | **Low** (mitigated by §2.3) |

---

## 4. QuickBooks / Financials Readiness Audit

> **Critical finding:** The QuickBooks integration described in the prompt **does not exist in this codebase.** Only generic finance-integration plumbing is present. There is no OAuth flow, no `/auth/quickbooks` route, no `/callback` route, no `intuit` SDK, and no token refresh code. The "OAuth start route may be `GET /auth/quickbooks`" in the prompt is a planned-state assumption, not the current state.

### 4.1 What exists
- **DB:** `finance_integrations` table (`app/models/finance_integration.py`) with `provider_key="quickbooks"` enum value, `encrypted_credentials BYTEA`, `config_json JSONB`, `status` enum (`pending|configured|error|disabled`), `company_id` FK, unique `(company_id, provider_key)`. **Per-company ownership** is correct.
- **Service:** `app/services/finance/sync_service.py` — generic sync orchestrator.
- **Provider base:** `app/services/finance/provider.py`.
- **Registry:** `app/services/finance/registry.py` — only `GravityFinanceProvider` (stub) is registered. No `QuickBooksProvider`.
- **Routes:** `app/routers/finance/integrations.py` exposes:
  - `POST /finance/integrations/{company_id}/{provider_key}` — manual `api_key`/`api_secret` entry
  - `POST /finance/integrations/{company_id}/{provider_key}/test`
  - `POST /finance/integrations/{company_id}/{provider_key}/sync`
- **Audit:** `finance_sync_runs` table records who triggered sync and the outcome.
- **Webhooks:** **None.**
- **Production vs sandbox switching:** `base_url` can be passed in the credentials payload manually; no first-class toggle.

### 4.2 What is missing for real QBO connections

| # | Finding | Severity |
|---|---|---|
| 4.1 | **No OAuth start endpoint.** Required: `GET /api/integrations/quickbooks/connect` that builds the Intuit authorize URL with `state`, `redirect_uri`, and `scope=com.intuit.quickbooks.accounting`. | **Blocker** for QBO use |
| 4.2 | **No OAuth callback endpoint.** Required: `GET /api/integrations/quickbooks/callback` that exchanges code for tokens, stores `access_token`, `refresh_token`, `realm_id`, expiry, and associates them with the initiating user's `company_id` (validated against `state`). | **Blocker** |
| 4.3 | **No refresh handler.** Intuit refresh tokens rotate; need a wrapper that intercepts 401, refreshes, persists the new refresh token, and retries. | **Blocker** |
| 4.4 | **No `realm_id` column** on `finance_integrations`. Currently `realm_id` would have to live inside `config_json` — workable but requires explicit handling. | **High** |
| 4.5 | **No QBO API client.** Need `python-quickbooks` or direct REST against `https://quickbooks.api.intuit.com/v3/company/{realm_id}/...`. Sandbox base differs (`sandbox-quickbooks.api.intuit.com`). | **Blocker** |
| 4.6 | **Tenant/user scoping at OAuth time:** Intuit's `state` parameter must be a signed value tying the OAuth flow back to the originating user+company; otherwise a malicious user could complete a flow against another company's connection slot. | **High** |
| 4.7 | **No reconnect/disconnect UI flow** that handles `last_error` surfacing, expired refresh tokens (after 100 days inactive), or revoked grants. | **High** |
| 4.8 | **No webhooks** — fine for v1; flag for later. | **Low** |
| 4.9 | **Encryption key for `encrypted_credentials`** comes from `secret_key` in settings; rotation invalidates all stored credentials. Document this. | **Medium** |

**Verdict:** **Not safe to connect real QBO accounts.** The OAuth flow and provider implementation must be built before any customer can authorize Ilios.

---

## 5. Telemetry / Provider Account Readiness Audit

### 5.1 What exists (V2 architecture is real and well-structured)
- **Catalog table:** `telemetry_provider_catalog` (provider_key, display_name, adapter_class, config_schema, is_enabled).
- **Licensing:** `company_das_providers` maps a company to a catalog entry it is licensed for.
- **Provider Account:** `das_connections` (company_id, name, provider, secret_token_name, status, credential_status, last_sync_status). Three-state lifecycle: `active|paused|archived`.
- **External site cache:** `telemetry_external_sites`.
- **Mapping tables:** `telemetry_sites_mapping`, `telemetry_devices_mapping`.
- **Adapter abstraction:** `app/integrations/telemetry/base.py` (`ProviderAdapter` Protocol), with `CloudFunctionAdapter`, `AlsoEnergyAdapter`, `KmcAdapter` concrete classes. Loaded via `registry.py` from the catalog's `adapter_class` column.
- **Credential storage:** `GCPSecretManagerCredentialStore` with `ilios-telemetry-v2` prefix, fallback to `InMemoryCredentialStore`.
- **Lifecycle endpoints:** `POST /api/telemetry/v2/provider-accounts/{id}/test`, `.../sync-sites`, etc.
- **Demo telemetry:** `app/helpers/telemetry/demo_data.py`, gated by `DEMO_TELEMETRY=true` AND non-prod env.
- **Performance report fallback:** `app/routers/reporting/performance.py` returns demo data only for demo sites.

### 5.2 Findings

| # | Finding | Severity |
|---|---|---|
| 5.1 | **In-memory credential fallback in production.** Deployment logs show `telemetry_v2_credential_backend=in-memory (no GCP credentials in environment)`. Any provider account credentials saved in prod **will be lost on every container restart**, breaking telemetry sync. | **Blocker** for telemetry use |
| 5.2 | **Soft-delete of provider account retains GCP secret** (when GCP backend is active). Add a purge step. | **Medium** |
| 5.3 | **Demo mode bypasses BigQuery globally** if env var is set anywhere. Add a startup assertion: in prod, `DEMO_TELEMETRY` must be unset or `false`, else fail fast. | **Medium** |
| 5.4 | **Credential fingerprinting** — non-reversible hashes shown in UI for ID purposes. Acceptable; document it. | **Low** |
| 5.5 | **No background sync schedule inside Ilios** — sync is manual via `POST .../sync-sites`. Real customer use will need scheduled sync; today this lives in `backend/rea-telemetry/telemetry/jobs/` (Cloud Run Jobs). The Replit deployment cannot trigger them. | **High** for telemetry use |
| 5.6 | **Legacy v1 router** (`app/routers/telemetry/telemetry.py`) still mounted alongside v2. Document which is canonical and gate v1 behind a feature flag if you intend to retire it. | **Medium** |

**Verdict:** **Not safe** to expose telemetry to real users until §5.1 (durable credential storage) is fixed. Demo telemetry on demo sites is OK.

---

## 6. Security & Compliance Readiness

| # | Finding | Severity | Reference |
|---|---|---|---|
| 6.1 | **Hardcoded Google API key** in DocAI notebooks. | **High — manual rotation needed** | `backend/ilios-DocAI/notebooks/gemini_test.ipynb:14`, `file_enrichment_pipeline.ipynb:72`, `rerun-validation/rework-fix-borrower.ipynb:22` |
| 6.2 | **Hardcoded DB password** in DocAI notebook. | **High — manual rotation needed** | `file_enrichment_pipeline.ipynb:517,1761` |
| 6.3 | **CORS wildcard with credentials.** | **High** | `app/main.py:139-142` |
| 6.4 | **JWT in localStorage** vulnerable to XSS. | **High** | `token-manager.ts:15` |
| 6.5 | **No CSRF protection** — acceptable because of header-based bearer auth. | OK | — |
| 6.6 | **No rate limiting anywhere** — login, password reset, file upload, AI parse. | **High** | `main.py` (no `slowapi` etc.) |
| 6.7 | **No login lockout** after repeated failures. | **High** | `app/routers/auth.py` |
| 6.8 | **Pydantic validation** is used universally on request bodies. | OK | — |
| 6.9 | **File upload size limit** enforced in `in_app_parsing_service.py:89`. MIME validation present. SPA fallback uses `os.path.normpath` traversal guard. | OK | `app/main.py:331` |
| 6.10 | **Error handler** returns generic 500 without leaking traceback. Validation errors include field paths (standard FastAPI behavior). | OK | `app/utils.py:32-40` |
| 6.11 | **Log redaction** is wired (`configure_redaction()` in `app/security/redaction.py`) and called at startup (`main.py:89`). Settings init failures redact passwords (just added). | OK | — |
| 6.12 | **Frontend secrets:** `REACT_APP_AG_GRID_LICENSE_KEY` is baked into the bundle. This is normal for AG Grid licensing; ensure no other `REACT_APP_*` carries actual secrets. | **Medium** | `index.tsx:8` |
| 6.13 | **Dependency audit** has not been run as part of this audit. Run `runDependencyAudit` before public users. | **Medium** | — |
| 6.14 | **Headers (HSTS, X-Frame-Options, CSP, X-Content-Type-Options)** are not set by FastAPI in code. Replit's edge may set some; should be confirmed and complemented. | **Medium** | — |
| 6.15 | **Audit log gaps:** §3.8. | **Medium** | — |

---

## 7. Observability & Support Readiness

| # | Finding | Severity |
|---|---|---|
| 7.1 | **Structured logging** exists for telemetry/DocAI (`StructuredLoggerAdapter`) but ilios-server uses simple text format. Inconsistent. | **Medium** |
| 7.2 | **No external error reporting** (Sentry/Bugsnag). All exceptions live only in Replit deployment logs, which have a retention cap and no alerting. | **High** for support |
| 7.3 | **Health check** exists at `/health`. No `/ready` or DB-connectivity probe. | **Medium** |
| 7.4 | **Admin diagnostics:** `app/routers/admin/access_health.py` (orphaned membership detection + repair), `app/routers/debug.py` (effective-access inspection per user/company/project). Strong support primitives exist. | OK |
| 7.5 | **Audit log UI** present (`Settings → AuditLogs` tab), but coverage is limited to login/logout/global-admin events. Insufficient for support to answer "what changed on Project X yesterday". | **High** |
| 7.6 | **No integration status dashboard.** Telemetry credential failures, finance sync failures, OAuth refresh failures are spread across model `last_error` columns with no unified "ops health" page. | **High** for support |
| 7.7 | **No runbook docs in repo** beyond `scripts/grant_global_admin.py` docstring. Need: "deployment runbook", "rotate secret_key", "restore Company X", "rebuild telemetry credentials after restart". | **High** |
| 7.8 | **Frontend:** no `ErrorBoundary` (only `ErrorLayout` for routes). Add one at the app root. | **Medium** |

---

## 8. Deployment & Environment Readiness

### 8.1 Current state (verified)
- **Build cmd:** `(cd frontend && npm install && rm -rf node_modules/.cache build && CI=false npm run build) && (cd backend && pip install -r requirements.txt)` (`.replit:64`).
- **Run cmd:** `gunicorn --bind 0.0.0.0:5000 --workers 2 --worker-class uvicorn.workers.UvicornWorker --timeout 120 --graceful-timeout 30 --preload app.main:app` (`.replit:65`).
- **Port mappings:** 5000→80 (prod entry), 8000→8000 (dev API). 
- **Env scopes:** `[userenv.production]` and `[userenv.development]` properly populated (23 vars previously in `shared` were moved during this session's deployment fix).
- **DB connection:** `assemble_db_uri` now consumes `DATABASE_URL` with scheme normalization; settings init wrapped in a redacted-stderr diagnostic try/except.

### 8.2 Findings

| # | Finding | Severity |
|---|---|---|
| 8.1 | **`CI=false`** in build silences React build warnings. Acceptable but loses early warning of deprecated APIs and lint regressions. | **Low** |
| 8.2 | **No automated migration step** in deploy. Migrations must be applied manually with `alembic upgrade head` against the prod DB before code that requires them ships. There is no `alembic current == head` startup assertion. | **High** |
| 8.3 | **No rollback runbook.** Replit checkpoints exist for the codebase; the DB has snapshot-level rollback but no per-tenant restore. | **High** |
| 8.4 | **Demo seed scripts are not blocked from running in prod.** | **High** (covered in §2.4) |
| 8.5 | **Boot-time `set_predefined_data`** auto-creates the system user. This is fine but should also assert that critical telemetry catalog rows exist (or be moved to migrations). | **Medium** |
| 8.6 | **Custom domain** (`app.iliospower.com`) verified. **Privacy is currently set to Private** (Replit auth shield 307s), so external users will not see the app login page; toggle to Public when ready. | **High** for live use |
| 8.7 | **QuickBooks redirect URI** must be registered in Intuit developer portal as `https://app.iliospower.com/api/integrations/quickbooks/callback` once §4 is built. | (future) |
| 8.8 | **`--preload`** with stateful per-worker resources is generally fine for FastAPI but be cautious about DB pool fork-safety; SQLAlchemy engines should be created lazily inside a startup hook, not at import time. Audit `app/db/session.py` to confirm. | **Medium** |

### 8.3 Deployment Checklist (for every future publish)
1. ✅ All required env vars present in `[userenv.production]` (`viewEnvVars` env=production).
2. ✅ `alembic upgrade head` run against prod DB; `alembic current` matches HEAD.
3. ✅ No `DEMO_*` env var set true in prod scope.
4. ✅ `secret_key` unchanged (rotation invalidates encrypted credentials).
5. ✅ Build succeeds locally with `CI=true npm run build`.
6. ✅ Smoke test: `curl https://app.iliospower.com/health` returns 200.
7. ✅ Smoke test: login flow works on prod.
8. ✅ Privacy setting matches intent (Public for external users, Private for internal-only).
9. ✅ Replit deployment logs show `Application startup complete` for all workers.

---

## 9. Recommended Roadmap Reset

### Phase 0 — Immediate Production Hardening (before any users)
**Objective:** Make the production deployment safe to leave running with zero users.
- Block demo seed scripts from running against production DB (add env-name guard at top of each `seed_demo_*.py`).
- Add `alembic current == head` assertion at startup.
- Add startup assertion that `DEMO_TELEMETRY` is not set in prod.
- Tighten CORS to known origins (`https://app.iliospower.com`, the Replit dev domain). Remove the wildcard.
- Add basic security headers middleware (HSTS, X-Frame-Options=DENY, X-Content-Type-Options=nosniff, Referrer-Policy=strict-origin).
- Add `ErrorBoundary` at the React app root.
- Document the rollback procedure (workspace checkpoint + DB snapshot restore steps).
- **Acceptance:** All checklist items in §8.3 pass; CORS no longer wildcard; demo scripts refuse to run in prod.

### Phase 1 — First Internal Users (Jeff + small team, non-sensitive data)
**Objective:** Allow trusted internal staff to use the app daily without risk of cross-account leakage or auth abuse.
- Add login rate limiting (`slowapi` or equivalent) + per-account lockout after 5 failed attempts within 15 min.
- Switch privacy to Public.
- Configure Sentry (or equivalent) for backend + frontend error reporting.
- Backfill missing audit-log coverage on mutations to companies, sites, deals, finance, documents.
- Build a tenant-isolation test suite that asserts every list endpoint, when called as User-of-Company-A, returns no Company-B rows.
- Write the operations runbook (deploy, rollback, rotate secret_key, restore a company, recover after credential backend fail).
- **Acceptance:** Internal team can log in, create projects, attach files, and exercise core flows; Sentry captures and alerts on errors; isolation tests pass in CI.

### Phase 2 — First External / Investor Demo Users
**Objective:** Allow external invited users to access the app for demo or pilot use.
- Move JWT off `localStorage` to HttpOnly Secure SameSite=Lax cookie + introduce server-side CSRF token for state-changing requests, OR adopt short-lived access tokens + refresh-token rotation.
- Tighten CORS to the exact production origin only.
- Add public-facing legal pages (Terms, Privacy) and per-company data-access notice.
- Enforce password policy + MFA option (TOTP).
- Add invitation expiry and single-use enforcement assertion in tests.
- Add a per-company "demo / pilot / production" tier flag and gate destructive bulk operations behind it.
- **Acceptance:** External invited users can self-onboard via invitation, complete password setup, log in, and only see their own company's data; MFA available.

### Phase 3 — Real QuickBooks Connections
**Objective:** Allow customers to authorize Ilios against their real QBO companies and pull live financial data.
- Implement `QuickBooksProvider` in `app/services/finance/`.
- Implement OAuth start (`/api/integrations/quickbooks/connect`) and callback (`/api/integrations/quickbooks/callback`) routes with signed `state` containing `(user_id, company_id, csrf_nonce)`.
- Persist `realm_id`, `access_token`, `refresh_token`, `expires_at` in `finance_integrations.encrypted_credentials` (already encrypted via `secret_key`).
- Implement refresh flow: intercept 401, refresh, persist new refresh token, retry once.
- Add disconnect endpoint that revokes tokens with Intuit and zeroes credentials.
- Add reconnect UX surfaced via `status=error` + `last_error`.
- Register redirect URI in Intuit developer portal (sandbox + prod).
- Add finance sync audit row per call (already supported by `finance_sync_runs`).
- Add scheduled sync (lightweight in-process scheduler, OR a Cloud Scheduler hitting a protected internal endpoint).
- **Acceptance:** A real customer can click Connect QuickBooks, complete the Intuit OAuth screen, see their realm_id stored, trigger a sync, view finance data, and disconnect cleanly.

### Phase 4 — Real Operational Telemetry / Provider Accounts
**Objective:** Allow real customers to attach their solar telemetry provider accounts.
- Provision GCP service account credentials into prod env so the credential backend leaves "in-memory" and persists to GCP Secret Manager.
- Implement secret purge on provider account hard-delete.
- Build an internal scheduled sync (or wire Cloud Run Jobs to a protected webhook).
- Add an integration health dashboard (per-company list of `das_connections` with last_sync_status, last_error, credential_status).
- Add startup assertion: in prod, credential backend must be `gcp-secret-manager`.
- Decide v1 telemetry router fate: keep behind feature flag or remove.
- **Acceptance:** A customer can attach a real AlsoEnergy/KMC account, sync external sites, map to ilios sites, and see live data without secrets being lost on a deploy.

### Phase 5 — Scale, Support, and Operations
- Move structured logging into ilios-server (match telemetry/DocAI conventions).
- Build an admin "Ops Console" page that aggregates: pending invitations, failed sync runs, telemetry credential health, recent audit entries by company.
- Add automated DB backup verification and restore drills.
- Add usage metering per company (for billing/quota).
- Convert ad-hoc seed scripts into idempotent management commands gated by `--allow-prod` flag with confirmation.
- Add SLOs (login p95 latency, sync success rate, error rate) and alerts.

---

## 10. Proposed Next Sprint

### Sprint Name: **Phase 0 — Production Hardening Guardrails**

**Why this and not Phase 1 / QBO / Telemetry:**
The deployment is live but several items would cause real damage if hit in their current state: a wildcard CORS, an unguarded demo seed script, no startup assertion that prod is prod, no `ErrorBoundary`, and a system that will silently lose telemetry credentials on every restart. None of these block "the app boots" but all of them block "the app is safe to leave running while we onboard humans". They are also small, additive, low-risk — exactly the kind of work that earns trust before bigger Phase 1+ surgery.

### Objective
Add the minimum set of additive guardrails so the production deployment is safe to leave running and safe for the first internal users to log into during Phase 1.

### Implementation Tasks

1. **Demo seed-script production guard** *(safety; ~30 min)*
   - In each of `scripts/seed_demo_environment.py`, `scripts/seed_demo_deal.py`, `scripts/seed_demo_telemetry.py`, `scripts/backfill_demo_document_tasks.py`: at top of `__main__`, refuse to run if `settings.environment_name in {"production","prod","staging"}` unless `--allow-prod` is passed. Print clear refusal message.

2. **Startup environment assertions** *(safety; ~1 hr)*
   - In `app/main.py:_validate_configuration()`, when `environment_name == "production"`:
     - Assert `os.environ.get("DEMO_TELEMETRY","false").lower() != "true"`.
     - Assert credential backend resolves to `gcp-secret-manager` OR log a single loud `WARNING: telemetry credentials non-durable` (do not fail boot, since today it is in-memory; turn this into an assertion in Phase 4).
     - Assert `alembic current` head matches code's `HEAD` (use `alembic.config.Config` + `ScriptDirectory`).

3. **CORS tightening** *(security; ~30 min)*
   - In `app/main.py:139-142`, replace `allow_origins=["*"]` with an env-driven allowlist:
     - Prod: `["https://app.iliospower.com", "https://ilios-monorepo.replit.app"]`.
     - Dev: include the Replit dev domain via `REPLIT_DEV_DOMAIN`.
   - Keep `allow_credentials=True`; restrict `allow_methods` to `["GET","POST","PUT","PATCH","DELETE","OPTIONS"]`; keep `allow_headers=["*"]` for now (Authorization + content-type are needed; tightening can come later).

4. **Security headers middleware** *(security; ~30 min)*
   - Add a small middleware that sets on every response:
     - `Strict-Transport-Security: max-age=63072000; includeSubDomains`
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `Referrer-Policy: strict-origin-when-cross-origin`

5. **Frontend ErrorBoundary** *(reliability; ~45 min)*
   - Add a `<RootErrorBoundary>` at `frontend/rea-investment-fe/src/index.tsx` wrapping the App tree. Render a friendly "Something went wrong — please refresh" panel on render-time errors and emit the error to console (Sentry hook will be added in Phase 1).

6. **Operations runbook** *(support; ~1 hr)*
   - Create `docs/RUNBOOK.md` with sections: (a) how to deploy and verify, (b) how to roll back code, (c) how to roll back DB, (d) how to grant/revoke global admin, (e) how to rotate `secret_key` (and the consequence: re-prompt every connected integration for credentials), (f) how to reset a stuck "Promote" phase.

7. **Smoke tests as a script** *(reliability; ~45 min)*
   - `scripts/smoke_test_prod.py` that hits `/health`, attempts `/api/auth/login` with a known test user, and asserts `/api/auth/me` returns 200. Document running it after every publish in the runbook.

### Files Affected
- `backend/ilios-server/scripts/seed_demo_environment.py`, `seed_demo_deal.py`, `seed_demo_telemetry.py`, `backfill_demo_document_tasks.py`
- `backend/ilios-server/app/main.py` (CORS + headers middleware + `_validate_configuration`)
- `frontend/rea-investment-fe/src/index.tsx` (ErrorBoundary wrap)
- `frontend/rea-investment-fe/src/components/RootErrorBoundary.tsx` (new)
- `docs/RUNBOOK.md` (new)
- `backend/ilios-server/scripts/smoke_test_prod.py` (new)

### Data Model Changes
**None.** This sprint is intentionally code-only.

### API Changes
**None.** Existing endpoints unchanged. CORS allowlist is server-side only.

### UI Changes
**None visible** under happy path. Error boundary fallback only renders on render-time exceptions.

### Security Implications
- CORS becomes restrictive; any other Ilios-derived frontend on a different host will need to be added to the allowlist.
- Security headers may break embedding the app in an iframe (intentional — `X-Frame-Options: DENY` is the right default).

### Test/Validation Checklist
- ✅ Existing dev backend boots cleanly (no startup assertion failures).
- ✅ Production deploy boots; `_validate_configuration` log line confirms prod-mode assertions all passed.
- ✅ `curl -H "Origin: https://malicious.example" https://app.iliospower.com/api/...` does not get a permissive CORS response.
- ✅ `curl -I https://app.iliospower.com/` shows the four new security headers.
- ✅ Login still works in production; happy-path RBAC unchanged.
- ✅ Running `python scripts/seed_demo_environment.py` against production DATABASE_URL refuses with a clear message.
- ✅ React app root no longer white-screens on a forced render error (verify by temporarily throwing in a component in dev).
- ✅ `scripts/smoke_test_prod.py` exits 0 against the live prod URL.

### Explicitly Out of Scope
- Token storage migration (localStorage → cookie) — this is a Phase 2 item and requires CSRF rework.
- Sentry / external error reporting — Phase 1.
- Login rate limiting — Phase 1 (next sprint after this).
- Any QuickBooks work — Phase 3.
- Migrating the telemetry credential backend off in-memory — requires GCP service account provisioning, which the user may want to defer; flag-only this sprint.
- Touching the existing OAuth / dashboard / RBAC code beyond the CORS line.

---

## Executive Summary

| Question | Answer |
|---|---|
| Is Ilios safe for live users today? | **No.** Login has no rate limit / lockout; demo seed scripts can execute against prod; CORS is a wildcard. Safe for **a couple of trusted internal users** today provided no one runs a seed script. |
| Is Ilios safe for real customer data today? | **Not yet.** Tenant isolation is enforced application-side without an automated test suite; soft-delete coverage is partial; no migration-state assertion at startup. |
| Is Ilios safe for real QuickBooks connections today? | **No.** The QuickBooks integration described in the prompt **does not exist in code** beyond a generic finance-integration table and a stub provider. OAuth start, callback, refresh, sync, and reconnect must all be built. |
| Is Ilios safe for external customer access today? | **No.** No rate limiting, no MFA, no Sentry, JWT in localStorage, wildcard CORS, no formal runbook. Privacy currently set to Private (Replit shield) — fine while bootstrapping. |
| **Top 5 blockers** | (1) Demo seed scripts can run in prod with no env guard. (2) Login has no rate limit or account lockout. (3) Telemetry V2 credentials silently fall back to in-memory in prod, so any real account would lose credentials on every restart. (4) Hardcoded Google API key + DB password in DocAI notebooks (manual rotation required outside this sprint). (5) The QuickBooks integration referenced as a constraint **does not exist** — must be built before any customer can connect. |
| **Recommended next sprint** | **Phase 0 — Production Hardening Guardrails** (see §10). Small, additive, no schema changes, no OAuth changes, no API changes. Brings the app from "running in production" to "safe to leave running while Phase 1 onboards internal users." |

---
*End of report.*
