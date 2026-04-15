# How to Add or Update Documentation

Quick-reference guide for developers. See `docs/DOCUMENTATION_REQUIREMENTS.md` for full governance rules and the mandatory documentation checklist.

## Adding a New Help Article

1. **Choose a slug** — lowercase, hyphenated (e.g., `portfolio-admin-overview`).

2. **Register it** in `docs/route-help-registry.json` under `helpArticles`:
   ```json
   "portfolio-admin-overview": {
     "title": "Portfolio Administration Overview",
     "section": "Portfolio Admin",
     "status": "draft"
   }
   ```

3. **Map routes** — add the slug to the `helpArticles` array of relevant routes in the same file.

4. **Write content** — add a new `HelpArticle` object in the appropriate file under `frontend/rea-investment-fe/src/content/help/articles/`. Follow the existing pattern with `slug`, `title`, `summary`, `category`, `audience`, `articleType`, `tags`, `searchKeywords`, `relatedArticles`, `lastUpdated`, and `body`.

5. **Update coverage** — in `docs/documentation-coverage.json`, set page status to `covered` and module `overviewArticle` if applicable.

6. **Set status** — change the article status from `draft` to `published` in the registry once content is finalized.

## Adding a New Route

1. Add the route to `docs/route-help-registry.json` with `module`, `label`, `description`, and `helpArticles`.
2. Add the page to its module in `docs/documentation-coverage.json`.
3. Map it to existing articles or create new ones.
4. For auth or redirect routes, set `"excludeFromCoverage": true`.

## Adding a New Module

1. Create a new module entry in `docs/documentation-coverage.json` with all its pages.
2. Register all routes in `docs/route-help-registry.json`.
3. Create an overview article for the module.
4. Add article files under the content directory.

## Updating Existing Content

1. Find the article by slug in the content directory.
2. Update the article body.
3. If scope changed, update route mappings in the registry.
4. Update `lastUpdated` in the article definition.

## Running the Audit

```bash
cd frontend/rea-investment-fe
npm run docs:audit
```

The audit checks:
- Routes with no help article mappings
- Article references that don't exist in the registry
- Registry articles that don't exist in the content directory
- Registry/coverage parity (routes in one but not the other)
- Status consistency between registry and coverage
- Module overview article presence

**Exit code 1** = errors found (must fix). **Exit code 0** = only warnings (informational).

## Key Files

| File | Purpose |
|------|---------|
| `docs/route-help-registry.json` | Route-to-article mappings and article definitions |
| `docs/documentation-coverage.json` | Module/page coverage status |
| `frontend/rea-investment-fe/src/content/help/articles/*.ts` | Help article content |
| `scripts/docs-audit.js` | Audit script |
| `docs/DOCUMENTATION_REQUIREMENTS.md` | Full governance rules |
| `docs/AI_DEVELOPMENT_GUARDRAILS.md` | AI agent instructions |
