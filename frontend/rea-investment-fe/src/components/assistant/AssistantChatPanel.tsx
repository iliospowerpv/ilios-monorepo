import * as React from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import SendIcon from '@mui/icons-material/Send';

import { ActionCardItem } from './ActionCardItem';
import type { AssistantActionCard, AssistantToolInvocation } from '../../api/assistant';

export interface ChatUiMessage {
  role: 'user' | 'assistant';
  content: string;
  action_cards?: AssistantActionCard[];
  used_tools?: AssistantToolInvocation[];
}

interface AssistantChatPanelProps {
  messages: ChatUiMessage[];
  isSending: boolean;
  isError: boolean;
  onSend: (text: string) => void;
  onOpenCard: (route: string) => void;
}

const EMPTY_HINT =
  'Ask about your projects, workflows, or what to do next. I can point you to the right place — but you always take the action.';

const MessageBubble: React.FC<{ message: ChatUiMessage; onOpenCard: (route: string) => void }> = ({
  message,
  onOpenCard
}) => {
  const isUser = message.role === 'user';
  return (
    <Stack spacing={1} alignItems={isUser ? 'flex-end' : 'flex-start'}>
      <Paper
        elevation={0}
        sx={{
          px: 1.5,
          py: 1,
          maxWidth: '85%',
          borderRadius: 2,
          bgcolor: isUser ? 'secondary.main' : 'action.hover',
          color: isUser ? 'secondary.contrastText' : 'text.primary'
        }}
      >
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
          {message.content}
        </Typography>
      </Paper>
      {message.action_cards && message.action_cards.length > 0 ? (
        <Stack spacing={1} sx={{ width: '85%' }}>
          {message.action_cards.map((card, idx) => (
            <ActionCardItem key={`${card.route}-${idx}`} card={card} onOpen={onOpenCard} />
          ))}
        </Stack>
      ) : null}
    </Stack>
  );
};

export const AssistantChatPanel: React.FC<AssistantChatPanelProps> = ({
  messages,
  isSending,
  isError,
  onSend,
  onOpenCard
}) => {
  const [draft, setDraft] = React.useState('');
  const scrollRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isSending]);

  const submit = () => {
    const text = draft.trim();
    if (!text || isSending) return;
    onSend(text);
    setDraft('');
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <Box ref={scrollRef} sx={{ flex: 1, overflowY: 'auto', px: 2, py: 2 }}>
        {messages.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            {EMPTY_HINT}
          </Typography>
        ) : (
          <Stack spacing={2}>
            {messages.map((message, idx) => (
              <MessageBubble key={idx} message={message} onOpenCard={onOpenCard} />
            ))}
          </Stack>
        )}
        {isSending ? (
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 2 }}>
            <CircularProgress size={16} color="secondary" />
            <Typography variant="caption" color="text.secondary">
              Thinking…
            </Typography>
          </Stack>
        ) : null}
        {isError ? (
          <Alert severity="error" sx={{ mt: 2 }}>
            Something went wrong. Please try again.
          </Alert>
        ) : null}
      </Box>
      <Box sx={{ p: 1.5, borderTop: 1, borderColor: 'divider' }}>
        <Stack direction="row" spacing={1} alignItems="flex-end">
          <TextField
            value={draft}
            onChange={event => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the assistant…"
            size="small"
            fullWidth
            multiline
            maxRows={4}
            disabled={isSending}
          />
          <IconButton
            color="secondary"
            onClick={submit}
            disabled={isSending || draft.trim().length === 0}
            aria-label="Send message"
          >
            <SendIcon />
          </IconButton>
        </Stack>
      </Box>
    </Box>
  );
};
