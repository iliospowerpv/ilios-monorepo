# Quicklinks Routing Alignment

This document describes the routing contract for quicklinks and module navigation within the iliOS platform.

## Route Types

### 1. Module-Scoped Lens Routes (Preferred for Internal Navigation)

Lens routes maintain the user's current module context while changing the entity scope:

```
/{module}/scope/portfolio
/{module}/scope/company/{companyId}
/{module}/scope/project/{projectId}
```

Examples:
- `/finance/scope/company/123` - Finance module, Company 123 scope
- `/asset-management/scope/project/456` - Asset Management module, Project 456 scope
- `/due-diligence/scope/portfolio` - Due Diligence module, Portfolio scope

### 2. Canonical Routes (For Direct Entity Access)

Canonical routes navigate directly to entity overview pages:

```
/portfolio
/companies/{companyId}
/projects/{projectId}
```

### 3. Picker Routes (For Entity Selection)

When no entity is selected, route to picker pages:

```
/companies - Company picker
/projects - Project picker
/projects?companyId={id} - Project picker filtered by company
```

## buildLensRoute() Utility

Use the `buildLensRoute()` utility from `src/utils/routing.ts` for all quicklink route generation:

```typescript
import { buildLensRoute, ModuleType } from '../../utils/routing';

// From Project context
buildLensRoute('finance', 'project', { projectId: 123 })
// Returns: /finance/scope/project/123

// From Company context
buildLensRoute('asset-management', 'company', { companyId: 456 })
// Returns: /asset-management/scope/company/456

// Portfolio scope
buildLensRoute('due-diligence', 'portfolio')
// Returns: /due-diligence/scope/portfolio

// Missing ID - returns picker route
buildLensRoute('finance', 'company', { companyId: null })
// Returns: /companies

buildLensRoute('finance', 'project', { companyId: 123 })
// Returns: /projects?companyId=123
```

## Routing Rules

### Quicklinks on Entity Pages

| Source Page | Quicklink Click | Expected Route |
|-------------|-----------------|----------------|
| Company Overview | Finance | `/finance/scope/company/{companyId}` |
| Company Overview | Asset Management | `/asset-management/scope/company/{companyId}` |
| Project Overview | Finance | `/finance/scope/project/{projectId}` |
| Project Overview | O&M | `/operations-and-maintenance/scope/project/{projectId}` |
| Portfolio View | Any Module | `/{module}/scope/portfolio` |

### Null/Missing ID Fallback Rules

| Scope | Missing Value | Fallback Route |
|-------|---------------|----------------|
| Company | No companyId | `/companies` |
| Project | No projectId | `/projects` |
| Project | No projectId, has companyId | `/projects?companyId={companyId}` |

**IMPORTANT:** Never fall back to `/dashboard` unless it's an explicit "Home" button action.

## Files Changed

| File | Change |
|------|--------|
| `src/utils/routing.ts` | New file - buildLensRoute(), getPickerRoute(), getCanonicalRoute() |
| `src/utils/routing.test.ts` | Unit tests for routing utilities |
| `src/pages/Hierarchy/ProjectView.tsx` | Updated quicklinks to use buildLensRoute() |
| `src/pages/Hierarchy/CompanyView.tsx` | Added module quicklinks using buildLensRoute() |
| `src/contexts/entityContext/entityContext.tsx` | Changed default fallback from /dashboard to /portfolio; Updated navigateToLevel() to use lens routes |

## Before/After Examples

### Example 1: Project Overview - Finance Quicklink

**Before:**
```typescript
onClick={() => navigate(`/finance/project/${project.id}`)}
```

**After:**
```typescript
onClick={() => navigate(buildLensRoute('finance', 'project', { projectId: project.id }))}
// Generates: /finance/scope/project/{projectId}
```

### Example 2: Company Overview - Asset Management Quicklink

**Before:**
No quicklinks existed on Company Overview page.

**After:**
```typescript
onClick={() => navigate(buildLensRoute('asset-management', 'company', { companyId: company.id }))}
// Generates: /asset-management/scope/company/{companyId}
```

### Example 3: Default Fallback Route

**Before:**
```typescript
default:
  return '/dashboard';
```

**After:**
```typescript
default:
  return '/portfolio';
```

## 10-Minute Manual Test Checklist

### Company Overview Tests
- [ ] Navigate to `/companies/{id}` for any company
- [ ] Click "Asset Management" quicklink -> Verify URL is `/asset-management/scope/company/{id}`
- [ ] Click "Finance" quicklink -> Verify URL is `/finance/scope/company/{id}`
- [ ] Click "O&M" quicklink -> Verify URL is `/operations-and-maintenance/scope/company/{id}`
- [ ] Click "Due Diligence" quicklink -> Verify URL is `/due-diligence/scope/company/{id}`

### Project Overview Tests
- [ ] Navigate to `/projects/{id}` for any project
- [ ] Click "Asset Management" quicklink -> Verify URL is `/asset-management/scope/project/{id}`
- [ ] Click "Finance" quicklink -> Verify URL is `/finance/scope/project/{id}`
- [ ] Click "O&M" quicklink -> Verify URL is `/operations-and-maintenance/scope/project/{id}`
- [ ] Click "Due Diligence" quicklink -> Verify URL is `/due-diligence/scope/project/{id}`

### Context Bar Tests
- [ ] From any module, use Context Bar to switch to Portfolio scope -> Verify URL includes `/scope/portfolio`
- [ ] From any module, select a Company via Context Bar -> Verify URL includes `/scope/company/{id}`
- [ ] From any module, select a Project via Context Bar -> Verify URL includes `/scope/project/{id}`

### Null Fallback Tests
- [ ] Clear localStorage and refresh -> Should NOT route to `/dashboard`
- [ ] Verify no navigation leads to `/dashboard` unless clicking explicit "Home" button

## Acceptance Criteria

- [x] All quicklinks from Company pages route to `/{module}/scope/company/{companyId}`
- [x] All quicklinks from Project pages route to `/{module}/scope/project/{projectId}`
- [x] Switching modules from Company context preserves Company scope
- [x] Switching modules from Project context preserves Project scope
- [x] Null company/project selection routes to picker views, not dashboard
- [x] buildLensRoute() is the single source of truth for lens route generation
