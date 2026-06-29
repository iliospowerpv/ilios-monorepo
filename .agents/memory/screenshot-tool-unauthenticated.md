---
name: app_preview screenshot is unauthenticated
description: Why authenticated UI pages can't be screenshot-verified in this repl, and what to use instead
---

The `app_preview` screenshot tool renders the running app in a **fresh browser context that does
NOT carry the user's session cookies**. On this session-authenticated app (no test credentials
available in the env), any auth-gated route screenshots as the **Sign In** page, not the real UI —
even though the user's own browser session is logged in (its API calls return 200).

**Why it matters:** do not plan "screenshot the authenticated dashboard" as a validation step here;
it will always show the login screen and waste a screenshot call.

**How to apply / alternatives:**
- Validate backend routes via direct curl to `:8000` (expect the structured
  `{"message":"Unauthorized","code":401}` payload to confirm registration + auth gating).
- Cover engine/business logic with unit tests.
- Trust the FE webpack `No issues found.` (fork-ts-checker) as the TS-clean signal.
- For visual confirmation, hand it to the user's own authenticated session; don't ask for
  credentials just to screenshot.
