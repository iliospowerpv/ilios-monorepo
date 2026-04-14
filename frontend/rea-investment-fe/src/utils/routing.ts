export type ScopeType = 'portfolio' | 'company' | 'project';

export type ModuleType =
  | 'asset-management'
  | 'operations-and-maintenance'
  | 'due-diligence'
  | 'finance'
  | 'sales'
  | 'reports'
  | 'dashboard'
  | 'portfolio';

export interface LensRouteParams {
  companyId?: number | string | null;
  projectId?: number | string | null;
}

const PICKER_ROUTES: Record<ScopeType, string> = {
  portfolio: '/portfolio',
  company: '/companies',
  project: '/projects'
};

export function buildLensRoute(module: ModuleType, scope: ScopeType, params?: LensRouteParams): string {
  const basePath = `/${module}`;

  switch (scope) {
    case 'portfolio':
      return `${basePath}/scope/portfolio`;

    case 'company':
      if (params?.companyId) {
        return `${basePath}/scope/company/${params.companyId}`;
      }
      return PICKER_ROUTES.company;

    case 'project':
      if (params?.projectId) {
        return `${basePath}/scope/project/${params.projectId}`;
      }
      if (params?.companyId) {
        return `${PICKER_ROUTES.project}?companyId=${params.companyId}`;
      }
      return PICKER_ROUTES.project;

    default:
      return PICKER_ROUTES.portfolio;
  }
}

export function getPickerRoute(scope: ScopeType, companyId?: number | string | null): string {
  switch (scope) {
    case 'portfolio':
      return '/portfolio';
    case 'company':
      return '/companies';
    case 'project':
      if (companyId) {
        return `/projects?companyId=${companyId}`;
      }
      return '/projects';
    default:
      return '/portfolio';
  }
}

export function getCanonicalRoute(scope: ScopeType, params?: LensRouteParams): string {
  switch (scope) {
    case 'portfolio':
      return '/portfolio';
    case 'company':
      if (params?.companyId) {
        return `/companies/${params.companyId}`;
      }
      return '/companies';
    case 'project':
      if (params?.projectId) {
        return `/project-hub/projects/${params.projectId}`;
      }
      return '/projects';
    default:
      return '/portfolio';
  }
}
