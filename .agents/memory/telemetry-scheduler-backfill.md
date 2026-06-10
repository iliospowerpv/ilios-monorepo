---
name: Telemetry V2 scheduler + backfill
description: Non-obvious invariants for the native V2 telemetry scheduler/backfill triggers (bucket alignment, lock release session, cursor advance).
---

# Native V2 telemetry scheduler + backfill

The scheduler (daemon thread) and bounded backfill (sync endpoint) are *only new
triggers* over the existing `run_site_refresh` (ingestion) + `run_rollups_for_window`
(rollup) services. They live alongside the manual "Refresh Telemetry" trigger.

## Rollup window must be hour-floored at the TRIGGER, not the rollup service
When a trigger pulls a partial window (e.g. now-30m → now) and then rolls up only
that exact span, the boundary interval bucket (the hour the window starts in) gets
recomputed from only the partial slice and overwrites the previously-correct full
bucket.
**Why:** the rollup service aggregates strictly within `[window_start, window_end]`;
it does not widen to bucket edges itself.
**How to apply:** any new trigger must call rollups with
`rollup_start = floor_to_hour(window_start)` and `bucket_sizes` including the
largest requested bucket (`1h`). This flooring belongs in the trigger, NOT inside
the rollup service. All three triggers now floor: the scheduler/backfill via
`run_ingestion_with_rollup`, and the manual-refresh endpoint (`refresh_site_readings`
in `app/routers/telemetry/v2.py`) which floors its own direct `run_rollups_for_window`
call. Note a symmetric, still-open end-boundary gap: `window_end` is NOT ceiled, so
an explicit historical window ending mid-hour recomputes the trailing 1h bucket from
a partial slice (self-heals on any later overlapping run; default "now"-ending
refreshes are inherently partial at the tail anyway).

## Lock release after an error must use a FRESH session
The DB row lock (`lock_token`/`locked_until`, claimed via one atomic conditional
UPDATE) is released in a `finally`. If the run hit an unexpected exception, the
request/run session may be in a broken transaction, so releasing on that same
session fails and strands the lock until the lease self-expires.
**Why:** SQLAlchemy session is poisoned after a failed statement.
**How to apply:** release with a brand-new `SessionFactory()` session, token-guarded
(no-op if the lease was already re-claimed). Both the runner (`_release_after_error`)
and the backfill endpoint follow this.

## Cursor advance is success-gated; backfill never moves it
`last_successful_pull_at` advances ONLY when readings sync == succeeded AND rollup
in {succeeded, skipped} (see `cursor_should_advance`). Never on `partial`. Backfill
omits cursor + next_due on `finish_run` (via the `_UNSET` sentinel) so historical
pulls can never move the live scheduled cursor.

## Gating
Runner only starts when `telemetry_scheduler_enabled` (new, default False) AND
`telemetry_v2_enabled` AND (non-prod OR durable credential store). Default-off, so
boot logs "Telemetry scheduler not started: telemetry_scheduler_enabled is false"
in dev. Cadence is a fixed whitelist {PT15M,PT30M,PT1H,PT6H,PT24H} validated at the
PUT endpoint — no ISO-8601 duration parser.

## Admin-UI lock model + timestamp parsing (frontend)
Only **backfill and the scheduler** claim the per-site lease lock; the manual
"Refresh Telemetry" trigger does **not** share it. So UI must disable
backfill/scheduler actions while `locked_until` is in the future, but must NOT try
to reconcile manual-refresh against that lock.
**Why:** a 409 "Telemetry sync is already running for this site." comes only from a
held lease (concurrent backfill or scheduled run), never from a manual refresh.
**How to apply:** treat `isLocked = locked_until > now` as "busy"; disable the
backfill button while `isLocked || backfill.isPending`; poll the scheduler (~10s)
while busy so the lock clears on its own. The `PUT /scheduler` (enable/cadence) is
config-only and never locks, so leave those controls enabled during a run.

Scheduler/backfill timestamps are **naive UTC with no `Z`/offset** (e.g.
`2026-06-10T14:30:00`). `new Date()` would read them as LOCAL time and skew every
"is the lock held / next due" comparison by the browser offset.
**How to apply:** append `Z` when no tz designator is present before parsing (see
`tabs/Telemetry/telemetryTime.ts`).

Frontend telemetry-admin gating must mirror backend `telemetry_admin_required` =
`has_platform_bypass` (`is_system_user` OR `is_global_admin`) OR role `Telemetry.admin`
OR `Settings Page.edit`. The admin-gated scheduler GET must only mount for those
users (gate the component render, equivalent to `enabled: isAdmin`) so non-admins
never fire 403s. Shared hook: `hooks/useTelemetryAdminPermission.ts`. Backend stays
authoritative regardless.
