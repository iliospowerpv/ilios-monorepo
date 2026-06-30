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
import { useWorkflowCompanion } from '../../contexts/workflowCompanion';
import { AssistantChatPanel, ChatUiMessage, AssistantChatError } from './AssistantChatPanel';
import { ConversationList } from './ConversationList';
import type {
  AssistantChatRequest,
  AssistantContextHints,
  AssistantFeedbackRating,
  AssistantUiEventName
} from '../../api/assistant';
import { getTheme } from '../../utils/styles/theme';
import { useAssistantLauncherPosition, LAUNCHER_MARGIN, type LauncherSide } from './useAssistantLauncherPosition';
import { useAssistantAnalytics } from './useAssistantAnalytics';
import { AssistantLauncherCallout } from './AssistantLauncherCallout';
import { useAssistantLauncher } from '../../contexts/assistantLauncher';

// Pointer travel (px) below which a press is treated as a click (open) rather than a drag (reposition).
const DRAG_THRESHOLD = 5;

const DRAWER_WIDTH = 420;
// The shared MuiDrawer override paints the Drawer surface dark even in light mode (it is reused by the
// dark left-nav sidebar). Render the assistant panel under the dark theme so all child text, inputs,
// and chips resolve to light, high-contrast colors against that dark surface instead of the
// light-mode defaults (black text) that were disappearing into the dark background.
const ASSISTANT_THEME = getTheme('dark');
const CONFIG_KEY = ['assistant', 'config'];
const CONVERSATIONS_KEY = ['assistant', 'conversations'];
const HISTORY_LIMIT = 20;
// Per-user localStorage key prefix for the one-time first-run coachmark (suffixed with the user id).
const FIRST_RUN_KEY_PREFIX = 'ilios.assistant.firstRunSeen.';

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
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { currentCompany, currentProject } = useEntityContext();
  // Advisory snapshot of the workflow run the user is currently inside (published by <Wizard>). When
  // present, the assistant switches into read-only "Workflow Companion Mode". Identifiers only.
  const { companion } = useWorkflowCompanion();
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
      currentProject?.id ?? null,
      // Companion run/step so the prompts + cards refresh as the user advances through a wizard.
      companion?.runId ?? null,
      companion?.workflowId ?? null,
      companion?.stepId ?? null
    ],
    queryFn: () =>
      ApiClient.assistant.getSuggestedPrompts({
        route: location.pathname,
        siteId: currentProject?.id ?? null,
        companyId: currentCompany?.id ?? null,
        runId: companion?.runId ?? null,
        workflowId: companion?.workflowId ?? null,
        stepId: companion?.stepId ?? null
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
      project_id: currentProject?.id ?? null,
      // Advisory workflow run/step (when inside a wizard). Identifiers only — the assistant reads the
      // run server-side via its owner-scoped tool; NEVER form values, files, or confirm tokens.
      run_id: companion?.runId ?? null,
      workflow_id: companion?.workflowId ?? null,
      step_id: companion?.stepId ?? null
    };
  }, [
    location.pathname,
    currentCompany?.id,
    currentProject?.id,
    companion?.runId,
    companion?.workflowId,
    companion?.stepId
  ]);

  // First-party, privacy-bounded UI-interaction analytics. Inert unless the assistant is actually
  // available (flag on + authenticated). Records ONLY bounded event metadata — never message text.
  const analytics = useAssistantAnalytics(isAuthenticated && configQuery.isSuccess);
  // Stamp every event with the current route + companion mode so the server can bucket adoption by
  // module and split in-wizard usage. `detail` is an optional small allowlisted qualifier.
  const trackUi = React.useCallback(
    (event: AssistantUiEventName, detail?: string | null) =>
      analytics.track(event, {
        detail: detail ?? null,
        route: location.pathname,
        inCompanion: Boolean(companion?.runId)
      }),
    [analytics, location.pathname, companion?.runId]
  );

  // --- Shared launcher + native discoverability ----------------------------------------------
  // A shared context lets discoverability entry points elsewhere in the app (top bar, help menu)
  // open THIS existing drawer. Opening the drawer is the ONLY effect — purely navigational, never an
  // action, preview, or execution. The widget also publishes its availability so those entries only
  // render when the assistant is actually reachable (flag on + authenticated).
  const { openRequest, setAvailable } = useAssistantLauncher();
  const assistantAvailable = isAuthenticated && configQuery.isSuccess;

  React.useEffect(() => {
    setAvailable(assistantAvailable);
    return () => setAvailable(false);
  }, [assistantAvailable, setAvailable]);

  // First-run guidance: a one-time, per-user, dismissible coachmark beside the launcher. It NEVER
  // auto-opens the drawer; it only invites. Persisted in localStorage keyed by the user id.
  const userId = user?.id ?? null;
  const firstRunKey = userId != null ? `${FIRST_RUN_KEY_PREFIX}${userId}` : null;
  const [firstRunSeen, setFirstRunSeen] = React.useState(true);
  React.useEffect(() => {
    if (!firstRunKey) {
      setFirstRunSeen(true);
      return;
    }
    try {
      setFirstRunSeen(localStorage.getItem(firstRunKey) === '1');
    } catch {
      setFirstRunSeen(true);
    }
  }, [firstRunKey]);
  const markFirstRunSeen = React.useCallback(() => {
    setFirstRunSeen(true);
    if (firstRunKey) {
      try {
        localStorage.setItem(firstRunKey, '1');
      } catch {
        // Best-effort: a storage failure just means the hint may appear again later.
      }
    }
  }, [firstRunKey]);

  // Proactive per-step workflow nudge: shown ONLY while inside a guided run, once per run+step, and
  // dismissible. Like first-run it NEVER auto-opens — the assistant stays read-only / propose-only.
  const stepKey = companion?.runId != null ? `${companion.runId}:${companion.stepId ?? ''}` : null;
  const [dismissedSteps, setDismissedSteps] = React.useState<Set<string>>(() => new Set());
  const dismissProactiveStep = React.useCallback(() => {
    if (stepKey) {
      setDismissedSteps(prev => new Set(prev).add(stepKey));
    }
  }, [stepKey]);

  const showFirstRun = assistantAvailable && !open && userId != null && !firstRunSeen;
  const showProactiveHint =
    assistantAvailable && !open && !showFirstRun && stepKey != null && !dismissedSteps.has(stepKey);

  // Emit the "shown" impression once per surface, guarded by refs so toggling the drawer open/closed
  // does not re-count an impression for the same first-run / step.
  const firstRunShownRef = React.useRef(false);
  React.useEffect(() => {
    if (showFirstRun && !firstRunShownRef.current) {
      firstRunShownRef.current = true;
      trackUi('first_run_shown');
    }
  }, [showFirstRun, trackUi]);
  const proactiveShownRef = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (showProactiveHint && stepKey && proactiveShownRef.current !== stepKey) {
      proactiveShownRef.current = stepKey;
      trackUi('proactive_hint_shown', 'step_help');
    }
  }, [showProactiveHint, stepKey, trackUi]);

  // External open requests from discoverability entry points. Each carries only a bounded source
  // token; the widget opens the drawer and records the discoverability event from the single
  // analytics instance.
  const handledOpenRef = React.useRef(0);
  React.useEffect(() => {
    if (!openRequest || openRequest.id === handledOpenRef.current) return;
    handledOpenRef.current = openRequest.id;
    setOpen(true);
    markFirstRunSeen();
    if (openRequest.source) {
      trackUi('discoverability_entry_clicked', openRequest.source);
    }
  }, [openRequest, markFirstRunSeen, trackUi]);

  // `assistant_opened` is recorded once per closed->open transition, regardless of which entry point
  // opened the drawer (FAB, top-bar, help menu, first-run / proactive CTA). The source-specific
  // events above provide attribution; this gives a single, never-double-counted "opened" total.
  const wasOpenRef = React.useRef(false);
  React.useEffect(() => {
    if (open && !wasOpenRef.current) {
      wasOpenRef.current = true;
      trackUi('assistant_opened');
    } else if (!open) {
      wasOpenRef.current = false;
    }
  }, [open, trackUi]);

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

  // User-initiated close (Drawer backdrop/Esc or the Close button). Distinct from a card navigation,
  // which closes the drawer as a side effect of navigating, not as a dismiss.
  const handleCloseDrawer = () => {
    trackUi('assistant_dismissed');
    setOpen(false);
  };

  const handleOpenCard = (route: string) => {
    setOpen(false);
    navigate(route);
  };

  // --- Draggable launcher ---------------------------------------------------
  const { position, setPosition } = useAssistantLauncherPosition();
  // Live coordinates while a drag is in progress; null when the launcher rests at its anchored spot.
  const [dragPos, setDragPos] = React.useState<{ x: number; y: number } | null>(null);
  const dragInfo = React.useRef<{
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    moved: boolean;
  } | null>(null);
  // Set on a drag-release so the synthetic click that follows pointerup does not also open the drawer.
  const suppressClick = React.useRef(false);

  const handlePointerDown = (event: React.PointerEvent<HTMLButtonElement>) => {
    // Only react to the primary (left/touch) button; let modified clicks behave normally.
    if (event.button !== 0) return;
    const rect = event.currentTarget.getBoundingClientRect();
    dragInfo.current = {
      startX: event.clientX,
      startY: event.clientY,
      originX: rect.left,
      originY: rect.top,
      moved: false
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLButtonElement>) => {
    const info = dragInfo.current;
    if (!info) return;
    const dx = event.clientX - info.startX;
    const dy = event.clientY - info.startY;
    if (!info.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    info.moved = true;
    setDragPos({ x: info.originX + dx, y: info.originY + dy });
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLButtonElement>) => {
    const info = dragInfo.current;
    dragInfo.current = null;
    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      // Pointer capture may already be released.
    }
    if (info?.moved && dragPos) {
      // Snap horizontally to the nearest screen edge; keep the chosen vertical offset.
      const centerX = dragPos.x + event.currentTarget.offsetWidth / 2;
      const side: LauncherSide = centerX < window.innerWidth / 2 ? 'left' : 'right';
      setPosition({ side, y: dragPos.y });
      suppressClick.current = true;
    }
    setDragPos(null);
  };

  const handleLauncherClick = () => {
    // A real drag just ended — swallow this click instead of opening the drawer.
    if (suppressClick.current) {
      suppressClick.current = false;
      return;
    }
    setOpen(true);
    markFirstRunSeen();
  };

  if (!isAuthenticated || !configQuery.isSuccess) {
    return null;
  }

  return (
    <>
      <Tooltip title="AI Assistant" placement="left">
        <Fab
          variant="extended"
          aria-label="Open AI Assistant"
          onClick={handleLauncherClick}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          sx={{
            position: 'fixed',
            top: dragPos ? dragPos.y : position.y,
            left: dragPos ? dragPos.x : position.side === 'left' ? LAUNCHER_MARGIN : 'auto',
            right: dragPos ? 'auto' : position.side === 'right' ? LAUNCHER_MARGIN : 'auto',
            zIndex: theme => theme.zIndex.drawer + 2,
            gap: 1,
            px: 2.5,
            color: '#FFFFFF',
            background: theme => theme.custom.gradient.ctaDefault,
            boxShadow: 4,
            cursor: dragPos ? 'grabbing' : 'grab',
            // Prevent the browser from scrolling/selecting while dragging on touch/pointer devices.
            touchAction: 'none',
            transition: dragPos ? 'none' : 'box-shadow 0.2s ease',
            '&:hover': { background: theme => theme.custom.gradient.ctaHover },
            '&:focus-visible': {
              outline: theme => `3px solid ${theme.custom.interactive.highContrast}`,
              outlineOffset: 2
            }
          }}
        >
          <SmartToyOutlinedIcon sx={{ mr: 1 }} />
          AI Assistant
        </Fab>
      </Tooltip>

      {showFirstRun ? (
        <AssistantLauncherCallout
          side={position.side}
          y={position.y}
          title="Meet your AI Assistant"
          body="Read-only guidance on your projects, workflows, and what to do next — you always take the actions."
          ctaLabel="Show me"
          onOpen={() => {
            markFirstRunSeen();
            trackUi('first_run_opened');
            setOpen(true);
          }}
          onDismiss={() => {
            markFirstRunSeen();
            trackUi('first_run_dismissed');
          }}
        />
      ) : null}

      {showProactiveHint ? (
        <AssistantLauncherCallout
          side={position.side}
          y={position.y}
          title="Need a hand with this step?"
          body="Ask the assistant to explain this workflow step, its fields, or what's blocking you."
          ctaLabel="Ask"
          onOpen={() => {
            dismissProactiveStep();
            trackUi('proactive_hint_opened', 'step_help');
            setOpen(true);
          }}
          onDismiss={() => {
            dismissProactiveStep();
            trackUi('proactive_hint_dismissed', 'step_help');
          }}
        />
      ) : null}

      <ThemeProvider theme={ASSISTANT_THEME}>
        <Drawer
          anchor="right"
          open={open}
          onClose={handleCloseDrawer}
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
                <IconButton size="small" onClick={handleCloseDrawer} aria-label="Close assistant">
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
                companionMode={Boolean(companion?.runId)}
                feedbackPendingId={feedbackMutation.isPending ? (feedbackMutation.variables?.messageId ?? null) : null}
                onSend={handleSend}
                onRetry={handleRetry}
                onOpenCard={handleOpenCard}
                onPromptCard={handleSend}
                onFeedback={handleFeedback}
                onTrack={trackUi}
              />
            )}
          </Box>
        </Drawer>
      </ThemeProvider>
    </>
  );
};
