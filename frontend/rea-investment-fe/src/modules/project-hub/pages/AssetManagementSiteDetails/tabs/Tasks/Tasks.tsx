import React from 'react';
import { useSearchParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';

import { AssetManagementSiteDetailsTabProps } from '../types';
import TasksCluster from '../../../../../../components/clusters/TasksCluster/TasksCluster';
import { useFocusHighlight } from '../../../../../../hooks/useFocusHighlight';

export const Tasks: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { focusState } = useFocusHighlight();

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
      {focusState.notFoundMessage && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {focusState.notFoundMessage}
        </Alert>
      )}
      <TasksCluster
        view={view}
        setView={setView}
        scope="site"
        companyId={siteDetails.company.id}
        siteId={siteDetails.id}
        focusTaskId={focusState.focusType === 'task' ? focusState.focusId : null}
      />
    </Box>
  );
};

export default Tasks;
