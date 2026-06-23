---
name: Dev CORS origin allow-list brittleness (Preview login)
description: Static dev CORS allow-list snapshots one REPLIT_DEV_DOMAIN at startup; any other Replit preview origin gets preflight 400 and blocks login. Fixed with a dev-only allow_origin_regex.
---

# Dev CORS allow-list is brittle for Replit Preview

The `ilios-server` dev CORS allow-list (`_resolve_cors_origins` in `app/main.py`) is a static snapshot of `localhost` variants + the single `REPLIT_DEV_DOMAIN` read at process startup. The FE (`rea-investment-fe`) calls the BE cross-origin (`baseURL = REACT_APP_URL`, e.g. `https://<id>.picard.replit.dev:8000`), so every API call has an OPTIONS preflight.

**Symptom that looks like an auth bug but isn't:** login "fails" with `OPTIONS /api/auth/login -> 400` (body `Disallowed CORS origin`) in the backend logs, and the `POST` never runs — so correct credentials are irrelevant. Verify the password separately (bcrypt `checkpw` against the stored hash) to rule auth out fast; the real gate is the preflight.

**Why the static list breaks:** the browser's Origin can differ from the one snapshotted — a rotated dev domain, a port-specific preview host, or a stale Preview tab carrying a previous domain. Starlette CORS rejects a non-matching preflight Origin with HTTP 400.

**Fix (in place):** `_resolve_cors_origin_regex()` returns `https://([a-z0-9-]+\.)*(replit\.dev|replit\.app)(:\d+)?` and is passed as `allow_origin_regex` to `CORSMiddleware` alongside the static `allow_origins`. It is intentionally returned ONLY when NOT production-like AND `CORS_ALLOWED_ORIGINS` is unset. Production stays locked to the explicit list. Starlette uses `fullmatch()` for the regex so it's effectively anchored (no path/suffix bypass), and `allow_credentials=True` still works because the matched specific origin is reflected.

**How to apply:** don't "fix" a Preview login failure by touching `authentication.py`/`auth.py` until you've checked the preflight status. Don't widen prod CORS. If a future change must read a custom response header cross-origin, also see `cors-expose-headers.md`. After a backend restart, the user may still need to hard-refresh/reopen the Preview tab to clear stale-origin browser state.
