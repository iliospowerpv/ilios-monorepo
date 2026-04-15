# Documentation Requirements

Documentation is mandatory for every feature in the Ilios platform. Undocumented features are treated as incomplete. This document establishes the governance rules and developer checklist that must be followed for all changes.

## Core Rule

**Any new or modified module, page, workflow, report, dashboard, field, metric, status, navigation item, setting, permission behavior, integration, or data concept must have corresponding documentation updates before the work is considered complete.**

This includes:

- Help content (user-facing articles)
- FAQ updates
- Glossary entries (when new terms are introduced)
- Route-to-help mappings in `docs/route-help-registry.json`
- Contextual help links in the UI
- Documentation coverage inventory updates in `docs/documentation-coverage.json`

## Developer Checklist

Use this checklist before submitting any feature work. Every item must be addressed.

### 1. Route-to-Help Registry
- [ ] Any new route has been added to `docs/route-help-registry.json`
- [ ] The route entry includes the correct `module`, `label`, `description`, and `helpArticles` array
- [ ] Referenced help article slugs exist in the `helpArticles` section of the registry
- [ ] Any removed routes have been deleted from the registry

### 2. Help Content
- [ ] A user-facing help article exists for the feature (in the Help & Resources section definitions)
- [ ] The article covers: what the feature does, how to use it, and any prerequisites
- [ ] If an existing article was affected, it has been updated
- [ ] New terms or concepts have glossary entries

### 3. FAQ Updates
- [ ] Common questions about the feature are addressed in the FAQs section
- [ ] Edge cases and "gotchas" are documented

### 4. Coverage Inventory
- [ ] `docs/documentation-coverage.json` has been updated with the new/modified pages
- [ ] Status indicators accurately reflect coverage (`covered`, `partial`, or `missing`)
- [ ] Module-level `overviewArticle` is set when an overview article exists

### 5. Contextual Help
- [ ] UI components include contextual help links where appropriate
- [ ] Help links point to the correct article slugs

### 6. Audit Verification
- [ ] Run `npm run docs:audit` from the `frontend/rea-investment-fe` directory
- [ ] All errors are resolved (zero errors in audit output)
- [ ] Any new warnings are acknowledged and tracked

## How to Add or Update Documentation

### Adding a New Help Article

1. **Choose an article slug**: Use lowercase, hyphenated format (e.g., `portfolio-admin-overview`).

2. **Register the article** in `docs/route-help-registry.json` under the `helpArticles` section:
   ```json
   "portfolio-admin-overview": {
     "title": "Portfolio Administration Overview",
     "section": "Getting Started",
     "status": "draft"
   }
   ```

3. **Map routes to the article** by adding the slug to the `helpArticles` array of relevant routes:
   ```json
   "/portfolio-admin": {
     "module": "portfolio-admin",
     "label": "Portfolio Admin",
     "helpArticles": ["portfolio-admin-overview"],
     "description": "Portfolio-level administration"
   }
   ```

4. **Add the article content** to the Help & Resources page definitions in `frontend/rea-investment-fe/src/pages/Help/HelpResources.tsx` (or the content system used by the Help page).

5. **Update the coverage inventory** in `docs/documentation-coverage.json`:
   - Set the page status to `covered` or `partial`
   - Set the module's `overviewArticle` if this is the module overview

6. **Update the article status** from `stub` or `draft` to `published` once content is written.

### Updating an Existing Article

1. Locate the article by its slug in `docs/route-help-registry.json`.
2. Update the article content in the Help page definitions.
3. If the article scope expanded, add it to additional route mappings.
4. Run `npm run docs:audit` to verify nothing is broken.

### Adding a New Route

1. Add the route entry to `docs/route-help-registry.json` with all required fields.
2. Either map it to an existing help article or create a new one.
3. Add the corresponding page entry in `docs/documentation-coverage.json`.
4. Run the audit to confirm the mapping is valid.

### Adding a New Module

1. Add a new module entry in `docs/documentation-coverage.json` with all its pages.
2. Create an overview article for the module.
3. Register all new routes in the route-help registry.
4. Ensure the module appears in the Help & Resources page navigation.

## Running the Documentation Audit

```bash
cd frontend/rea-investment-fe
npm run docs:audit
```

The audit checks for:
- Routes with no help article mappings
- Mappings that point to articles that don't exist in the registry
- Modules without overview articles
- Overall coverage percentage

The audit exits with code 1 if there are errors (broken references). Warnings (unmapped routes, missing overviews) are informational and should be addressed over time.

## Governance Enforcement

- Documentation gaps flagged by the audit are tracked and must be resolved
- New features without documentation are not considered complete
- The audit should be run before any feature is considered ready for review
- The route-help registry and coverage inventory are the source of truth for what is documented
