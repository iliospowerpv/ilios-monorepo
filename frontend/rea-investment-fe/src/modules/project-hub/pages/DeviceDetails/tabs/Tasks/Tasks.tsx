import React from 'react';
import { useSearchParams } from 'react-router-dom';
import Box from '@mui/material/Box';

import { DeviceDetailsTabProps } from '../types';
import TasksCluster from '../../../../../../components/clusters/TasksCluster/TasksCluster';

export const Tasks: React.FC<DeviceDetailsTabProps> = ({ siteId, deviceId, companyId }) => {
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
    <Box>
      <TasksCluster
        view={view}
        setView={setView}
        scope="site"
        companyId={companyId}
        siteId={siteId}
        deviceId={deviceId}
      />
    </Box>
  );
};

export default Tasks;
