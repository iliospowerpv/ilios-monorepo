---
name: System Settings service-health probe contract
description: How the superuser service-health dashboard probes infra without leaking secrets or blocking the request.
---

# Service-health probe contract

The superuser "Third-Party Services" dashboard probes only cheap, read-only infra
(Postgres / Redis / Object Storage) and reports configuration-only (`reachable=None`,
"Not probed") for external/billable providers — it never fabricates a reachability result.

## No-secrets guarantee is enforced by construction, not by redaction
The value returned to the client is ALWAYS a fixed, secret-free string
(configured-but-not-reachable / timed-out / probe-failed-see-server-logs). Raw probe
exception text is NEVER returned — provider SDK errors can embed tokens/DSNs/headers.
`_redact()` (URL creds + `key=value` + `Bearer` masking) is **defense-in-depth for
server logs only**; do not rely on it to sanitize a client response.

**Why:** the task's hard rule is "no secret values ever returned". Best-effort redaction
of arbitrary exception text cannot prove that, so the response path carries no detail at all.

## Time-box without blocking
Worker-thread probes must NOT use `ThreadPoolExecutor` as a context manager: leaving the
`with` block calls `shutdown(wait=True)`, which re-blocks on a hung probe even after
`future.result(timeout)` already raised. Instead submit, `result(timeout=...)`, and in
`finally` call `shutdown(wait=False, cancel_futures=True)` so a wedged probe thread is
abandoned and the request returns within the timeout.

## Postgres is probed inline (request-scoped session)
A SQLAlchemy request session is not safe to use from another thread, so Postgres is probed
inline — bounded with `SET LOCAL statement_timeout` and a `rollback()` in `finally` to reset
the timeout / clear aborted-txn state. Known residual edge (accepted for local infra):
`SET LOCAL` bounds server-side execution but not pool-checkout / TCP-connect stalls.
