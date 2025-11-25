interface TasksViewCommonProps {
  boardId: number;
  searchTerm?: string;
  companyId: number;
  module?: string;
}

type TasksViewSiteScopeProps = TasksViewCommonProps & {
  scope: 'site';
  siteId: number;
};

type TasksViewCompanyScopeProps = TasksViewCommonProps & {
  scope: 'company';
  siteId?: undefined;
};

type TasksViewProps = TasksViewSiteScopeProps | TasksViewCompanyScopeProps;

export type { TasksViewProps };
