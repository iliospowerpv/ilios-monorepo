---
name: AI Assistant UI analytics (adoption telemetry)
description: Privacy interpretation + drift/counting rules for the native assistant's first-party UI-interaction analytics.
---

# AI Assistant UI-interaction analytics

The native assistant emits first-party, privacy-bounded UI telemetry to `POST /api/assistant/events`
(closed event enum + server-normalized route bucket + `in_companion` bool + per-event allowlisted
detail token; `extra='forbid'`; admin-gated aggregate read via `has_platform_bypass`).

## Bounded impression telemetry is allowed under "user actions only"
`*_shown` events (`first_run_shown`, `proactive_hint_shown`) are auto-emitted on visibility — they are
impressions, not clicks — and were intentionally kept.
**Why:** an adoption funnel needs the denominator (open-rate / dismiss-rate is the whole point of the
analytics); impressions are privacy-safe (bounded enum + route bucket only, no content/ids) and are
ref-guarded to fire once per surface.
**How to apply:** read "first-party UI telemetry on user actions" as *UI-interaction telemetry driven
by the UI* (vs content capture / server-side profiling). Don't strip `*_shown` to satisfy a literal
"clicks only" reading; keep them privacy-bounded.

## Two parallel route-bucket lists must stay aligned
There are TWO independent `_ROUTE_BUCKETS`: one in `suggested_prompts.py` (route→prompt module) and
one in `ui_events_service.normalize_route` (route→analytics bucket token).
**Why:** they drift silently — if a module exists in suggested-prompts but not in the analytics list,
its adoption events collapse to the `other` bucket and the data is lost.
**How to apply:** when you add/rename a module route, update BOTH lists. Both are first-match-wins, so
list more specific prefixes first (e.g. `/portfolio-admin` BEFORE `/portfolio`,
`/operations-and-maintenance` as its own token). The analytics token set is closed (unknown→`other`).

## `assistant_opened` = closed→open transition (single counter)
`assistant_opened` is recorded once per drawer closed→open transition via a state-watching effect,
NOT per entry point.
**Why:** every open source (FAB, top-bar, help-menu, first-run/proactive CTA) must count exactly once
without double-counting; the source-specific events (`discoverability_entry_clicked`,
`first_run_opened`, `proactive_hint_opened`) provide attribution.
**How to apply:** never add `trackUi('assistant_opened')` to an individual open handler — let the
transition effect own it; add only the source-specific attribution event at the call site.
