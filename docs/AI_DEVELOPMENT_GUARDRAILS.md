# AI Development Guardrails

This file instructs AI agents (Replit Agent, Copilot, Cursor, or any LLM-based development assistant) on mandatory documentation practices when making changes to the Ilios platform.

## Mandatory Documentation Rule

When implementing any feature, fix, or change, the AI agent MUST also create or update the corresponding documentation. A feature is not complete until its documentation is in place.

## What Requires Documentation Updates

Any change that introduces or modifies any of the following MUST include documentation updates:

- **Module**: A new application module or section
- **Page**: A new page or view within a module
- **Workflow**: A new multi-step user workflow or process
- **Report**: A new report or analytics view
- **Dashboard**: A new dashboard or dashboard widget
- **Field**: A new data field visible to users
- **Metric**: A new KPI, metric, or calculated value
- **Status**: A new status value or lifecycle state
- **Navigation item**: A new menu item, tab, or navigation link
- **Setting**: A new user or system setting
- **Permission behavior**: A new or changed permission check
- **Integration**: A new external integration or data connection
- **Data concept**: A new entity type, relationship, or domain concept

## Required Documentation Actions

For every qualifying change, the agent MUST:

### 1. Update Route-to-Help Registry
- File: `docs/route-help-registry.json`
- Add new routes with module, label, description, and helpArticles mappings
- Add new help article entries with title, section, and status
- Remove entries for deleted routes

### 2. Update Documentation Coverage Inventory
- File: `docs/documentation-coverage.json`
- Add new pages under the appropriate module
- Update status indicators (covered/partial/missing)
- Add new modules if the change introduces one

### 3. Update Help Content
- Add or update help article definitions in the Help & Resources page
- File: `frontend/rea-investment-fe/src/pages/Help/HelpResources.tsx`
- Ensure new features appear in the appropriate help section

### 4. Update FAQs
- Add common questions about the new feature to the FAQs section
- Address edge cases and potential confusion points

### 5. Run the Documentation Audit
- Execute `npm run docs:audit` from `frontend/rea-investment-fe`
- Resolve any errors before considering the task complete
- Report any new warnings

## Pre-Completion Checklist

Before marking any task as complete, verify:

- [ ] All new routes are in `docs/route-help-registry.json`
- [ ] All new pages are in `docs/documentation-coverage.json`
- [ ] Help articles exist for new user-facing features
- [ ] The docs audit passes with zero errors
- [ ] Any new terminology is defined in help content

## File Reference

| File | Purpose |
|------|---------|
| `docs/route-help-registry.json` | Maps routes to help articles |
| `docs/documentation-coverage.json` | Tracks coverage status per module/page |
| `docs/DOCUMENTATION_REQUIREMENTS.md` | Developer governance rules and checklist |
| `docs/AI_DEVELOPMENT_GUARDRAILS.md` | This file - AI agent instructions |
| `frontend/rea-investment-fe/src/pages/Help/HelpResources.tsx` | Help & Resources UI |
| `scripts/docs-audit.js` | Documentation audit script |

## Interaction with replit.md

When updating `replit.md` (the project memory file), include a note about documentation governance so it persists across sessions. The key points to preserve:

- Documentation is mandatory for all features
- Route-help registry and coverage inventory must be kept in sync
- The docs audit script should be run after changes
- This guardrails file exists and should be consulted for any feature work
