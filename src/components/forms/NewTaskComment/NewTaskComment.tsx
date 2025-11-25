import React from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';

import { useNotify } from '../../../contexts/notifications/notifications';
import { ApiClient } from '../../../api';
import UniversalNewCommentForm, {
  NewCommentFormSubmitHandler,
  UniversalNewCommentFormRef
} from '../UniversalNewCommentForm/UniversalNewCommentForm';

interface NewTaskCommentProps {
  taskId: number;
  boardId: number;
  module?: string;
}

type PostTaskCommentMutationArgs = {
  commentText: string;
  mentions: number[];
  permission_module?: string;
};

export const NewTaskComment: React.FC<NewTaskCommentProps> = ({ taskId, boardId, module }) => {
  const formRef = React.useRef<UniversalNewCommentFormRef | null>(null);
  const notify = useNotify();
  const queryClient = useQueryClient();

  const { data, error } = useQuery({
    queryKey: ['user-mentions-suggestions', { boardId }],
    queryFn: () => ApiClient.taskManagement.potentialTaskAssignees(boardId, {}),
    initialData: { items: [] }
  });

  React.useEffect(() => {
    if (error && error instanceof AxiosError) notify(error.response?.data);
  }, [error, notify]);

  const { mutateAsync: postComment } = useMutation({
    mutationFn: (args: PostTaskCommentMutationArgs) =>
      ApiClient.taskManagement.postTaskComment(taskId, args.commentText, args.mentions, module)
  });

  const onSubmit: NewCommentFormSubmitHandler = async data => {
    try {
      const response = await postComment({
        commentText: data.value.plainValue,
        mentions: data.value.mentions.map(userId => Number.parseInt(userId))
      });
      queryClient.invalidateQueries({ queryKey: ['comments'] });
      formRef.current?.resetForm && formRef.current?.resetForm();
      notify(response.message || `Task comment was successfully posted.`);
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when posting a task comment...');
    }
  };

  return <UniversalNewCommentForm ref={formRef} onSubmit={onSubmit} usersList={data.items || []} />;
};

export default NewTaskComment;
