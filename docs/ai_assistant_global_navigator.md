# AI Assistant — Global Application Navigator

## Summary

This change turns the existing **native, read-only AI Assistant** into a proactive **global
application navigator**. Wherever the assistant is open, it now offers route-aware
**Explain / Open / Resume** action cards that either deep-link the user into an **existing** native
read view or re-prompt the existing read-only chat — without the user typing anything.

The work is **strictly additive and zero-mutation**:

- No new business logic, no duplicate APIs. The navigator is folded into the existing
  `GET /api/assistant/suggested-prompts` endpoint (a new `action_cards[]` field on its response).
- Every card wraps an **existing** native read service / route. `open` destinations are an
  **enum** — routes are derived server-side, never from free-form text.
- The assistant still **never** starts, advances, previews, or executes a workflow, and never
  mutates anything. Cards are inert deep links; `explain` cards simply re-submit a canned question
  into the read-only chat. The user always takes the action.

## Files changed

### Backend (`backend/ilios-server`)

| File | Change |
| --- | --- |
| `app/schema/assistant.py` | `AssistantActionCard.kind` Literal extended with `open`, `explain`; added optional `target_view` and `prompt`; added `action_cards: list[AssistantActionCard] = []` to `AssistantSuggestedPromptsResponse`. |
| `app/services/assistant/action_cards.py` | `VALID_KINDS += (open, explain)`; new `OPEN_TARGET_VIEWS` enum; helpers `_resolve_visible_site`, `_can_view_finance`, `_open_route`, `_open_card_dict`, `_build_open_card`; `build_action_card` gained `target_view` / `prompt` / `current_route` / `title` params plus the `open` and `explain` branches. |
| `app/services/assistant/navigator_suggestions.py` | **New.** Deterministic suggester: `_bucket(route)`, `_resolve_site_id`, `_open_run_ids`, `_collect`, `build_navigator_cards`. Pure routing + authz plumbing; everything funnels through `build_action_card`. |
| `app/routers/assistant.py` | `GET /suggested-prompts` now takes a `db_session` dependency + `AssistantContextHints`, calls `build_navigator_cards`, and returns the cards in `action_cards`. (No new route.) |
| `app/services/assistant/tools.py` | `propose_action_card` tool + spec extended with the `open` / `explain` enums (so the chat path can return the same cards). |
| `tests/test_assistant_navigator.py` | **New.** 38 unit tests for the card builder + suggester. |

### Frontend (`frontend/rea-investment-fe`)

| File | Change |
| --- | --- |
| `src/api/assistant.ts` | `AssistantActionCardKind` += `open` \| `explain`; added `target_view?` and `prompt?` to `AssistantActionCard`; added `action_cards` to `AssistantSuggestedPromptsResponse`. |
| `src/components/assistant/ActionCardItem.tsx` | `open`/`explain` labels; `explain` cards render an **Ask** button that calls `onPrompt(card.prompt)` (re-prompt, no navigation); all other kinds keep the **Open** deep-link button. Added optional `onPrompt` / `disabled`. |
| `src/components/assistant/AssistantChatPanel.tsx` | New `navigatorCards` + `onPromptCard` props; renders the proactive cards under a "Jump to / Explain" header in the empty chat state; threads `onPrompt` + `disabled` into per-message cards too. |
| `src/components/assistant/AssistantWidget.tsx` | Passes `navigatorCards={suggestedPromptsQuery.data?.action_cards}` and `onPromptCard={handleSend}`. The suggested-prompts query key already includes `location.pathname`, so cards **refetch on route change**. |

## Page → context → actions matrix

The FE sends the current `route` + `site_id`/`company_id` to `GET /suggested-prompts`. The backend
classifies the route into a bucket and offers an `explain` card, then page-relevant `open` cards,
then the caller's own resumable runs — each independently permission-gated (a denied card is simply
absent). Cards are deduped and capped at `MAX_NAVIGATOR_CARDS = 5`.

| Page (route prefix) | Bucket | Explain | Open cards offered (if permitted) | Resume |
| --- | --- | --- | --- | --- |
| `/project-hub/projects/{id}` | `project_overview` | "Explain this project" | data_room, reconciliation, site_finance | own open runs (site-scoped) |
| `/project-hub/{id}/data-room` | `data_room` | "Explain the data room" | project_overview, reconciliation | own open runs (site-scoped) |
| `/finance/sites/{id}/summary` | `site_finance` | "Explain project finance" | project_overview, data_room | own open runs (site-scoped) |
| `/reconciliation?site_id=` | `reconciliation` | "Explain reconciliation" | project_overview, data_room | own open runs (site-scoped) |
| `/project-hub/companies/{id}` | `company_hub` | "Explain this workspace" | company_finance | own open runs (company-scoped) |
| `/finance/summary?company_id=` | `company_finance` | "Explain company finance" | — | own open runs (company-scoped) |
| `/project-hub` | `project_hub` | "Explain Project Hub" | — | own open runs |
| `/workflows/...` | `workflows` | "Explain workflows" | — | own open runs |
| anything else / none | `generic` | "Explain this page" | — | own open runs |

### Open target_view → existing route (derived server-side)

| `target_view` | Route | Existing read view it wraps |
| --- | --- | --- |
| `project_overview` | `/project-hub/projects/{id}` | Project Hub overview |
| `data_room` | `/project-hub/{id}/data-room` | Data Room |
| `reconciliation` | `/reconciliation?site_id={id}` | Diligence reconciliation ladder |
| `site_finance` | `/finance/sites/{id}/summary?company_id={cid}` | Per-site finance summary |
| `company_finance` | `/finance/summary?company_id={cid}` | Company portfolio finance summary |

## Permission model (fail-closed)

Each card mirrors the **destination's own** read permission, so a card is never offered to a caller
who could not open that view directly. Authorization is delegated to the same checks the read
endpoints use — the navigator never widens scope.

| Card | Gate | Source of truth reused |
| --- | --- | --- |
| `open` project_overview | site is visible to caller | `resolve_candidate_sites` (visibility intersection) |
| `open` data_room | site visible **and** Diligence `view` | `resolve_candidate_sites` + `can_view_diligence` |
| `open` reconciliation | site visible **and** Diligence `view` | `resolve_candidate_sites` + `can_view_diligence` |
| `open` site_finance | site visible **and** Finance `view` **and** the site's company is authorized | `resolve_candidate_sites` + `_can_view_finance` + `get_authorized_company` |
| `open` company_finance | `company_id` present **and** Finance `view` **and** that company is authorized | `_can_view_finance` + `get_authorized_company` |
| `resume` | run is the caller's own and not closed | `list_user_runs` (owner-scoped) |
| `explain` | non-empty prompt (no data gate — re-prompts read-only chat only) | n/a |

`has_platform_bypass=True` bypasses module checks (matching the rest of the app). Unknown
`target_view`, missing required scope, an unauthorized site, or a missing module permission all
yield no card (`_deny`).

## Zero-mutation proof

- **No write primitives in the new/changed paths.** `navigator_suggestions.py` and the new
  `action_cards.py` branches perform only `query/get`-style reads via the reused authz helpers; they
  never call `add/commit/flush/delete/execute/start_run/advance/execute`. The unit tests assert this
  explicitly with a `MagicMock` session: `_assert_no_writes` checks `add/add_all/commit/flush/
  delete/merge/execute/bulk_save_objects` were **never** called for both the `open` and `explain`
  builders.
- **Routes are derived server-side from an enum** (`OPEN_TARGET_VIEWS` → `_open_route`). A card can
  never carry a free-form/raw route, so it cannot point at a fabricated or non-existent destination.
- **No workflow start/preview/execute.** `resume` only surfaces the caller's own already-existing
  open runs (owner-scoped `list_user_runs`); clicking a card later runs the normal human-authorized
  engine handshake in the existing UI.
- **`explain` never navigates.** The FE submits its `prompt` through the existing `sendMessage` path
  (`onPromptCard = handleSend`); it is an ordinary read-only chat turn.
- **Endpoint is unchanged in surface** — `action_cards` is an additive field on the existing
  suggested-prompts response; no new API was introduced.

## Validation

- **Backend tests:** `test_assistant_navigator.py` — **40 passed** (open allowed/denied/missing-scope/
  unknown-target; explain prompt-required; route bucketing; id coercion; dedupe; max-card cap;
  resume owner/scope/closed filtering; no-writes assertions; **finance cards denied when the
  destination company is not authorized** — both site_finance and company_finance). Full assistant
  suite (`mvp + phase1 + slice2 + slice3 + navigator`) — **132 passed**, no regressions.
- **Frontend:** webpack typecheck **"No issues found."**; `eslint` clean (exit 0) on all four
  changed files (the prod build lints bundled modules and fails on ESLint, so this matters).
- **Unauthenticated probes (fail-closed):** `GET /api/assistant/suggested-prompts` (both with and
  without scope), `POST /api/assistant/chat`, and `GET /api/assistant/config` all return **HTTP 401**
  without a session. The navigator surface inherits the assistant's existing auth gate.

## Gaps / known limitations

- **Authenticated browser screenshots were not captured.** The screenshot tool's browser carries no
  session cookies, so every auth-gated route (where the cards render) resolves to the Sign-In page.
  Validation therefore relies on the unit tests, the 401 probes, and the webpack/eslint checks. A
  manual logged-in pass is the way to eyeball the cards in situ.
- **Resume scoping is best-effort.** `_open_run_ids` filters the caller's own runs by the current
  site (or company) when known; on a generic page with no scope it surfaces any open runs (still
  owner-scoped). It never discloses another user's runs.
- **Static explain prompts.** `explain` prompts are canned per bucket (deterministic). They are not
  personalized to the specific record on the page beyond the route bucket.
- **Scope comes from EntityContext, not the URL query string.** Like the pre-existing suggested-prompts
  call, the FE sends `siteId`/`companyId` from the active `EntityContext` (the app's single source of
  truth for scope), not from query params such as `?site_id=` / `?company_id=`. On a deep-linked page
  where EntityContext is not yet populated, scoped open cards are simply absent (fail-closed) rather
  than wrong — never a leak. Deriving scope from the URL was intentionally avoided to not duplicate /
  diverge from EntityContext.

## Next recommendations

1. Add one authenticated end-to-end check (or a logged-in manual QA note with screenshots) covering
   project overview / data room / finance, to close the screenshot gap.
2. Consider an explicit endpoint-level test asserting `action_cards` shape on `GET /suggested-prompts`
   with an authenticated fixture (current coverage is via the navigator/builder unit tests + the
   slice3 no-regression suite).
3. If product wants deeper context, the `explain` prompt could optionally include the resolved
   record name (still read-only) — a small, additive enhancement.
