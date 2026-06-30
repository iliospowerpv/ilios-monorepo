# AI Assistant — Native Adoption, Discoverability & Privacy-Bounded Analytics

> Status: implemented (additive, flag-gated behind `native_assistant_enabled`).
> Sibling surfaces: [`ai_assistant_global_navigator.md`](./ai_assistant_global_navigator.md),
> [`ai_assistant_workflow_companion.md`](./ai_assistant_workflow_companion.md).

## 1. Purpose

The native AI Assistant was already a **read-only / propose-only** helper with a global navigator
and a workflow companion. This change makes it **feel native, discoverable, and measurable** without
adding a single new capability or execution path:

- **First-run guidance** — a one-time, per-user, dismissible coachmark beside the launcher.
- **Contextual chips by module** — the static suggested-prompt buckets now cover every major module.
- **Discoverability entry points** — a top-bar button and a profile-menu item that open the **same**
  existing drawer (no second instance, no second code path).
- **Proactive in-wizard help** — a subtle, per-step, dismissible nudge while inside a guided run.
- **Companion polish** — the active run's resume card is reserved so it is never crowded out, and the
  empty-state copy/heading adapt to companion mode.
- **Privacy-bounded product analytics** — first-party UI-interaction telemetry, emitted by the FE on
  user actions only, recording **bounded enum metadata only**, surfaced behind the existing
  admin-gated usage aggregate.

### The permanent invariant (unchanged)

> **The Workflow Engine is the ONLY system that mutates state.** The assistant may
> guide / explain / summarize / recommend / deep-link, but it **NEVER** starts, previews, advances,
> resumes, executes, or governs anything, and there is **no second execution path**. Every new
> surface here is **navigational or observational**:
>
> - First-run / proactive callouts and the discoverability entries only **open the existing drawer**.
>   They never auto-open, and they never execute, preview, or start anything.
> - The resume "card" is the pre-existing inert deep link (owner-validated, fail-closed). Reserving a
>   slot for it changes ordering only — never behaviour.
> - Analytics is **write-only UI telemetry into an isolated table**, never read by any business path.

## 2. Privacy model (analytics)

Analytics is **first-party**: events are emitted by our own FE in response to a user action and sent
to our own backend. There is no third-party tag, no cross-site tracking, and no content capture.

What is recorded — and only this:

| Field | Bound | Notes |
| --- | --- | --- |
| `event` | closed enum (13 names) | Pydantic `Literal` → unknown names 422 before ingest. |
| `route` | server-normalized **bucket** token | The raw client path is reduced to a coarse bucket (entity ids discarded); a raw path is **never** stored. |
| `in_companion` | bool | Whether the user was inside a guided run. |
| `detail` | per-event **allowlisted** token | e.g. card `kind`, entry `source`, hint `kind`; anything not on the allowlist is dropped to `None`. |

What is **never** recorded: prompt or response text, message ids, entity/site/company ids, file
names, operational/business values, or any cross-user profile. The ingest schema uses
`extra='forbid'`, so a client cannot smuggle extra keys into the sink. Batches are capped (50) and
string lengths are capped.

**Read is admin-gated.** The aggregate is exposed only through the existing admin usage endpoint
(gate = `current_user.has_platform_bypass`) and reads **only** the isolated assistant tables.

### Design decision — bounded impression telemetry is allowed

The `*_shown` events (`first_run_shown`, `proactive_hint_shown`) are emitted automatically when a
callout becomes visible, i.e. they are **impressions**, not literal user clicks. This is a
deliberate decision: an adoption funnel needs the denominator. Without a "shown" count there is no
way to compute the open-rate / dismiss-rate of the first-run coachmark or the per-step nudge, which
is the entire point of the analytics in this task. Impressions remain **privacy-safe** — they carry
only the bounded event name (+ the `step_help` token for the proactive hint) and the coarse route
bucket, never content or ids. They are ref-guarded to fire **once per surface** (per user / per
`runId:stepId`), so toggling the drawer never re-counts. "First-party UI telemetry on user actions"
is therefore interpreted as *UI-interaction telemetry driven by the UI* (as opposed to content
capture or server-side profiling), which bounded impressions satisfy.

### Event vocabulary (13)

| Event | Emitted when | `detail` allowlist |
| --- | --- | --- |
| `assistant_opened` | the drawer transitions **closed→open from any source** (FAB, top-bar, help-menu, first-run / proactive CTA), counted once per open via a state-transition effect; the source-specific events below provide attribution | — |
| `assistant_dismissed` | drawer closed by the user | — |
| `prompt_submitted` | free-text prompt sent from the composer | — |
| `suggested_prompt_clicked` | a suggested-prompt chip is picked | — |
| `action_card_clicked` | any propose-only card is clicked | card `kind` (`workflow`/`sequence`/`resume`/`open`/`explain`) |
| `sources_disclosure_opened` | the per-message sources disclosure is expanded | — |
| `first_run_shown` | first-run coachmark first becomes visible | — |
| `first_run_dismissed` | first-run coachmark dismissed ("Not now"/close) | — |
| `first_run_opened` | first-run coachmark CTA opens the drawer | — |
| `proactive_hint_shown` | per-step nudge first becomes visible | `step_help` |
| `proactive_hint_dismissed` | per-step nudge dismissed | `step_help` |
| `proactive_hint_opened` | per-step nudge CTA opens the drawer | `step_help` |
| `discoverability_entry_clicked` | a top-bar/menu entry opens the drawer | `source` (`topbar`/`help_menu`/`sidebar`/`empty_state`/`module_header`) |

The FE `AssistantEntrySource` union and `_HINT_KINDS`/`_ENTRY_SOURCES`/`_CARD_KINDS` server sets are
kept as a closed vocabulary; a drift-guard test asserts the schema `Literal` and the model enum match
exactly.

## 3. Files changed

### Backend (`backend/ilios-server`)

| File | Change |
| --- | --- |
| `app/models/assistant.py` | `assistant_ui_events` table + `AssistantUiEventName` enum (registered in `db/base`). |
| `app/schema/assistant.py` | `AssistantUiEventNameLiteral`, `AssistantUiEventIn`/batch schema (`extra='forbid'`, caps), `AssistantInteractionStats` + `AssistantActionCardClickStat`; `interactions` added to `AssistantUsageResponse`. |
| `app/services/assistant/ui_events_service.py` | `normalize_route` (bucket), `normalize_detail` (per-event allowlist), `record_events`; `build_interaction_stats` for the aggregate. `_ROUTE_BUCKETS` aligned with the expanded suggested-prompt modules (due-diligence, O&M, reports, portfolio, portfolio-admin→admin **before** portfolio, home→workspace) so adoption data is not collapsed to `other`. |
| `app/services/assistant/usage_service.py` | `build_usage_summary` now folds in `build_interaction_stats`. |
| `app/routers/assistant.py` | `POST /api/assistant/events` (202, flag-gated, user from auth); admin usage endpoint returns `interactions`. |
| `app/services/assistant/suggested_prompts.py` | `_ROUTE_BUCKETS` expanded to all major modules (due-diligence, O&M, finance, reports, portfolio-admin **before** portfolio, portfolio, settings, home/Workspace). |
| `app/services/assistant/navigator_suggestions.py` | Companion cards **reserve the resume slot** so the active run is never crowded out by explain cards (ordering only; still fail-closed + read-only). |

### Frontend (`frontend/rea-investment-fe`)

| File | Change |
| --- | --- |
| `src/api/assistant.ts` | `trackEvents` (fire-and-forget, swallows errors, slices to 50); `AssistantUiEventName` type. |
| `src/components/assistant/useAssistantAnalytics.ts` | Buffered hook (3s debounce + flush on `visibilitychange` hidden + unmount); no-op when the assistant is unavailable. |
| `src/contexts/assistantLauncher/*` | **New** shared launcher context: `available`/`setAvailable`, `openRequest`, `requestOpen(source)`; non-throwing `NOOP_LAUNCHER` fallback so entries placed in shared chrome never crash. |
| `src/components/assistant/AssistantLauncherCallout.tsx` | **New** reusable, dismissible coachmark anchored beside the launcher (above/below by available space); "Not now" + a navigational CTA. |
| `src/components/assistant/AssistantWidget.tsx` | Publishes availability; first-run coachmark (per-user `localStorage`, **never** auto-open); per-step proactive nudge (per `runId:stepId`, dismissible); handles external `openRequest`; emits the impression/CTA/dismiss events; passes `companionMode`. |
| `src/components/assistant/AssistantChatPanel.tsx` | `companionMode` prop adjusts the empty-state copy + navigator heading; analytics threaded through prompt/card/sources interactions. |
| `src/components/layout/PageHeader/PageHeader.tsx` | Top-bar **AI Assistant** icon button (`source='topbar'`) + profile-menu **Ask the AI Assistant** item (`source='help_menu'`); both render only when `available`. |
| `src/components/layout/BaseLayout/BaseLayout.tsx` | `<AssistantLauncherProvider>` wraps the shell inside `WorkflowCompanionProvider`. |
| `src/modules/portfolio-admin/.../AssistantUsagePanel.tsx` | "Native adoption", "Guidance & hints", and "Action cards clicked" sections over `interactions`. |

## 4. Behavioural guarantees

- **Never auto-open.** Both callouts only *invite*; opening the drawer always requires a user click.
- **One drawer, one path.** Every entry point routes through the shared `requestOpen`, which the
  single mounted widget consumes to open the existing drawer — no second instance, no second loop.
- **Per-user / per-step idempotence (persisted).** First-run is keyed by user id in `localStorage`;
  the proactive nudge's **dismissal is persisted per user** in `localStorage` (keyed by user id +
  `runId:stepId`), so a dismissed step stays dismissed across reloads and new sessions. Impression
  events fire once per surface (ref-guarded) so toggling the drawer does not re-count.
- **Fails silently.** `trackEvents` is fire-and-forget and swallows errors; a `localStorage` failure
  degrades to "may show again", never a crash.
- **Inert availability.** Entries read `available` from the shared context and never render a
  dead button when the assistant is unreachable (flag off / unauthenticated).

## 5. Validation

- **Backend tests:** `test_assistant_navigator.py`, `test_assistant_slice2.py`,
  `test_assistant_slice3.py`, `test_assistant_analytics.py` — **97 passed** (route buckets per
  module; analytics ingest/normalization/allowlist; companion resume-slot reservation; no-writes
  assertions). No regressions.
- **Frontend:** webpack typecheck **"No issues found."**; `eslint` clean (exit 0) on every changed
  file (the prod build lints bundled modules and fails on ESLint, so this matters); webpack
  **compiled successfully**.

## 6. Gaps / known limitations

- **Authenticated browser screenshots were not captured.** The screenshot tool's browser carries no
  session cookies, so the auth-gated routes where these surfaces render resolve to the Sign-In page.
  The mockup-sandbox preview server was not stood up for these components because they are deeply
  coupled to app contexts (auth, launcher, router, theme); validation relies on the unit tests, the
  typecheck, and the lint/compile checks. A logged-in manual pass is the way to eyeball them in situ.
- **Persistence is per-browser.** Both the first-run "seen" flag and the proactive-hint "dismissed"
  flags live in `localStorage` (keyed by user id), so a brand-new device/browser will show them again.
  This is intentional — no server write for cosmetic, non-intrusive hints.
