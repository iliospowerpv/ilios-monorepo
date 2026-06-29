import * as React from 'react';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';

import type { AssistantConversationSummary } from '../../api/assistant';

interface ConversationListProps {
  conversations: AssistantConversationSummary[];
  isLoading: boolean;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
}

const formatWhen = (iso: string): string => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString();
};

export const ConversationList: React.FC<ConversationListProps> = ({ conversations, isLoading, onSelect, onDelete }) => {
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress size={20} color="secondary" />
      </Box>
    );
  }

  if (conversations.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
        No saved conversations yet.
      </Typography>
    );
  }

  return (
    <List dense disablePadding>
      {conversations.map(conversation => (
        <ListItem
          key={conversation.id}
          disablePadding
          secondaryAction={
            <IconButton
              edge="end"
              size="small"
              aria-label="Delete conversation"
              onClick={() => onDelete(conversation.id)}
            >
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          }
        >
          <ListItemButton onClick={() => onSelect(conversation.id)}>
            <ListItemText
              primary={conversation.title || 'Conversation'}
              secondary={formatWhen(conversation.updated_at)}
              primaryTypographyProps={{ noWrap: true, variant: 'body2' }}
              secondaryTypographyProps={{ variant: 'caption' }}
            />
          </ListItemButton>
        </ListItem>
      ))}
    </List>
  );
};
