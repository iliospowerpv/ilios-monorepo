import React from 'react';
import Typography from '@mui/material/Typography';
import NewTaskComment from '../NewTaskComment/NewTaskComment';
import CommentsList from '../CommentsList/CommentsList';

interface TaskCommentsProps {
  taskId: number;
  boardId: number;
  module?: string;
}

export const TaskComments: React.FC<TaskCommentsProps> = ({ taskId, boardId, module }) => {
  return (
    <>
      <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
        Comments
      </Typography>
      <NewTaskComment taskId={taskId} boardId={boardId} module={module} />
      <CommentsList taskId={taskId} module={module} />
    </>
  );
};

export default TaskComments;
