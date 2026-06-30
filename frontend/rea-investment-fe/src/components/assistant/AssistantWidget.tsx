import * as React from 'react';
import Fab from '@mui/material/Fab';
import Drawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import { ThemeProvider } from '@mui/material/styles';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import CloseIcon from '@mui/icons-material/Close';
import AddCommentOutlinedIcon from '@mui/icons-material/AddCommentOutlined';
import HistoryIcon from '@mui/icons-material/History';
import ChatOutlinedIcon from '@mui/icons-material/ChatOutlined';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';

import { ApiClient } from '../../api';
import { useAuth } from '../../contexts/auth/auth';
import { useEntityContext } from '../../contexts/entityContext';
import { AssistantChatPanel, ChatUiMessage, AssistantChatError } from './AssistantChatPanel';
import { ConversationList } from './ConversationList';
import type { AssistantChatRequest, AssistantContextHints, AssistantFeedbackRating } from '../../api/assistant';
import { getTheme } from '../../utils/styles/theme';

const DRAWER_WIDTH = 420;
// The shared MuiDrawer override paints the Drawer surface dark even in light mode (it is reused by the
// dark left-nav sidebar). Render the assistant panel under the dark theme so all child text, inputs,
// and chips resolve to light, high-contrast colors against that dark surface instead of the
// light-mode defaults (black text) that were disappearing into the dark background.
const ASSISTANT_THEME = getTheme('dark');
const CONFIG_KEY = ['assistant', 'config'];
const CONVERSATIONS_KEY = ['assistant', 'conversations'];
const HISTORY_LIMIT = 20;

type PanelView = 'chat' | 'history';

// Translate an axios failure on /chat into a friendly, classified error for the panel. 429 means the
// assistant (or its model backend) is busy; we surface the server-provided Retry-After when present.
const toChatError = (err: unknown): AssistantChatError => {
  if (axios.isAxiosError(err) && err.response?.status === 429) {
    const header = err.response.headers?.['retry-after'];
    const seconds = header != null ? Number(header) : NaN;
    return { kind: 'rate_limit', retryAfterSeconds: Number.isFinite(seconds) ? seconds : null };
  }
  return { kind: 'generic' };
};

export const AssistantWidget: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { currentCompany, currentProject } = useEntityContext();
  const queryClient = useQueryClient();

  const [open, setOpen] = React.useState(false);
  const [view, setView] = React.useState<PanelView>('chat');
  const [conversationId, setConversationId] = React.useState<string | null>(null);
  const [messages, setMessages] = React.useState<ChatUiMessage[]>([]);
  const [chatError, setChatError] = React.useState<AssistantChatError | null>(null);
  // The exact request that was last attempted, so "Retry" can resend it verbatim (the user message is
  // already in the transcript, so we never re-append it).
  const [pendingRequest, setPendingRequest] = React.useState<AssistantChatRequest | null>(null);

  // Probe: reachable ONLY when the backend flag is on (404 otherwise). A successful fetch means the
  // assistant is available; any error keeps the FAB hidden. Never retried so a 404 fails fast.
  const configQuery = useQuery({
    queryKey: CONFIG_KEY,
    queryFn: ApiClient.assistant.getConfig,
    enabled: isAuthenticated,
    retry: false,
    staleTime: 5 * 60 * 1000
  });

  const conversationsQuery = useQuery({
    queryKey: CONVERSATIONS_KEY,
    queryFn: () => ApiClient.assistant.listConversations(),
    enabled: isAuthenticated && configQuery.isSuccess && open && view === 'history'
  });

  // Static, page-aware example prompts for the empty chat state. No business data is fetched.
  const suggestedPromptsQuery = useQuery({
    queryKey: [
      'assistant',
      'suggested-prompts',
      location.pathname,
      currentCompany?.id ?? null,
      currentProject?.id ?? null
    ],
    queryFn: () =>
      ApiClient.assistant.getSuggestedPrompts({
        route: location.pathname,
        siteId: currentProject?.id ?? null,
        companyId: currentCompany?.id ?? null
      }),
    enabled: isAuthenticated && configQuery.isSuccess && open && view === 'chat',
    staleTime: 5 * 60 * 1000
  });

  const buildContext = React.useCallback((): AssistantContextHints => {
    return {
      route: location.pathname,
      company_id: currentCompany?.id ?? null,
      // Project == Site (UI label only); send the same id under both keys.
      site_id: currentProject?.id ?? null,
      project_id: currentProject?.id ?? null
    };
  }, [location.pathname, currentCompany?.id, currentProject?.id]);

  const chatMutation = useMutation({
    mutationFn: (request: AssistantChatRequest) => ApiClient.assistant.chat(request),
    onSuccess: response => {
      setConversationId(prev => response.conversation_id ?? prev);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: response.reply,
          id: response.message_id ?? null,
          action_cards: response.action_cards,
          used_tools: response.used_tools,
          sources: response.sources,
          feedback: null
        }
      ]);
      setChatError(null);
      setPendingRequest(null);
      queryClient.invalidateQueries({ queryKey: CONVERSATIONS_KEY });
    },
    onError: err => {
      setChatError(toChatError(err));
    }
  });

  const loadMutation = useMutation({
    mutationFn: (id: number) => ApiClient.assistant.getConversation(id),
    onSuccess: detail => {
      setMessages(
        detail.messages.map(message => ({
          role: message.role,
          content: message.content,
          id: message.id,
          action_cards: message.action_cards,
          used_tools: message.used_tools,
          sources: message.sources,
          feedback: message.feedback ?? null
        }))
      );
      setConversationId(String(detail.id));
      setChatError(null);
      setPendingRequest(null);
      setView('chat');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => ApiClient.assistant.deleteConversation(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: CONVERSATIONS_KEY });
      if (conversationId === String(id)) {
        setMessages([]);
        setConversationId(null);
      }
    }
  });

  // Owner-scoped thumbs feedback on a persisted assistant reply. Optimistic, with revert on failure.
  const feedbackMutation = useMutation({
    mutationFn: ({ messageId, rating }: { messageId: number; rating: AssistantFeedbackRating | null }) =>
      ApiClient.assistant.setMessageFeedback(Number(conversationId), messageId, { rating }),
    onMutate: ({ messageId, rating }) => {
      const previous = messages.find(message => message.id === messageId)?.feedback ?? null;
      setMessages(prev => prev.map(message => (message.id === messageId ? { ...message, feedback: rating } : message)));
      return { previous, messageId };
    },
    onError: (_err, _vars, context) => {
      if (context) {
        setMessages(prev =>
          prev.map(message => (message.id === context.messageId ? { ...message, feedback: context.previous } : message))
        );
      }
    }
  });

  const handleSend = (text: string) => {
    const history = messages.slice(-HISTORY_LIMIT).map(message => ({ role: message.role, content: message.content }));
    const request: AssistantChatRequest = {
      message: text,
      history,
      context: buildContext(),
      conversation_id: conversationId,
      persist: true
    };
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setChatError(null);
    setPendingRequest(request);
    chatMutation.mutate(request);
  };

  const handleRetry = () => {
    if (!pendingRequest) return;
    setChatError(null);
    chatMutation.mutate(pendingRequest);
  };

  const handleFeedback = (message: ChatUiMessage, rating: AssistantFeedbackRating | null) => {
    if (message.id == null || conversationId == null) return;
    feedbackMutation.mutate({ messageId: message.id, rating });
  };

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setChatError(null);
    setPendingRequest(null);
    setView('chat');
  };

  const handleOpenCard = (route: string) => {
    setOpen(false);
    navigate(route);
  };

  if (!isAuthenticated || !configQuery.isSuccess) {
    return null;
  }

  return (
    <>
      <Tooltip title="AI Assistant" placement="left">
        <Fab
          color="secondary"
          aria-label="Open AI Assistant"
          onClick={() => setOpen(true)}
          sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: theme => theme.zIndex.drawer + 2 }}
        >
          <SmartToyOutlinedIcon />
        </Fab>
      </Tooltip>

      <ThemeProvider theme={ASSISTANT_THEME}>
        <Drawer
          anchor="right"
          open={open}
          onClose={() => setOpen(false)}
          PaperProps={{
            sx: {
              width: { xs: '100%', sm: DRAWER_WIDTH },
              display: 'flex',
              flexDirection: 'column',
              color: 'text.primary'
            }
          }}
        >
          <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <SmartToyOutlinedIcon color="secondary" />
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
                AI Assistant
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Read-only guidance — you take the actions
              </Typography>
            </Box>
            <Stack direction="row" spacing={0.5}>
              <Tooltip title="New conversation">
                <IconButton size="small" onClick={handleNewConversation} aria-label="New conversation">
                  <AddCommentOutlinedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={view === 'history' ? 'Back to chat' : 'Conversation history'}>
                <IconButton
                  size="small"
                  onClick={() => setView(view === 'history' ? 'chat' : 'history')}
                  aria-label="Toggle conversation history"
                >
                  {view === 'history' ? <ChatOutlinedIcon fontSize="small" /> : <HistoryIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
              <Tooltip title="Close">
                <IconButton size="small" onClick={() => setOpen(false)} aria-label="Close assistant">
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Stack>
          </Box>
          <Divider />

          <Box sx={{ flex: 1, minHeight: 0 }}>
            {view === 'history' ? (
              <ConversationList
                conversations={conversationsQuery.data?.items ?? []}
                isLoading={conversationsQuery.isLoading || loadMutation.isPending}
                activeId={conversationId ? Number(conversationId) : null}
                onSelect={id => loadMutation.mutate(id)}
                onDelete={id => deleteMutation.mutate(id)}
              />
            ) : (
              <AssistantChatPanel
                messages={messages}
                isSending={chatMutation.isPending}
                error={chatError}
                suggestedPrompts={suggestedPromptsQuery.data?.prompts ?? []}
                suggestedContextLabel={suggestedPromptsQuery.data?.context_label ?? null}
                navigatorCards={suggestedPromptsQuery.data?.action_cards ?? []}
                feedbackPendingId={feedbackMutation.isPending ? (feedbackMutation.variables?.messageId ?? null) : null}
                onSend={handleSend}
                onRetry={handleRetry}
                onOpenCard={handleOpenCard}
                onPromptCard={handleSend}
                onFeedback={handleFeedback}
              />
            )}
          </Box>
        </Drawer>
      </ThemeProvider>
    </>
  );
};
