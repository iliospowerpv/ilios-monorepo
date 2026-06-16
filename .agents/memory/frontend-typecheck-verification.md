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
