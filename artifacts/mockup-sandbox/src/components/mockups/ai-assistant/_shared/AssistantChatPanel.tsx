import * as React from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import SendIcon from '@mui/icons-material/Send';

import { ActionCardItem } from './ActionCardItem';
import { SourcesDisclosure } from './SourcesDisclosure';
import { SuggestedPrompts } from './SuggestedPrompts';
import { MessageFeedback } from './MessageFeedback';
import type {
  AssistantActionCard,
  AssistantFeedbackRating,
  AssistantSource,
  AssistantSuggestedPrompt,
  AssistantToolInvocation
} from './assistant-types';

export interface ChatUiMessage {
  role: 'user' | 'assistant';
  content: string;
  // Persisted message id (only present once the turn is stored). Required to attach feedback.
  id?: number | null;
  action_cards?: AssistantActionCard[];
  used_tools?: AssistantToolInvocation[];
  sources?: AssistantSource[];
  feedback?: AssistantFeedbackRating | null;
}

// A friendly, classified chat error. `rate_limit` is the assistant-busy (429) case; everything else
// is `generic`. Both render with a Retry affordance that resends the last user message.
export interface AssistantChatError {
  kind: 'rate_limit' | 'generic';
  retryAfterSeconds?: number | null;
}

interface AssistantChatPanelProps {
  messages: ChatUiMessage[];
  isSending: boolean;
  error: AssistantChatError | null;
  suggestedPrompts: AssistantSuggestedPrompt[];
  suggestedContextLabel?: string | null;
  feedbackPendingId?: number | null;
  onSend: (text: string) => void;
  onRetry: () => void;
  onOpenCard: (route: string) => void;
  onFeedback: (message: ChatUiMessage, rating: AssistantFeedbackRating | null) => void;
}

const EMPTY_HINT =
  'Ask about your projects, workflows, or what to do next. I can point you to the right place — but you always take the action.';

const MessageBubble: React.FC<{
  message: ChatUiMessage;
  feedbackPending: boolean;
  onOpenCard: (route: string) => void;
  onFeedback: (message: ChatUiMessage, rating: AssistantFeedbackRating | null) => void;
}> = ({ message, feedbackPending, onOpenCard, onFeedback }) => {
  const isUser = message.role === 'user';
  const canFeedback = !isUser && message.id != null;
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
      {!isUser && message.sources && message.sources.length > 0 ? (
        <SourcesDisclosure sources={message.sources} />
      ) : null}
      {message.action_cards && message.action_cards.length > 0 ? (
        <Stack spacing={1} sx={{ width: '85%' }}>
          {message.action_cards.map((card, idx) => (
            <ActionCardItem key={`${card.route}-${idx}`} card={card} onOpen={onOpenCard} />
          ))}
        </Stack>
      ) : null}
      {canFeedback ? (
        <MessageFeedback
          value={message.feedback ?? null}
          disabled={feedbackPending}
          onChange={rating => onFeedback(message, rating)}
        />
      ) : null}
    </Stack>
  );
};

export const AssistantChatPanel: React.FC<AssistantChatPanelProps> = ({
  messages,
  isSending,
  error,
  suggestedPrompts,
  suggestedContextLabel,
  feedbackPendingId,
  onSend,
  onRetry,
  onOpenCard,
  onFeedback
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

  const errorMessage =
    error?.kind === 'rate_limit'
      ? `The assistant is busy right now. Please try again${
          error.retryAfterSeconds ? ` in ${error.retryAfterSeconds}s` : ' in a moment'
        }.`
      : 'Something went wrong. Please try again.';

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <Box ref={scrollRef} sx={{ flex: 1, overflowY: 'auto', px: 2, py: 2 }}>
        {messages.length === 0 ? (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              {EMPTY_HINT}
            </Typography>
            <SuggestedPrompts
              prompts={suggestedPrompts}
              contextLabel={suggestedContextLabel}
              disabled={isSending}
              onPick={text => onSend(text)}
            />
          </Box>
        ) : (
          <Stack spacing={2}>
            {messages.map((message, idx) => (
              <MessageBubble
                key={idx}
                message={message}
                feedbackPending={feedbackPendingId != null && feedbackPendingId === message.id}
                onOpenCard={onOpenCard}
                onFeedback={onFeedback}
              />
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
        {error ? (
          <Alert
            severity={error.kind === 'rate_limit' ? 'warning' : 'error'}
            sx={{ mt: 2 }}
            action={
              <Button color="inherit" size="small" onClick={onRetry} disabled={isSending}>
                Retry
              </Button>
            }
          >
            {errorMessage}
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
