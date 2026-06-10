---
name: CORS expose_headers for custom response headers
description: The React FE is cross-origin; any non-safelisted response header it must read has to be in CORSMiddleware expose_headers, or the browser silently strips it.
---

# Custom response headers need CORS `expose_headers`

The `rea-investment-fe` frontend talks to `ilios-server` cross-origin (axios `baseURL` = `REACT_APP_URL`; every API call shows an OPTIONS preflight in the backend logs). The FastAPI `CORSMiddleware` is configured in `backend/ilios-server/app/main.py`.

**Rule:** If the frontend needs to *read* any response header that is not a CORS-safelisted one (the safelist is basically `Cache-Control`, `Content-Language`, `Content-Length`, `Content-Type`, `Expires`, `Last-Modified`, `Pragma`), that header **must** be added to `expose_headers=[...]` on the `CORSMiddleware`. Otherwise the browser hides it from JS even though it arrives over the wire.

**Why:** The telemetry manual-refresh/backfill cooldown returns HTTP 429 with a `Retry-After` header that the UI countdown reads via `parseRetryAfterSeconds`. It worked in same-origin tests but the header was invisible in the browser until `expose_headers=["Retry-After"]` was added. The failure is silent — no error, the header is just `undefined` in axios — so it's easy to misdiagnose as a frontend bug.

**How to apply:** When adding any feature that depends on the FE reading a custom/non-standard response header (rate-limit headers, pagination totals like `X-Total-Count`, `Location` on 201/202, etc.), add that header name to `expose_headers` in `main.py` in the same change. Test in the actual browser (cross-origin), not just curl/same-origin.
