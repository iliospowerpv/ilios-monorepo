import React from 'react';
import { TransitionGroup } from 'react-transition-group';
import Box from '@mui/material/Box';
import Collapse from '@mui/material/Collapse';

import CommentListItem from '../CommentListItem/CommentListItem';

interface Comment {
  id: number;
  entity_id: number;
  text: string;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
}

interface UniversalCommentsListProps {
  comments: Comment[];
}

export const UniversalCommentsList: React.FC<UniversalCommentsListProps> = ({ comments }) => (
  <Box>
    <TransitionGroup>
      {comments.map(comment => (
        <Collapse key={comment.id}>
          <CommentListItem
            user={{ first_name: comment.first_name, last_name: comment.last_name }}
            text={comment.text}
            date={comment.updated_at}
          />
        </Collapse>
      ))}
    </TransitionGroup>
  </Box>
);

export default UniversalCommentsList;
