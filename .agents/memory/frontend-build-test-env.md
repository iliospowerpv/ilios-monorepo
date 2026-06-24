---
name: Frontend build/test environment truth-sources (rea-investment-fe)
description: How to actually run the React FE jest suite and trust its lint/typecheck signals — the non-obvious env gotchas that waste time.
---

# rea-investment-fe — running tests + trusting validation signals

These are environment/tooling facts, not code. They repeatedly cost time.

## Jest suite is env-wide-broken without libuuid
- Symptom: EVERY test fails with `libuuid.so.1: cannot open shared object file`.
  Chain is jsdom → `canvas` native binding → libuuid. It is NOT your test's fault.
- Fix: install the Nix system lib once via package management
  (`installSystemDependencies(["util-linux"])`, which provides `libuuid.so.1`).
  This reboots all workflows. After it, the whole suite runs.
- Run a single test file (ejected CRA jest):
  `CI=true node scripts/test.js --watchAll=false --coverage=false --testPathPattern="<name>"`.
  `resetMocks:true` is set, so set each mock's impl per-test.

## Stale eslint cache produces phantom errors AND masks real ones
- The webpack dev server's eslint plugin caches in `node_modules/.cache`.
- A stale cache can show prettier/eslint errors on files you ALREADY fixed, and
  conversely hide real violations in files you didn't touch.
- **Why:** the cached result is keyed before your edit and not invalidated.
- **How to apply:** if "webpack compiled with N error(s)" disagrees with a clean
  `npx eslint <file>`, clear `node_modules/.cache` and restart the Frontend
  workflow to get the truth. (Clearing it once surfaced a long-standing prettier
  error in an unrelated file — fix with `npx eslint --fix`, not the prettier CLI.)

## Trust fork-ts-checker for the typecheck, not raw `tsc`
- The Frontend dev server runs fork-ts-checker; its console line
  `Issues checking in progress... No issues found.` IS the real TypeScript
  typecheck passing on app source.
- Prefer it over `npx tsc --noEmit`, which is slow here and often gets
  killed at the ~120s timeout (inconclusive). Note `tsc --noEmit` ALSO flags
  pre-existing stale-mock errors in `**/__tests__/*.test.tsx` (see
  `repo-validation-known-noise.md`) — those are not regressions.

## A blocking ESLint *error* shows a full-screen "Compiled with problems" overlay
- Symptom: user reports the Frontend "crashed with a runtime error" but the app
  is actually covered by the CRA red "Compiled with problems:" overlay. The dev
  server compiles ESLint `error`-level rules as a blocking `ERROR in [eslint]`
  (`webpack compiled with N error(s)`) and the overlay hides the whole app.
- **Why:** CRA treats ESLint errors as build errors in dev; warnings do NOT block.
  prettier/prettier formatting and @typescript-eslint/no-unused-vars are errors
  here, so an unformatted/unused-var file ANYWHERE (even one you didn't touch)
  blackouts the app — it is not necessarily your diff's fault.
- **How to apply:** read the overlay/webpack log for the file+rule, `eslint --fix`
  the formatting ones, remove dead vars by hand, then clear `node_modules/.cache`
  + restart Frontend. Clean state = `webpack compiled with N warning(s)` (no
  "error"). Don't be misled by a recurring "Invalid hook call" console warning —
  check its timestamp; if it predates your merge it is pre-existing, not the crash.

## Prettier is enforced via eslint
- `.eslintrc` extends `plugin:prettier/recommended`; effective prettier config is
  `.prettierrc` (printWidth 120, singleQuote, semi, no trailing comma,
  arrowParens=avoid). The plain `npx prettier` CLI default printWidth disagrees —
  ALWAYS format with `npx eslint --fix <file>`, never the prettier CLI.
- eslint runs are slow (~30–60s) and sometimes killed (exit -1, no output) =
  inconclusive; re-run to verify, don't assume pass/fail.
