import React from 'react';
import { useSearchParams } from 'react-router-dom';

import { SiteDetailsTabProps } from '../types';
import TasksCluster from '../../../../../../components/clusters/TasksCluster/TasksCluster';

export const Tasks: React.FC<SiteDetailsTabProps> = ({ siteDetails, companyDetails }) => {
  const [searchParams, setSearchParams] = useSearchParams();

  const parsedViewValue = (searchParams.has('view') && searchParams.get('view')) || 'list';
  const view = ['list', 'board', 'calendar'].includes(parsedViewValue) ? parsedViewValue : 'list';

  const setView = React.useCallback(
    (view: string) => {
      setSearchParams(
        searchParams => {
          const newParams = new URLSearchParams(searchParams);
          newParams.set('view', view);
          return newParams;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  return (
    <TasksCluster
      view={view}
      setView={setView}
      module="O&M"
      scope="site"
      companyId={companyDetails.id}
      siteId={siteDetails.id}
    />
  );
};

export default Tasks;
