# Home Page Unification

## Overview

The Home page (`/home`) is the unified landing experience for iliOS, combining the functionality of the previous Dashboard and Workspace modules into a single, cohesive landing page.

## Purpose

The Home page serves as the central hub for users to:
- Get an at-a-glance view of their portfolio (companies, projects, tasks, notifications)
- Access common actions quickly (Create Company, Create Project, Invite User)
- Navigate to any company or module efficiently
- View and manage their pending tasks and notifications

## Composition

The Home page consists of the following sections:

### 1. Summary Cards (Top Row)
- **Companies**: Count of accessible companies
- **Projects**: Count of accessible projects  
- **Pending Tasks**: Count of tasks assigned to the user
- **Notifications**: Count of unread notifications

### 2. Main Content Area
- **Tasks Grid** (Left, ~67% width): AG Grid table showing pending tasks with priority, name, status, module, creator, and due date
- **Side Panel** (Right, ~33% width):
  - Notifications List: Recent notifications with "Show More" expansion
  - Quick Actions: Permission-aware action buttons

### 3. Quick Actions Panel
Permission-aware CTAs that respect user roles:
- **Create Company**: Only visible to system users
- **Create Project**: Visible to all authenticated users, defaults to current company context
- **Invite User**: Visible to all authenticated users, defaults to current company context
- **Manage Members**: Only visible when a company is selected in Context Bar

### 4. Companies List (Bottom)
Grid of accessible companies showing:
- Company name
- Role badge (Admin, Contributor, Read Only)
- Project count
- Access source indicator (Direct Member, Via Project, Legacy Access)
- "Open Company" action button

## Route Redirects

The following routes now redirect to `/home`:

| Old Route | New Destination | Notes |
|-----------|-----------------|-------|
| `/workspace` | `/home` | Full redirect |
| `/workspace/*` | `/home` | Catches all workspace sub-routes |
| `/dashboard` | `/home` | Full redirect |
| `/dashboard/*` | `/home` | Catches all dashboard sub-routes |

**Preserved Routes:**
- `/portfolio` - Canonical portfolio rollup route (unchanged)
- `/company-admin` - Context-aware company membership management

## Default Scoping Rules

The Home page respects the Context Bar's current scope:

### When `currentCompany` is set:
- **Create Project** defaults `company_id` to the current company
- **Invite User** defaults `company_id` to the current company
- **Manage Members** button is visible and navigates to Company Admin

### When no company is selected:
- **Create Project** requires selecting a company from a picker
- **Invite User** requires selecting a company from a picker
- **Manage Members** button is hidden

## Dialog Behaviors

### Create Company Dialog
- Minimal fields: Company Name (required), Email, Phone, Address
- On success:
  - Sets `currentCompany` in Context Bar
  - Navigates to `/companies/:newCompanyId`
  - Refreshes workspace data

### Create Project Dialog
- Fields: Company (required), Project Name (required), Address, City, State, Zip, System Size AC/DC
- Company picker defaults to current company if set
- On success:
  - Navigates to `/projects/:newProjectId`
  - Refreshes workspace data

### Invite User Dialog (Add User to Company)
- Fields: Company (required), User (autocomplete), Role
- Optional: Project assignment multi-select (collapsible section)
- Company picker defaults to current company if set
- Project assignment is NOT required (key UX improvement)
- On success:
  - Shows confirmation toast
  - Closes dialog

## Navigation Menu Changes

The primary navigation now includes:
1. **Home** (new) - Primary landing destination
2. Portfolio
3. Sales
4. Diligence
5. O&M
6. Asset Management
7. Finance
8. Reports
9. Company Admin

Removed from navigation:
- Dashboard (deprecated, redirects to Home)
- Workspace (deprecated, redirects to Home)

## Component Architecture

The Home page is structured as composable sections for future extensibility:

```
modules/home/
├── ModuleContainer.tsx          # Auth-gated container
├── pages/
│   └── Home/
│       ├── HomePage.tsx         # Main page component
│       ├── handle.ts            # Route handle for breadcrumbs
│       └── dialogs/
│           ├── CreateCompanyDialog.tsx
│           ├── CreateProjectDialog.tsx
│           └── InviteUserDialog.tsx
├── components/
│   ├── HomeSummaryCards/        # Summary statistics cards
│   ├── HomeTasks/               # Tasks AG Grid table
│   ├── HomeNotifications/       # Notifications list
│   ├── HomeCompanies/           # Companies grid
│   └── HomeQuickActions/        # Action buttons panel
└── config/
    └── sections.ts              # Section configuration (future widget registry seam)
```

## Future Widget Framework (Deferred)

The current implementation creates a seam for future widget customization:

1. **Section Configuration** (`config/sections.ts`): Defines section order and enabled state
2. **Composable Components**: Each section is a self-contained component
3. **No Persistence Yet**: Section order is currently static

When implementing a full widget framework in the future:
- Add drag-and-drop reordering using `@dnd-kit` or similar
- Persist user preferences to backend or localStorage
- Add widget registry with dynamic component loading
- Consider widget-level permissions and visibility rules

## Acceptance Criteria

1. ✅ Logging in lands on `/home` (or Home is 1 click from nav)
2. ✅ Home shows: summary cards, tasks grid, notifications, companies list with access source indicators
3. ✅ Create Project from Home defaults to currentCompany if set, otherwise requires selection
4. ✅ Invite User from Home defaults to currentCompany if set, allows optional project assignment
5. ✅ `/workspace` and `/dashboard` redirect to `/home` and are removed from primary nav
6. ✅ No regressions to Context Bar lens routing or quicklinks
