import React from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';

import { useNotify } from '../../../../../contexts/notifications/notifications';
import { ApiClient } from '../../../../../api';
import UniversalNewCommentForm, {
  NewCommentFormSubmitHandler,
  UniversalNewCommentFormRef
} from '../../../../../components/forms/UniversalNewCommentForm/UniversalNewCommentForm';

interface NewCommentProps {
  boardId: number;
  entityId: number;
  entityType?: string;
  isDocumentModal?: boolean;
  onAction?: () => void;
  fileId?: number;
  taskId?: number;
}

type PostDocumentCommentMutationArgs = {
  commentText: string;
  mentionedUsersIds: number[];
};

export const NewComment: React.FC<NewCommentProps> = ({
  entityId,
  boardId,
  entityType,
  isDocumentModal,
  onAction,
  fileId,
  taskId
}) => {
  const formRef = React.useRef<UniversalNewCommentFormRef | null>(null);
  const notify = useNotify();
  const queryClient = useQueryClient();

  const { data, error } = useQuery({
    queryKey: ['user-mentions-suggestions', { boardId }],
    queryFn: () => ApiClient.taskManagement.potentialTaskAssignees(boardId, { task_id: taskId }),
    initialData: { items: [] }
  });

  React.useEffect(() => {
    if (error && error instanceof AxiosError) notify(error.response?.data);
  }, [error, notify]);

  const { mutateAsync: postComment } = useMutation({
    mutationFn: (args: PostDocumentCommentMutationArgs) =>
      ApiClient.dueDiligence.postDocumentComment(
        entityId,
        args.commentText,
        args.mentionedUsersIds,
        entityType,
        fileId,
        'Diligence'
      )
  });

  const onSubmit: NewCommentFormSubmitHandler = async data => {
    try {
      const response = await postComment({
        commentText: data.value.plainValue,
        mentionedUsersIds: data.value.mentions.map(userId => Number.parseInt(userId))
      });
      if (entityType === 'document_key') {
        onAction && onAction();
        queryClient.invalidateQueries({ queryKey: ['document-terms'] });
      } else {
        queryClient.invalidateQueries({ queryKey: ['comments'] });
      }
      formRef.current?.resetForm && formRef.current?.resetForm();
      notify(response.message || `Document comment was successfully posted.`);
    } catch (e: any) {
      notify(e.response?.data?.message || 'Something went wrong when posting a document comment...');
    }
  };

  return (
    <UniversalNewCommentForm
      ref={formRef}
      usersList={data.items || []}
      isDocumentModal={isDocumentModal}
      onSubmit={onSubmit}
      onAction={onAction}
    />
  );
};

export default NewComment;
