import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNotify } from '../../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../../api';
import { UniversalDescription, DescriptionFormSubmitHandler } from './UniversalDescription';

interface DescriptionProps {
  descriptionText: string | null;
  boardId: number;
  taskId: number;
}

type EditDescriptionMutationArgs = {
  boardId: number;
  taskId: number;
  description: string | null;
};

export const TaskDescription: React.FC<DescriptionProps> = ({ descriptionText, boardId, taskId }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();

  const { mutateAsync: updateDescription } = useMutation({
    mutationFn: (args: EditDescriptionMutationArgs) =>
      ApiClient.taskManagement.updateTaskDescription(args.boardId, args.taskId, args.description)
  });

  const onSubmit: DescriptionFormSubmitHandler = async data => {
    try {
      const response = await updateDescription({
        boardId,
        taskId,
        description: data.description
      });
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      notify(response.message || `Task description was successfully updated.`);
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when updating the task description...');
    }
  };

  return <UniversalDescription descriptionText={descriptionText} onSubmitEdit={onSubmit} maxLength={2000} />;
};

export default TaskDescription;
