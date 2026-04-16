import React, { useState } from 'react';
import { useQuery, queryOptions } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import TaskBoard from './internal/TaskBoard/TaskBoard';
import TaskList from './internal/TaskList/TaskList';
import CalendarView from './internal/CalendarView/CalendarView';
import ToggleGroup from './internal/ToogleGroup/ToggleGroup';
import AddTaskForm from './internal/AddTaskForm/AddTaskForm';
import SearchAndActions from '../../common/tables/components/SearchAndActions/SearchAndActions';
import { ApiClient } from '../../../api';

export const boardQuery = (
  entityType: 'site' | 'company',
  entityId: number,
  enabled = true,
  throwOnError = false,
  module: string
) =>
  queryOptions({
    queryKey: ['board', { entityType, entityId, module }],
    queryFn: () => ApiClient.taskManagement.getBoard({ entityType, entityId, module }),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

type TasksCommonProps = {
  view: string;
  setView: (view: string) => void;
  companyId: number;
  module?: string;
  focusTaskId?: number | null;
  deviceId?: number;
};

type TasksSiteScopeProps = TasksCommonProps & {
  scope: 'site';
  siteId: number;
};

type TasksCompanyScopeProps = TasksCommonProps & {
  scope: 'company';
  siteId?: undefined;
};

type TasksProps = TasksSiteScopeProps | TasksCompanyScopeProps;

export const Tasks: React.FC<TasksProps> = ({
  module = '',
  scope,
  companyId,
  siteId,
  view,
  setView,
  focusTaskId,
  deviceId
}) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [isFormOpen, setIsFormOpen] = React.useState<boolean>(false);

  const entityId = scope === 'company' ? companyId : siteId;
  const {
    data: boardInfo,
    isLoading: isBoardLoading,
    isError: isBoardError
  } = useQuery(boardQuery(scope, entityId, true, false, module));
  const boardId = boardInfo?.items?.[0]?.id ? Number.parseInt(boardInfo.items[0].id as string) : -1;
  const hasBoard = boardId > 0;

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleAddClick = () => {
    setIsFormOpen(true);
  };

  const handleCloseForm = () => setIsFormOpen(false);

  const emptyState = (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        py: 8,
        color: 'text.secondary'
      }}
    >
      <Typography variant="h6" gutterBottom>
        No task board configured
      </Typography>
      <Typography variant="body2">
        {scope === 'company'
          ? 'No task board has been set up for this company yet.'
          : 'No task board has been set up for this project yet.'}
      </Typography>
    </Box>
  );

  if (isBoardLoading) {
    return (
      <Box sx={{ py: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">Loading tasks...</Typography>
      </Box>
    );
  }

  if (isBoardError) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 8 }}>
        <Typography variant="h6" color="error" gutterBottom>
          Unable to load tasks
        </Typography>
        <Typography variant="body2" color="text.secondary">
          There was a problem retrieving the task board. Please try again later.
        </Typography>
      </Box>
    );
  }

  const renderTaskViews = () => {
    if (!hasBoard) return emptyState;

    if (scope === 'site') {
      return (
        <>
          {view === 'list' && (
            <TaskList
              boardId={boardId}
              scope={scope}
              companyId={companyId}
              siteId={siteId}
              searchTerm={searchTerm}
              module={module}
              focusTaskId={focusTaskId}
              deviceId={deviceId}
            />
          )}
          {view === 'board' && (
            <TaskBoard
              boardId={boardId}
              scope={scope}
              companyId={companyId}
              siteId={siteId}
              searchTerm={searchTerm}
              module={module}
              deviceId={deviceId}
            />
          )}
          {view === 'calendar' && (
            <CalendarView
              boardId={boardId}
              scope={scope}
              companyId={companyId}
              siteId={siteId}
              searchTerm={searchTerm}
              module={module}
              deviceId={deviceId}
            />
          )}
          <AddTaskForm
            open={isFormOpen}
            onClose={handleCloseForm}
            boardId={boardId}
            scope={scope}
            siteId={siteId}
            companyId={companyId}
            module={module}
          />
        </>
      );
    }

    return (
      <>
        {view === 'list' && (
          <TaskList boardId={boardId} scope={scope} companyId={companyId} searchTerm={searchTerm} module={module} />
        )}
        {view === 'board' && (
          <TaskBoard boardId={boardId} scope={scope} companyId={companyId} searchTerm={searchTerm} module={module} />
        )}
        {view === 'calendar' && (
          <CalendarView boardId={boardId} scope={scope} companyId={companyId} searchTerm={searchTerm} module={module} />
        )}
        <AddTaskForm
          open={isFormOpen}
          onClose={handleCloseForm}
          boardId={boardId}
          scope={scope}
          companyId={companyId}
          module={module}
        />
      </>
    );
  };

  return (
    <>
      <SearchAndActions
        showSearch={hasBoard}
        showAdd={hasBoard}
        reversOrder={true}
        searchPlaceholder="Search"
        btnAddLabel="Add a New Task"
        onSearch={handleSearch}
        onAdd={handleAddClick}
        customActions={hasBoard ? <ToggleGroup alignment={view} setAlignment={setView} /> : undefined}
      />
      {renderTaskViews()}
    </>
  );
};

export default Tasks;
