import React, { useEffect, useState } from 'react';
import { cloneDeep } from 'lodash';
import { useQuery, keepPreviousData, useMutation, useQueryClient } from '@tanstack/react-query';

import Board from './Board/Board';
import { ApiClient } from '../../../../../api';
import { useNotify } from '../../../../../contexts/notifications/notifications';
import { TasksViewProps } from '../../types';

interface DragDetails {
  taskId: number;
  statusId: number;
}

const TaskBoard: React.FC<TasksViewProps> = ({ boardId, searchTerm, scope, companyId, siteId, module }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();
  const [columns, setColumns] = useState(null);
  const [dragDetails, setDragDetails] = useState<DragDetails | null>(null);

  const { data: statusData, isLoading: isLoadingStatusData } = useQuery({
    queryFn: async () => {
      return ApiClient.taskManagement.getStatuses(boardId);
    },
    queryKey: ['statuses', { boardId }]
  });

  const { data: taskData, isLoading: isLoadingTaskData } = useQuery({
    queryFn: async () => {
      return ApiClient.taskManagement.getTasks(boardId, {
        skip: 0,
        limit: 1000,
        ...(searchTerm && { search: searchTerm })
      });
    },
    queryKey: ['tasks', { boardId, searchTerm }],
    placeholderData: keepPreviousData
  });

  const { mutateAsync: updateTask } = useMutation({
    mutationFn: (args: any) => ApiClient.taskManagement.updateTask(args.boardId, args.taskId, args.data)
  });

  const createColumnsFromData = (statuses: any[], tasks: any[]) => {
    const newColumns: any = {};

    statuses.forEach(status => {
      const { name, id } = status;
      newColumns[id] = {
        name: name,
        items: tasks.filter(task => task.status.id === id)
      };
    });

    setColumns(cloneDeep(newColumns));
  };

  const updateTaskDetails = async (details: DragDetails) => {
    const task = taskData?.items.find(item => {
      return item.id === details.taskId;
    });

    if (!task) return null;

    try {
      await updateTask({
        boardId: boardId,
        taskId: details.taskId,
        data: {
          assignee_id: task.assignee?.id || null,
          name: task.name,
          priority: task.priority,
          due_date: task.due_date,
          status_id: dragDetails?.statusId
        }
      });
      notify(`Task ${task.external_id} was updated`);
    } catch (e: any) {
      notify('Something went wrong with moving task...');
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    }
  };

  useEffect(() => {
    if (!isLoadingStatusData && statusData && !isLoadingTaskData && taskData) {
      createColumnsFromData(statusData.items, taskData.items);
    }
  }, [isLoadingStatusData, statusData, isLoadingTaskData, taskData, searchTerm]);

  useEffect(() => {
    if (dragDetails) {
      updateTaskDetails(dragDetails);
    }
  }, [dragDetails]);

  if (!columns || isLoadingStatusData || !statusData || isLoadingTaskData || !taskData) return null;

  return (
    <Board
      data={columns}
      siteId={siteId}
      companyId={companyId}
      scope={scope}
      setDragDetails={setDragDetails}
      module={module}
    />
  );
};

export default TaskBoard;
