import * as React from 'react';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';

import type { AssistantConversationSummary } from '../../api/assistant';

interface ConversationListProps {
  conversations: AssistantConversationSummary[];
  isLoading: boolean;
  activeId?: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
}

// Compact, human-friendly "x ago" for the last-activity timestamp; falls back to a locale date for
// anything older than a week (or empty on an unparseable value).
const formatRelative = (iso: string): string => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
};

const formatCount = (count: number): string => `${count} message${count === 1 ? '' : 's'}`;

export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  isLoading,
  activeId,
  onSelect,
  onDelete
}) => {
  const [confirmingId, setConfirmingId] = React.useState<number | null>(null);

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
        No saved conversations yet. Start chatting and your threads will show up here.
      </Typography>
    );
  }

  return (
    <List dense disablePadding>
      {conversations.map(conversation => {
        const isConfirming = confirmingId === conversation.id;
        return (
          <ListItem
            key={conversation.id}
            disablePadding
            secondaryAction={
              isConfirming ? (
                <Stack direction="row">
                  <Tooltip title="Confirm delete">
                    <IconButton
                      edge="end"
                      size="small"
                      color="error"
                      aria-label="Confirm delete conversation"
                      onClick={() => {
                        onDelete(conversation.id);
                        setConfirmingId(null);
                      }}
                    >
                      <CheckIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Cancel">
                    <IconButton
                      edge="end"
                      size="small"
                      aria-label="Cancel delete"
                      onClick={() => setConfirmingId(null)}
                    >
                      <CloseIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Stack>
              ) : (
                <Tooltip title="Delete conversation">
                  <IconButton
                    edge="end"
                    size="small"
                    aria-label="Delete conversation"
                    onClick={() => setConfirmingId(conversation.id)}
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )
            }
          >
            <ListItemButton
              selected={activeId != null && activeId === conversation.id}
              onClick={() => onSelect(conversation.id)}
            >
              <ListItemText
                primary={conversation.title || 'Conversation'}
                secondary={`${formatRelative(conversation.updated_at)} · ${formatCount(conversation.message_count)}`}
                primaryTypographyProps={{ noWrap: true, variant: 'body2' }}
                secondaryTypographyProps={{ variant: 'caption', noWrap: true }}
              />
            </ListItemButton>
          </ListItem>
        );
      })}
    </List>
  );
};
