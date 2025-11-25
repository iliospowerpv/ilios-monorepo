import React from 'react';
import { AxiosError } from 'axios';
import { useQuery, queryOptions } from '@tanstack/react-query';
import { ApiClient } from '../../../../../api';
import { useNotify } from '../../../../../contexts/notifications/notifications';
import UniversalCommentsList from '../../../../../components/forms/UniversalCommentsList/UniversalCommentsList';

const documentCommentsQuery = (documentId: number, enabled = true, throwOnError = false, module: string | undefined) =>
  queryOptions({
    queryKey: ['comments', 'documents', { documentId, module }],
    queryFn: () => ApiClient.dueDiligence.documentComments({ documentId, limit: 1000, skip: 0, module: module }),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

interface CommentsListProps {
  documentId: number;
  module?: string;
}

export const CommentsList: React.FC<CommentsListProps> = ({ documentId, module }) => {
  const notify = useNotify();
  const { data: documentCommentsResponse, error: documentCommentsError } = useQuery(
    documentCommentsQuery(documentId, true, false, module)
  );

  React.useEffect(() => {
    const e = documentCommentsError;
    if (e) {
      const errorMessage =
        (e instanceof AxiosError ? e.response?.data?.message : e.message) ||
        'An error occured when retrieving document comments';
      notify(errorMessage);
    }
  }, [notify, documentCommentsError]);

  if (!documentCommentsResponse) return null;

  const { items: comments } = documentCommentsResponse;

  return <UniversalCommentsList comments={comments} />;
};

export default CommentsList;
