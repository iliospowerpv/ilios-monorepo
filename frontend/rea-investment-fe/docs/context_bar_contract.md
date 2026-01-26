# Context Bar Contract

This document defines the architectural contract for the iliOS Context Bar infrastructure, including scope management, route patterns, persistence, and module integration guidelines.

## Overview

The Context Bar provides a unified three-tier scope management system that persists across all modules. It enables users to navigate between Portfolio, Company, and Project levels while maintaining context within the current module.

## Scope Types

| Scope | Description | Entity Selection |
|-------|-------------|------------------|
| `portfolio` | Aggregate view across all accessible entities | No specific entity selected |
| `company` | Company-scoped view | A specific company is selected |
| `project` | Project-scoped view | A specific project is selected |

## State Management

### EntityContext State

The `EntityContext` provides the following state:

```typescript
interface EntityContextType {
  currentLevel: EntityLevel;        // Derived from URL path
  currentScope: ScopeType;          // User's selected scope (authoritative)
  currentCompany: EntityInfo | null; // Currently selected company
  currentProject: EntityInfo | null; // Currently selected project
  currentModule: ModuleType;        // Current module based on URL path
}
```

### Persistence

Context state is persisted to `localStorage` under the key `ilios_entity_context`:

```json
{
  "company": { "id": 1, "name": "Company Name" },
  "project": { "id": 1, "name": "Project Name" },
  "scope": "company"
}
```

**Behavior:**
- State persists across page reloads
- State persists across sessions
- State is restored on application load
- State updates are immediate and synchronous

## Route Patterns

### Canonical Hierarchy Routes

Direct entity access routes that display entity overview pages:

| Route | Description |
|-------|-------------|
| `/portfolio` | Portfolio overview page |
| `/companies` | Company picker (when no company selected) |
| `/companies/:companyId` | Company overview page |
| `/projects` | Project picker (when no project selected) |
| `/projects/:projectId` | Project overview page |

### Module-Scoped Lens Routes

Routes that set scope context and render module content:

| Pattern | Description |
|---------|-------------|
| `/{module}/scope/portfolio` | Module at portfolio scope |
| `/{module}/scope/company/:companyId` | Module at company scope |
| `/{module}/scope/project/:projectId` | Module at project scope |

**Supported Modules:**
- `/dashboard`
- `/my-portfolio`
- `/reports`
- `/finance`
- `/sales`
- `/due-diligence`
- `/operations-and-maintenance`
- `/asset-management`

## Navigation Methods

### navigateToScope(scope, options)

Navigate to a specific scope level.

```typescript
navigateToScope('portfolio', { stayInModule: true });
navigateToScope('company', { stayInModule: false });
```

**Options:**
- `stayInModule` (default: `true`): If `true`, navigates to module-scoped lens route. If `false`, navigates to canonical route.

### navigateToCompany(company, options)

Select a company and navigate to company scope.

```typescript
navigateToCompany({ id: 1, name: 'Acme Corp' }, { stayInModule: true });
```

### navigateToProject(project, options)

Select a project and navigate to project scope.

```typescript
navigateToProject({ id: 1, name: 'Solar Farm' }, { stayInModule: true });
```

### getCanonicalPath(scope)

Get the canonical route path for a scope.

```typescript
getCanonicalPath('company'); // Returns "/companies/1" if company selected
getCanonicalPath('project'); // Returns "/projects/1" if project selected
```

### getModuleScopedPath(module, scope)

Get the module-scoped lens route path.

```typescript
getModuleScopedPath('finance', 'company'); // Returns "/finance/scope/company/1"
```

## Deep Linking

### Canonical Deep Links

Visiting a canonical route sets the context appropriately:

- `/companies/5` → Sets currentCompany to company with ID 5, scope to 'company'
- `/projects/10` → Sets currentProject to project with ID 10, scope to 'project'

### Module-Scoped Deep Links

Visiting a module-scoped lens route sets context and renders module:

- `/finance/scope/company/5` → Sets company scope and renders Finance module
- `/sales/scope/portfolio` → Sets portfolio scope and renders Sales module

## Empty Selection Handling

When the user clicks a scope tab without a selection:

| Scenario | Behavior |
|----------|----------|
| Company tab, no company selected | Navigates to `/companies` picker |
| Project tab, no project selected | Navigates to `/projects` picker (filtered by current company if set) |

## Data Access

### useAccessibleEntities Hook

Fetches and caches user's accessible entities:

```typescript
const {
  companies,              // AccessibleCompany[]
  projects,               // AccessibleProject[]
  isLoading,
  isError,
  getProjectsByCompanyId, // (companyId: number) => AccessibleProject[]
  getCompanyById,         // (companyId: number) => AccessibleCompany | undefined
  getProjectById          // (projectId: number) => AccessibleProject | undefined
} = useAccessibleEntities();
```

**Caching:**
- `staleTime`: 5 minutes
- `gcTime`: 10 minutes
- `refetchOnWindowFocus`: false

### Backend Endpoint

`GET /api/users/account/me/accessible-entities`

Returns:
```json
{
  "companies": [
    { "id": 1, "name": "Company Name" }
  ],
  "projects": [
    { "id": 1, "name": "Project Name", "company_id": 1, "company_name": "Company Name" }
  ]
}
```

## Module Integration Guide

### Adding Scope Support to a New Module

1. **Add Scoped Lens Routes** in `App.tsx`:

```tsx
<Route path="/new-module" element={<NewModuleContainer />}>
  <Route
    path="scope/portfolio"
    element={
      <ScopedModuleRoute scope="portfolio">
        <NewModuleHome />
      </ScopedModuleRoute>
    }
  />
  <Route
    path="scope/company/:companyId"
    element={
      <ScopedModuleRoute scope="company">
        <NewModuleCompanyView />
      </ScopedModuleRoute>
    }
  />
  <Route
    path="scope/project/:projectId"
    element={
      <ScopedModuleRoute scope="project">
        <NewModuleProjectView />
      </ScopedModuleRoute>
    }
  />
</Route>
```

2. **Register Module** in `entityContext.tsx`:

Add the module type:
```typescript
export type ModuleType =
  | 'asset-management'
  | 'operations-and-maintenance'
  // ... existing modules
  | 'new-module'
  | null;
```

Add path detection:
```typescript
if (path.startsWith('/new-module')) {
  setCurrentModule('new-module');
}
```

Add base path:
```typescript
case 'new-module':
  return '/new-module';
```

3. **Use Context in Components**:

```tsx
const MyComponent: React.FC = () => {
  const { currentScope, currentCompany, currentProject } = useEntityContext();
  
  // Filter data based on scope
  const filteredData = useMemo(() => {
    if (currentScope === 'project' && currentProject) {
      return data.filter(d => d.projectId === currentProject.id);
    }
    if (currentScope === 'company' && currentCompany) {
      return data.filter(d => d.companyId === currentCompany.id);
    }
    return data; // Portfolio scope - show all
  }, [data, currentScope, currentCompany, currentProject]);
  
  return <DataTable data={filteredData} />;
};
```

## ScopedModuleRoute Component

Wrapper component that sets scope context based on URL parameters:

```tsx
<ScopedModuleRoute scope="company">
  <ModuleContent />
</ScopedModuleRoute>
```

**Props:**
- `scope`: The scope type to set ('portfolio', 'company', 'project')
- `children`: The module content to render

**Behavior:**
- Sets context on mount based on URL parameters
- Shows loading spinner while fetching entity data
- Redirects to picker if entity not found
- Renders children once context is set

## Context Bar UI (EntityContextNav)

The Context Bar appears in the BaseLayout header and provides:

1. **Portfolio Tab**: Click to set portfolio scope
2. **Company Tab**: Click to open company picker dropdown
   - Search functionality
   - "View Company Overview" link to canonical route
3. **Project Tab**: Click to open project picker dropdown
   - Filtered by current company if one is selected
   - Search functionality
   - "View Project Overview" link to canonical route

## Best Practices

1. **Always check `currentScope`** before filtering data in modules
2. **Use `stayInModule: true`** for in-module navigation to maintain context
3. **Use canonical routes** for cross-module navigation or when explicitly viewing entity overviews
4. **Cache entity data** using the `useAccessibleEntities` hook rather than fetching per-component
5. **Handle loading states** - always show appropriate loading UI while context is being set
