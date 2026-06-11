---
name: Telemetry V2 scheduler activation flag
description: Why scheduled telemetry pulls silently never run, and how to turn them on
---

The native V2 telemetry scheduler (in-process daemon thread, started from the FastAPI `lifespan`) is gated behind an **opt-in** setting `telemetry_scheduler_enabled` that defaults to `False`. When off, the runner thread never starts and `scheduler_should_run()` returns `(False, "telemetry_scheduler_enabled is false")` — logged once at startup.

**Symptom when off (looks like a hang/bug, isn't):** the UI schedule shows "Enabled" with a cadence, `telemetry_scheduler_state.next_due_at` is set and goes overdue, but there are **zero `scheduled`-trigger rows** in `telemetry_sync_jobs` and `last_successful_pull_at` stays NULL ("Never"). Manual refresh + backfill still work because those endpoints don't go through `scheduler_should_run()`.

**Gates that must all pass for the runner to start:** `telemetry_scheduler_enabled=True` AND `telemetry_v2_enabled=True` AND (env not prod-like OR credential store is durable). In dev, the prod durability gate is skipped.

**How to enable:** set env var **lowercase** `telemetry_scheduler_enabled=true`. The key MUST be lowercase — settings use `SettingsConfigDict(case_sensitive=True)`, so an UPPERCASE `TELEMETRY_SCHEDULER_ENABLED` is ignored. (This is why other config here uses lowercase keys like `redis_url`.) Restart the backend; on first ~60s tick the runner claims any overdue rows and runs a `scheduled` pull. Confirm via startup log `telemetry_scheduler_started` and `telemetry_scheduler_run site_id=... status=succeeded`.

**Why:** the scheduler code shipped earlier but was intentionally left flag-off until the schedule UI existed and someone decided to turn it on; the flag is the activation switch, not a bug.
