export const BREADCRUMB_LABELS = {
  HOME: 'Home',
  PROJECT_HUB: 'Project Hub',
  ACQUISITIONS: 'Acquisitions',
  DATA_ROOM: 'Data Room',
  OM: 'O&M',
  FINANCE: 'Finance',
  TASKS: 'Tasks',
  REPORTING: 'Reporting',
  REPORTS: 'Reports',
  SETTINGS: 'Settings',
  PORTFOLIO_ADMIN: 'Portfolio Admin',
  MY_COMPANY_SETTINGS: 'My Company Settings',
  DASHBOARD: 'Dashboard',
  PORTFOLIO: 'Portfolio'
} as const;

export const CANONICAL_ROUTES = {
  HOME: '/home',
  PROJECT_HUB: '/project-hub',
  PROJECT_HUB_PROJECT: (siteId: number | string) => `/project-hub/projects/${siteId}`,
  PROJECT_HUB_PROJECT_TAB: (siteId: number | string, tab: string) => `/project-hub/projects/${siteId}/${tab}`,
  ACQUISITIONS: '/acquisitions',
  REPORTS: '/reports',
  FINANCE: '/finance',
  SETTINGS: '/settings'
} as const;

export type BreadcrumbLabel = (typeof BREADCRUMB_LABELS)[keyof typeof BREADCRUMB_LABELS];
