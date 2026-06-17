---
name: Frontend prod build ESLint gate
description: Why the deployment build can fail on lint even when the dev workflow says "No issues found"; what actually gets linted.
---

The frontend production deployment build (`CI=false npm run build`, react-scripts) fails on ESLint errors, while the dev workflow's "No issues found." only reflects TypeScript (fork-ts-checker). They are different gates.

**Why:** `.eslintrc` extends `plugin:prettier/recommended` (so `prettier/prettier` is an ERROR), plus `react/display-name` and `@typescript-eslint/no-unused-vars` are errors. In a production build, `eslint-webpack-plugin` runs with `failOnError: true`, so any of these error-level lint findings abort the build with "Failed to compile [eslint]". The dev server does NOT surface these (it type-checks only), so prettier/display-name/unused-import violations sail through dev and only blow up at publish time.

**How to apply:** When a publish/deploy build fails but dev is green, suspect ESLint, not TypeScript. Reproduce with `npx eslint . --ext .ts,.tsx --quiet` (errors only) from `frontend/rea-investment-fe`. Most are auto-fixable: `npx prettier --write <files>`. The non-auto-fixable ones are usually `react/display-name` (name the component/renderer function instead of an anonymous arrow) and `no-unused-vars` (remove the import).

**Test files do NOT block the build.** `eslint-webpack-plugin` (v3.x) lints only files collected from `compilation.hooks.succeedModule` — i.e. modules actually imported into the production bundle. Test files (`*.test.tsx`, `__tests__/`) are never imported into the bundle, so they are never linted by the build even though `.eslintignore` doesn't exclude them and a standalone `eslint .` will report them. So lint errors confined to test files are non-blocking lint debt, not a publish blocker. (Common test-only error: `@typescript-eslint/no-var-requires` from the intentional `require('react')` inside hoisted `jest.mock` factories — do NOT convert those to imports; it breaks the mock.)
