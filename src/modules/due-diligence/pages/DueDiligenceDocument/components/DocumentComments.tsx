import React from 'react';
import Typography from '@mui/material/Typography';
import NewComment from './NewComment';
import CommentsList from './CommentsList';

interface DocumentCommentsProps {
  documentId: number;
  boardId: number;
  taskId?: number;
}

export const DocumentComments: React.FC<DocumentCommentsProps> = ({ documentId, boardId, taskId }) => {
  return (
    <>
      <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
        Comments
      </Typography>
      <NewComment entityId={documentId} boardId={boardId} taskId={taskId} />
      <CommentsList documentId={documentId} module="Diligence" />
    </>
  );
};

export default DocumentComments;
