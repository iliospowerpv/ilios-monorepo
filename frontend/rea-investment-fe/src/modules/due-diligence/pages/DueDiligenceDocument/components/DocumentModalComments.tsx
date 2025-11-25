import React from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import AddCommentIcon from '@mui/icons-material/AddComment';

import NewComment from './NewComment';
import { ApiClient } from '../../../../../api';
import UniversalCommentsList from '../../../../../components/forms/UniversalCommentsList/UniversalCommentsList';
import Stack from '@mui/material/Stack';

type SetDocumentKeyValueFn = typeof ApiClient.dueDiligence.setDocumentKeyValue;
type SetDocumentKeyValueParams = Parameters<SetDocumentKeyValueFn>[number]['params'];

interface Comment {
  id: number;
  entity_id: number;
  text: string;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
}

interface DocumentModalCommentsProps {
  termId: number | null;
  termKey: string;
  documentId: number;
  siteId: number;
  comments: Comment[] | null;
  boardId: number;
  fileId: number;
  taskId: number;
}

export const DocumentModalComments: React.FC<DocumentModalCommentsProps> = ({
  termId,
  termKey,
  documentId,
  siteId,
  comments,
  boardId,
  fileId,
  taskId
}) => {
  const queryClient = useQueryClient();
  const [showAddComment, setShowAddComment] = React.useState<boolean>(false);
  const [newTermId, setNewTermId] = React.useState<number | null>(termId);

  const { mutateAsync: updateDocumentKeyValue } = useMutation({
    mutationFn: (params: SetDocumentKeyValueParams) =>
      ApiClient.dueDiligence.setDocumentKeyValue({ siteId, documentId, params })
  });

  const setEmptyValue = async () => {
    try {
      const response = await updateDocumentKeyValue({
        name: termKey,
        value: ' '
      });

      setNewTermId(response?.id);
      queryClient.invalidateQueries({ queryKey: ['document-terms'] });
    } catch (e: any) {
      console.log(e.response?.data?.message || 'Something went wrong when updating a document key...');
    }
  };

  const handleAddComment = () => {
    if (!termId) {
      setEmptyValue();
    }

    setShowAddComment(true);
  };

  const onAction = () => {
    setShowAddComment(false);
  };

  return (
    <Box pl="12px">
      <Stack direction="row" width="100%" py="16px" spacing={1} justifyContent="space-between">
        <Typography variant="h6" fontSize="16px" my="8px" fontWeight="600">
          {(showAddComment || comments?.length) && 'Comments'}
        </Typography>
        <Button
          size="small"
          disabled={showAddComment}
          data-testid="add-comment__btn"
          onClick={handleAddComment}
          startIcon={<AddCommentIcon />}
        >
          Add Comment
        </Button>
      </Stack>
      {showAddComment && (
        <NewComment
          entityId={(newTermId ?? termId) as number}
          entityType="document_key"
          boardId={boardId}
          isDocumentModal={true}
          onAction={onAction}
          fileId={fileId}
          taskId={taskId}
        />
      )}
      <UniversalCommentsList comments={comments || []} />
    </Box>
  );
};

export default DocumentModalComments;
