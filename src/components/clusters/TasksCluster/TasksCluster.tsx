import React, { useState } from 'react';
import { useQuery, queryOptions } from '@tanstack/react-query';

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

export const Tasks: React.FC<TasksProps> = ({ module = '', scope, companyId, siteId, view, setView }) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [isFormOpen, setIsFormOpen] = React.useState<boolean>(false);

  const entityId = scope === 'company' ? companyId : siteId;
  const { data: boardInfo } = useQuery(boardQuery(scope, entityId, true, true, module));
  const boardId = boardInfo ? Number.parseInt(boardInfo?.items[0].id as string) : -1;

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleAddClick = () => {
    setIsFormOpen(true);
  };

  const handleCloseForm = () => setIsFormOpen(false);

  return (
    <>
      <SearchAndActions
        showSearch={true}
        showAdd={true}
        reversOrder={true}
        searchPlaceholder="Search"
        btnAddLabel="Add a New Task"
        onSearch={handleSearch}
        onAdd={handleAddClick}
        customActions={<ToggleGroup alignment={view} setAlignment={setView} />}
      />
      {scope === 'site' ? (
        <>
          {view === 'list' && (
            <TaskList
              boardId={boardId}
              scope={scope}
              companyId={companyId}
              siteId={siteId}
              searchTerm={searchTerm}
              module={module}
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
      ) : (
        <>
          {view === 'list' && (
            <TaskList boardId={boardId} scope={scope} companyId={companyId} searchTerm={searchTerm} module={module} />
          )}
          {view === 'board' && (
            <TaskBoard boardId={boardId} scope={scope} companyId={companyId} searchTerm={searchTerm} module={module} />
          )}
          {view === 'calendar' && (
            <CalendarView
              boardId={boardId}
              scope={scope}
              companyId={companyId}
              searchTerm={searchTerm}
              module={module}
            />
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
      )}
    </>
  );
};

export default Tasks;
