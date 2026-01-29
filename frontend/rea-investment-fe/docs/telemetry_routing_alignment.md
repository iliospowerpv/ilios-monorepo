# Telemetry Routing Alignment

This document describes the routing architecture for the Telemetry feature, ensuring alignment with the Context Bar + module lens navigation contract.

## Canonical Routes

The primary entry point for Telemetry is through the Project hierarchy:

| Route | Description |
|-------|-------------|
| `/projects/:projectId/telemetry` | Canonical Project Telemetry page |

This route:
- Sets `currentProject` and `currentCompany` via EntityContext
- Sets scope to `project`
- Renders the full Telemetry UI with readiness strip, health strip, and wizard

## Lens Routes

Module-scoped lens routes allow users to access Telemetry while staying within a specific module:

| Route | Module | Description |
|-------|--------|-------------|
| `/operations-and-maintenance/scope/project/:projectId/telemetry` | O&M | Telemetry within O&M module scope |

These routes:
- Use `ScopedModuleRoute` wrapper to set context from URL parameters
- Keep users within the current module's navigation context
- Maintain Context Bar scope state

## Alias/Redirect Behavior

Legacy Asset Management routes are preserved as aliases:

| Legacy Route | Redirects To |
|--------------|--------------|
| `/asset-management/companies/:companyId/sites/:siteId/telemetry` | `/projects/:siteId/telemetry` |

Notes:
- The `siteId` parameter maps directly to `projectId` (sites = projects internally)
- Redirect is performed via `<Navigate replace />` for clean URL history
- Existing bookmarks and links continue to work

## Quick Links

Telemetry is accessible from the Project Overview page:
- `/projects/:projectId` displays a "Telemetry" quick link card
- Clicking navigates to `/projects/:projectId/telemetry`

## Context Bar Behavior

When on any Telemetry route:
1. **Company Tab**: Displays the project's parent company
2. **Project Tab**: Displays the current project
3. **Scope Switching**: Switching scope via Context Bar navigates to the appropriate module view
4. **Module Navigation**: Sidebar modules remain accessible

## Component Architecture

```
TelemetryPage.tsx (standalone page wrapper)
├── Uses EntityContext for scope management
├── Fetches siteDetails via API
├── Renders breadcrumb navigation
└── Embeds Telemetry.tsx component
    ├── ReadinessStrip (4-step progress)
    ├── HealthStrip (status with color-coded indicators)
    └── TelemetryWizard (4-step configuration dialog)
```

## 10-Minute Smoke Test

### Prerequisites
- User logged in with access to at least one company and project
- Backend running with telemetry endpoints available

### Test Steps

1. **Canonical Route Access** (2 min)
   - Navigate to `/projects/:projectId`
   - Verify "Telemetry" quick link is visible
   - Click "Telemetry" quick link
   - Verify URL is `/projects/:projectId/telemetry`
   - Verify breadcrumbs show: Company > Project > Telemetry
   - Verify Context Bar shows correct company and project

2. **Operations Lens Route** (2 min)
   - Navigate to `/operations-and-maintenance/scope/project/:projectId/telemetry`
   - Verify Telemetry UI renders correctly
   - Verify Context Bar scope is set to project
   - Verify sidebar shows O&M module as active

3. **Asset Management Alias Redirect** (2 min)
   - Navigate to `/asset-management/companies/:companyId/sites/:siteId/telemetry`
   - Verify redirect to `/projects/:siteId/telemetry`
   - Verify Telemetry UI loads correctly

4. **Wizard Flow** (3 min)
   - Click "Connect Telemetry" button
   - Verify wizard opens with Step 1 (Connection)
   - Select a provider and test connection
   - Proceed through all 4 steps
   - Verify wizard completes successfully

5. **Scope Switching** (1 min)
   - From Telemetry page, use Context Bar to switch to a different project
   - Verify navigation updates appropriately
   - Use Context Bar to switch back
   - Verify Telemetry loads for original project

### Expected Results
- All routes render Telemetry UI without errors
- Context Bar reflects correct scope and entity
- Wizard flow completes without errors
- Legacy routes redirect correctly
- No console errors related to routing or context

## Migration Notes

If migrating from embedded telemetry fields in SiteForm/DeviceForm:
1. Embedded telemetry fields are deprecated
2. Add "Manage Telemetry" link that navigates to canonical route
3. Do not remove fields immediately - maintain backward compatibility
