# Runbooks — Weather Provider Framework

> **Architecture freeze (D.6). Documentation only.** Procedures cover built (A–D) and
> designed (D.5) capabilities; **[DESIGNED]** steps depend on D.5a being built. Each
> runbook lists: when to use, preconditions, steps, verification, rollback.

---

## §1 — Enable / onboard a provider [DESIGNED, platform-admin]

**When:** preparing a provider (e.g. Open-Meteo) for use.
**Preconditions:** platform-admin; provider exists in catalog; entitlement decision
made (which companies).
**Steps:**
1. Review the provider's licensing class and `capabilities_json`.
2. `approve` the catalog entry (rationale required) → writes audit row.
3. `enable` the catalog entry (rationale required) → writes audit row.
4. (When built) set company **entitlement** for the pilot company only.
**Verify:** lifecycle audit drawer shows approve + enable; `GET /providers` shows
enabled+approved.
**Rollback:** `disable` (instant; no data loss) — see §5.

---

## §2 — Create a company provider account + acknowledge licensing

**When:** a provider's license class is not unrestricted (e.g. `free_noncommercial`),
or the provider needs credentials.
**Preconditions:** telemetry_admin + company visibility; in prod-like envs the durable
credential store must be configured (durability gate).
**Steps:**
1. Create the account (`POST /companies/{cid}/weather-provider-accounts`) with
   `licensing_acknowledged=true` (records who/when).
2. For keyed providers, supply credentials → stored in GCP Secret Manager; DB keeps
   only `secret_name`.
3. (Optional) run account `test` to verify credentials.
**Verify:** account `status=active`; `credential_status=verified` (if keyed);
`licensing_acknowledged_at` populated.
**Rollback:** `PATCH` account `status=paused` or `archived` (safe disable at account
level; no data loss).

---

## §3 — Preview then import a window

**When:** pulling external weather for a site.
**Preconditions:** provider enabled+approved (+entitled when built); account exists if
licensing requires it; site is the intended (ideally non-protected) site.
**Steps:**
1. **Preview** (`POST .../provider-import/preview`) with the window → confirm row
   counts and declared planes/types. Nothing is written.
2. **Import** (`POST .../provider-import`) with the same window.
**Verify:** new batch present; `external-weather-context` shows updated coverage and
the new entry in recent pulls; banner still "context only"; `physics_usable_rows=0`.
**Rollback:** none needed (additive, idempotent). To stop future pulls, disable (§5).

---

## §4 — Investigate a failed / partial import, then retry [retry is DESIGNED]

**When:** an import shows `failed` or `partial`.
**Steps:**
1. Read the job/batch `error_summary` and structured logs
   (`weather_provider_import_failed`, with site/provider/job/window).
2. Classify: provider/network error, credential error
   (`credential_status=invalid/expired`), or bad window.
3. Fix the root cause (rotate credentials §6, adjust window, wait out a provider
   outage).
4. **Retry** (`POST .../jobs/{job_id}/retry`) — same window; idempotent; new job
   linked via `parent_job_id`.
**Verify:** retry job `succeeded`; integrity check passes (DR guide); coverage
recovered.
**Rollback:** none (idempotent). The original failed job is preserved for audit.

---

## §5 — Safely disable a provider [DESIGNED, platform-admin]

**When:** provider misbehaving, licensing concern, or ending a pilot.
**Steps:**
1. `POST /providers/{key}/disable` with rationale.
**Effect:** future pulls fail the catalog gate immediately; **all** batches/
observations/context are retained and still render.
**Verify:** `GET /providers` shows disabled; a new import attempt is blocked; context
panel and history still load.
**Rollback:** `enable` again (re-approval may be required if it was retired).

---

## §6 — Rotate credentials [keyed providers]

**When:** credential expiry/compromise, or `credential_status=invalid/expired`.
**Preconditions:** prod-like envs require the durable store (durability gate).
**Steps:**
1. Update the secret in the credential store (referenced by `secret_name`).
2. Run account `test` to re-verify.
**Verify:** `credential_status=verified`; a small preview/import succeeds.
**Rollback:** revert to the prior secret value; re-test.

---

## §7 — Respond to a credential-expiry notification [DESIGNED, D.5c]

**When:** an inline notification fires (no poller — it is emitted at operator-action
time when expiry is detected).
**Steps:** run account `test` → if invalid/expired, rotate (§6) → re-run the affected
import (§3) or retry (§4).

---

## §8 — Quick triage table

| Symptom | Likely cause | Runbook |
|---|---|---|
| Import 422 on keyless provider | licensing not acknowledged | §2 |
| Credential op blocked in prod | durability gate / store not durable | §6 + ops |
| Import blocked, provider "off" | catalog disabled (`is_enabled=false`) | §1 |
| `partial`/`failed` job | provider/network/credential/window | §4 |
| Expected chart "changed"?! | **must not happen** — escalate | admin_guide §7 |
| `poa`/`cell` on external row?! | **must not happen** — escalate | admin_guide §7 |
