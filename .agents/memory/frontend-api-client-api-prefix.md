---
name: FE API client /api prefix convention
description: Every rea-investment-fe API client must put `/api` in the request path; the shared httpClient baseURL is the backend origin only.
---

# Frontend API client `/api` prefix convention

In `frontend/rea-investment-fe`, the single shared axios `httpClient`
(`src/api/http-client.ts`) has `baseURL = ''` (or `REACT_APP_URL` = the backend
**origin only**, never including `/api`). Therefore **every** API-client module
must hard-code the `/api` prefix into each request path (e.g. `/api/workspace`,
`/api/auth/login`, `/api/weather`, `/api/assistant`, `/api/workflows`).

**Why:** Two modules shipped a base-path constant *without* `/api`
(`const A = '/assistant'`, `const WF = '/workflows'`) under a copy-pasted,
**false** comment claiming "httpClient baseURL already includes `/api`". Every
call 404'd. For the AI Assistant this was silent and severe: `AssistantWidget`
does `if (!configQuery.isSuccess) return null`, so the 404 on `/assistant/config`
made the whole FAB/drawer render nothing even with the backend
`native_assistant_enabled` flag on. Backend routers are mounted under `/api/...`
(see `app/main.py` `include_router(..., prefix="/api/...")`).

**How to apply:** When adding or reviewing a `src/api/*.ts` client, confirm the
path starts with `/api`. Do NOT trust the "baseURL already includes /api"
comment. Quick route-level check: the wrong path returns 404 (route absent),
the right `/api/...` path returns 401 unauthenticated (route exists, auth-gated).
