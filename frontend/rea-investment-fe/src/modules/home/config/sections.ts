export type HomeSectionType = 'summary-cards' | 'tasks' | 'notifications' | 'quick-actions' | 'companies';

export interface HomeSection {
  id: HomeSectionType;
  title: string;
  enabled: boolean;
}

export const HOME_SECTIONS: HomeSection[] = [
  { id: 'summary-cards', title: 'Summary', enabled: true },
  { id: 'tasks', title: 'Tasks', enabled: true },
  { id: 'notifications', title: 'Notifications', enabled: true },
  { id: 'quick-actions', title: 'Quick Actions', enabled: true },
  { id: 'companies', title: 'Your Companies', enabled: true }
];
