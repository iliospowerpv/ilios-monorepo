# Admin Guide — Weather Provider Framework

> **Architecture freeze (D.6). Documentation only.** This guide describes the system
> as built (A–D) and as designed (D.5). Items tagged **[DESIGNED]** are not yet
> available in the UI/API.

## 1. What the framework does (and does not)

**Does:** lets an authorized admin pull external weather (e.g. Open-Meteo) for a
site, stores it with full provenance, and shows coverage/gaps/recent pulls as
**context**.

**Does not:** feed external weather into expected-energy or baseline math. External
weather is **context-only** (ADR-0001). If you see GHI or ambient temperature from a
provider, it will **never** be treated as plane-of-array irradiance or module cell
temperature (ADR-0004).

## 2. Core concepts

| Concept | Meaning |
|---|---|
| **Provider catalog** | Global registry of adapters (e.g. Open-Meteo). Default **off**. |
| **Provider account** | Per-company credential reference (or keyless + licensing ack). |
| **Licensing acknowledgment** | Required for any non-unrestricted license class before pulling. |
| **Import (pull)** | Operator-triggered fetch of a bounded window. No scheduler. |
| **Batch** | Immutable record of one pull (hashes, API version, row count). |
| **Job** [DESIGNED] | Attempt lifecycle (queued/running/…); retry lineage; references a batch. |
| **Observation** | One measurement; idempotent on `dedupe_key`. |
| **External weather context** | Read-only site view: sources, coverage, recent pulls, `physics_usable_rows = 0`. |

## 3. Who can do what (authorization)

| Action | Required role |
|---|---|
| Read external-weather context / metrics | asset-view + company visibility |
| Create/edit provider accounts, run preview/import | telemetry_admin + company visibility |
| Enable/approve/suspend/retire a catalog provider [DESIGNED] | **platform-admin** (catalog is global) |

> The catalog is **global**. Enabling a keyless provider could expose it to **all**
> eligible companies. The D.5 design adds a company **entitlement allowlist** to scope
> this; until built, treat global-enable as an all-companies action.

## 4. Typical admin tasks (pointers to runbooks)

- Onboard/enable a provider → `runbooks.md` §1 + `rollout_checklist.md`.
- Create a company provider account (and acknowledge licensing) → `runbooks.md` §2.
- Preview then import a window → `runbooks.md` §3.
- Investigate a failed/partial import and retry → `runbooks.md` §4.
- Safely disable a provider → `runbooks.md` §5.
- Rotate credentials → `runbooks.md` §6.
- Replay / verify after data loss → `disaster_recovery_guide.md`.

## 5. Reading the External Weather Context panel

- **"Context only — not expected-eligible" banner:** always present for external
  weather. This is correct and intentional, not an error.
- **Recent pulls table:** status, window, rows, provider API version, when, error
  tooltip.
- **Coverage / gaps:** which timestamps in the requested window have observations.
- **Honest unavailable:** missing values render as **N/A**, never `0`/`0%`.

## 6. Gates you will encounter (and what they mean)

1. **Licensing gate (default-deny).** If a provider's license class is not on the
   unrestricted allowlist, you must create a company account and acknowledge the
   license before importing. A keyless restricted provider with no acknowledged
   account returns an error (HTTP 422).
2. **Durability gate.** In production-like environments, credential operations are
   blocked unless the durable credential store (GCP Secret Manager) is configured.
   Keyless flows (no secret) are unaffected.
3. **Catalog gate.** Imports require the provider to be enabled (`is_enabled`) — the
   **only** catalog check **built** today. Approval state and company entitlement are
   **[DESIGNED]** (D.5a) and not enforced yet.

## 7. What to escalate to engineering

- An external `provider_pull` observation showing `poa` or `cell` semantics (should
  be impossible — ADR-0004).
- An expected-energy chart changing after an external import (should be impossible —
  ADR-0002; expected is byte-identical).
- Any request to "use this weather for expected" — that is **Phase E** and requires
  separate review (`phase_e_readiness_assessment.md`).
