---
name: Frontend typecheck verification (rea-investment-fe)
description: How to reliably verify TS correctness in the React FE when full tsc times out in this env.
---

# Frontend typecheck verification

Whole-project `tsc --noEmit -p tsconfig.json` on `frontend/rea-investment-fe` **times out (>115s)** in this
environment and is unusable for a quick pass/fail. Same for jest.

**Reliable TS-clean signal:** the running `Frontend` workflow (react-scripts/webpack-dev-server) logs, after a
recompile, both `webpack compiled successfully` AND `No issues found.` — the second line is fork-ts-checker
reporting a clean full-project type check. A TS error instead prints `ERROR in <file>:line` + the `TSxxxx`
message. Read the newest `/tmp/logs/Frontend_*.log` (use `refresh_all_logs` first; the captured stdout can be
**stale/buffered**, so after edits restart the `Frontend` workflow to force a fresh, trustworthy compile).

**Why:** `tsc` is too slow to gate on; the dev server already runs a full type check on every save and surfaces
the verdict cheaply.

**How to apply:** after FE edits, restart `Frontend`, `refresh_all_logs`, and confirm `No issues found.` with no
`ERROR in`. A scoped `tsconfig` (extends base, narrows `include` to the touched dirs) also works but is
borderline on the 115s timeout when the incremental cache is cold, so don't rely on it as the only check.

**Barrel re-export gap (recurring):** a type can be `export`ed from its own module (e.g. `src/api/due-diligence.ts`)
yet be missing from the `src/api/index.ts` barrel. Importers that use the barrel then fail with
`TS2305: ... has no exported member 'X'`, but the dev webpack build (babel, type-erasing) still prints
`compiled successfully` — only fork-ts-checker's `No issues found.` vs `ERROR in` reveals it. When you import a
shared api type through the barrel, verify the barrel actually re-exports it (its export list is a separate manual
step from the module's own `export`). This is also why "tests pass + webpack compiled" is NOT proof of a clean TS build.
