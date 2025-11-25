import React from 'react';
import { AxiosError } from 'axios';
import { useQuery, queryOptions } from '@tanstack/react-query';
import { ApiClient } from '../../../api';
import { useNotify } from '../../../contexts/notifications/notifications';
import UniversalCommentsList from '../UniversalCommentsList/UniversalCommentsList';

const taskCommentsQuery = (taskId: number, enabled = true, throwOnError = false, module: string | undefined) =>
  queryOptions({
    queryKey: ['comments', 'tasks', { taskId, module }],
    queryFn: () => ApiClient.taskManagement.taskComments(taskId, { limit: 1000, skip: 0, module: module }),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

interface CommentsListProps {
  taskId: number;
  module?: string;
}

export const CommentsList: React.FC<CommentsListProps> = ({ taskId, module }) => {
  const notify = useNotify();
  const { data: taskCommentsResponse, error: taskCommentsError } = useQuery(
    taskCommentsQuery(taskId, true, false, module)
  );

  React.useEffect(() => {
    const e = taskCommentsError;
    if (e) {
      const errorMessage =
        (e instanceof AxiosError ? e.response?.data?.message : e.message) ||
        'An error occured when retrieving task comments';
      notify(errorMessage);
    }
  }, [notify, taskCommentsError]);

  if (!taskCommentsResponse) return null;

  const { items: comments } = taskCommentsResponse;

  return <UniversalCommentsList comments={comments} />;
};

export default CommentsList;
