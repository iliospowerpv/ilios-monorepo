import React from 'react';
import { useBlocker, useMatches } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { TransitionGroup } from 'react-transition-group';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import SvgIcon from '@mui/material/SvgIcon';
import Fab from '@mui/material/Fab';
import Modal from '@mui/material/Modal';
import IconButton from '@mui/material/IconButton';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import Zoom from '@mui/material/Zoom';
import TextField from '@mui/material/TextField';
import Avatar from '@mui/material/Avatar';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Fade from '@mui/material/Fade';

import { RouteHandle } from '../../../handles';
import { ApiClient } from '../../../api';
import AIAssistantAppBar from './AIAssistantTopBar';
import AIAssistantActionConfirmationDialog from './AIAssistantActionConfirmationDialog';

const ChatbotSvgIcon: React.FC = (props: { fontSize?: number | string | undefined }) => (
  <SvgIcon sx={{ fontSize: props.fontSize ?? 28 }}>
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M16.1875 3.0625C16.1875 3.95951 15.6476 4.73042 14.875 5.06798V7H19.25C23.116 7 26.25 10.134 26.25 14C26.25 16.6815 24.7422 19.0109 22.5282 20.1865L22.5312 20.1865L22.4157 20.2449L22.3927 20.2566L14 24.5V21H8.75C4.88401 21 1.75 17.866 1.75 14C1.75 10.134 4.88401 7 8.75 7H13.125V5.06798C12.3524 4.73042 11.8125 3.95951 11.8125 3.0625C11.8125 1.85438 12.7919 0.875 14 0.875C15.2081 0.875 16.1875 1.85438 16.1875 3.0625ZM13.125 8.75H8.75C5.85051 8.75 3.5 11.1005 3.5 14C3.5 16.8995 5.8505 19.25 8.75 19.25H19.25C22.1495 19.25 24.5 16.8995 24.5 14C24.5 11.1005 22.1495 8.75 19.25 8.75H14.875H13.125ZM8.75 10.5C6.817 10.5 5.25 12.067 5.25 14C5.25 15.933 6.817 17.5 8.75 17.5H19.25C21.183 17.5 22.75 15.933 22.75 14C22.75 12.067 21.183 10.5 19.25 10.5H8.75ZM10.0625 15.3125C10.7874 15.3125 11.375 14.7249 11.375 14C11.375 13.2751 10.7874 12.6875 10.0625 12.6875C9.33763 12.6875 8.75 13.2751 8.75 14C8.75 14.7249 9.33763 15.3125 10.0625 15.3125ZM19.25 14C19.25 14.7249 18.6624 15.3125 17.9375 15.3125C17.2126 15.3125 16.625 14.7249 16.625 14C16.625 13.2751 17.2126 12.6875 17.9375 12.6875C18.6624 12.6875 19.25 13.2751 19.25 14Z"
        fill="white"
      />
    </svg>
  </SvgIcon>
);
interface AIChatBotClusterProps {
  siteId: number;
}

interface ChatBotResponse {
  metadata: { status: string };
  response: string;
}

const ProcessingStatus = Object.freeze({
  AWAITING_DATA: 'Waiting for query',
  COMPLETE: 'Complete',
  IN_PROGRESS: 'In Progress',
  ERROR: 'Error'
});

interface BotResponse {
  messages: { text: string; timestamp: string; type?: 'basic' | 'error' }[];
  type: 'response';
  timestamp: string;
}

interface UserInput {
  text: string;
  type: 'input';
  timestamp: string;
}

type Message = BotResponse | UserInput;

const AIChatBotCluster: React.FC<AIChatBotClusterProps> = ({ siteId }) => {
  const [open, setOpen] = React.useState(false);
  const [sessionActive, setSessionActive] = React.useState(false);
  const [confirmationDialogMode, setConfirmationDialogMode] = React.useState<'reset-chat' | 'close-chat' | 'closed'>(
    'closed'
  );

  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    const currentLocationPathnamePartials = currentLocation.pathname.split('/');
    const sitesPartialIndex = currentLocationPathnamePartials.findIndex(val => val === 'sites');
    const siteLevelLocationPathBase = currentLocationPathnamePartials
      .slice(0, sitesPartialIndex)
      .join('/')
      .concat(`/sites/${siteId}`);
    const isNavigationPathAllowed = nextLocation.pathname.startsWith(siteLevelLocationPathBase);
    return sessionActive && !isNavigationPathAllowed;
  });

  React.useEffect(() => {
    if (open && !sessionActive) setSessionActive(true);
  }, [open, sessionActive]);

  const containerRef = React.useRef<HTMLDivElement | null>(null);

  const queryClient = useQueryClient();

  const {
    data: sessionData,
    isFetching: isFetchingSessionData,
    error: errorRetrievingSessionData
  } = useQuery({
    queryFn: () => ApiClient.dueDiligence.getChatBotSession({ siteId }),
    queryKey: ['chatbot-session', { siteId }],
    staleTime: 8 * 60 * 60 * 1000,
    enabled: sessionActive
  });

  const handleExpandChat = () => setOpen(true);
  const handleCollapseChat = () => setOpen(false);
  const handleOpenResetConfirmation = () => setConfirmationDialogMode('reset-chat');
  const handleCloseConfirmationDialog = () => setConfirmationDialogMode('closed');
  const handleOpenChatCloseConfirmation = () => setConfirmationDialogMode('close-chat');

  const [messages, setMessages] = React.useState<Message[]>([]);

  React.useEffect(() => {
    setTimeout(() => {
      const element = containerRef.current;
      if (element) {
        element.scrollTop = element.scrollHeight;
      }
    }, 200);
  }, [messages]);

  React.useEffect(() => {
    queryClient.removeQueries({ queryKey: ['chatbot-session'] });

    return () => queryClient.removeQueries({ queryKey: ['chatbot-session'] });
  }, [queryClient]);

  const [processingStatusMessage, setProcessingStatusMessage] = React.useState<string | null>(null);
  const [processingStatus, setProcessingStatus] = React.useState<
    'initial' | 'awaiting' | 'error' | 'in-progress' | 'complete'
  >('initial');
  const [connectionStatusMessage, setConnectionStatusMessage] = React.useState<string | null>(null);

  const populateBotResponse = React.useCallback((response: string, isError?: boolean) => {
    setMessages(messages => {
      const [last] = messages.slice(-1);
      if (last?.type === 'response') {
        return [
          ...messages.slice(0, -1),
          {
            ...last,
            messages: [
              ...last.messages,
              {
                text: response,
                timestamp: `${+new Date()}`,
                type: isError ? 'error' : 'basic'
              }
            ]
          }
        ];
      }

      return [
        ...messages,
        {
          type: 'response',
          messages: [{ text: response, timestamp: `${+new Date()}`, type: isError ? 'error' : 'basic' }],
          timestamp: `${+new Date()}`
        }
      ];
    });
  }, []);

  const processReceivedMessage = React.useCallback(
    (message: MessageEvent<string>) => {
      const { metadata, response } = JSON.parse(message.data) as ChatBotResponse;

      switch (metadata.status) {
        case ProcessingStatus.AWAITING_DATA:
          setProcessingStatus('awaiting');
          setProcessingStatusMessage(null);
          break;
        case ProcessingStatus.IN_PROGRESS:
          setProcessingStatus('in-progress');
          setProcessingStatusMessage(response);
          break;
        case ProcessingStatus.ERROR:
          setProcessingStatus('error');
          setProcessingStatusMessage(null);
          populateBotResponse(response, true);
          break;
        case ProcessingStatus.COMPLETE:
          setProcessingStatus('complete');
          setProcessingStatusMessage(null);
          populateBotResponse(response);
          break;
      }
    },
    [populateBotResponse]
  );

  const [message, setMessage] = React.useState('');
  const shouldReconnect = React.useCallback(() => true, []);

  const { sendMessage, readyState } = useWebSocket(
    sessionData && sessionActive
      ? `${process.env.REACT_APP_CHATBOT_ENDPOINT || 'http://localhost:8080'}/chatbot/chat?token=${sessionData.token.access_token}`
      : null,
    {
      onMessage: processReceivedMessage,
      shouldReconnect,
      retryOnError: true
    }
  );

  const resendLastIfNoResponse = React.useCallback(() => {
    setMessages(messages => {
      const [secondToLast, last] = messages.slice(-2);

      if (last?.type === 'input') {
        sendMessage(last.text);
        setProcessingStatus('in-progress');
        setProcessingStatusMessage('Processing...');
        return [...messages.slice(0, -1), { ...last }];
      }
      if (secondToLast?.type === 'input' && last?.type === 'response' && last?.messages.length === 0) {
        sendMessage(secondToLast.text);
        setProcessingStatus('in-progress');
        setProcessingStatusMessage('Processing...');
      }

      return messages;
    });
  }, [sendMessage]);

  React.useEffect(() => {
    switch (readyState) {
      case ReadyState.UNINSTANTIATED:
      case ReadyState.CONNECTING:
        setConnectionStatusMessage('Establishing connection with chatbot');
        break;
      case ReadyState.OPEN:
        setConnectionStatusMessage('Connection with chatbot has been established');
        setProcessingStatus('initial');
        setProcessingStatusMessage(null);
        resendLastIfNoResponse();
        break;
      case ReadyState.CLOSING:
        setConnectionStatusMessage('Closing connection with chatbot');
        break;
      case ReadyState.CLOSED:
        setConnectionStatusMessage('Connection with chatbot has been closed');
        setProcessingStatus('initial');
        setProcessingStatusMessage(null);
        break;
    }
  }, [readyState, resendLastIfNoResponse]);

  const handleResetConfirm = () => {
    setConfirmationDialogMode('closed');
    setMessages([]);
    queryClient.removeQueries({ queryKey: ['chatbot-session'] });
  };
  const handleCloseChatConfirm = () => {
    setConfirmationDialogMode('closed');
    setOpen(false);
    setSessionActive(false);
    setMessages([]);
    queryClient.removeQueries({ queryKey: ['chatbot-session'] });
  };

  React.useEffect(() => {
    if (processingStatus === 'in-progress') {
      setTimeout(() => {
        setMessages(messages => {
          const [last] = messages.slice(-1);

          if (last?.type === 'input') {
            return [
              ...messages,
              {
                type: 'response',
                messages: [],
                timestamp: `${+new Date()}`
              }
            ];
          }
          return messages;
        });
      }, 100);
    }
  }, [processingStatus, messages]);

  const populateUserInput = (input: string) => {
    setMessages(messages => {
      const [last] = messages.slice(-1);
      if (last?.type === 'response' && !last.messages.length) {
        return [...messages.slice(0, -1), { type: 'input', text: input, timestamp: `${+new Date()}` }, last];
      }

      return [...messages, { type: 'input', text: input, timestamp: `${+new Date()}` }];
    });
  };

  const onMessageSubmit = () => {
    if (!message) return;
    sendMessage(message);
    populateUserInput(message);
    processingStatus !== 'in-progress' && setProcessingStatus('in-progress');
    !processingStatusMessage && setProcessingStatusMessage('Processing...');
    setMessage('');
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setMessage(e.target.value);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      onMessageSubmit();
      e.preventDefault();
      e.stopPropagation();
    }
  };

  const confirmationModalMessages: Readonly<{
    [key in 'navigation-blocked' | 'reset-chat' | 'close-chat' | 'closed']: { title: string; text: string } | null;
  }> = Object.freeze({
    ['reset-chat']: {
      title: 'Reset conversation?',
      text: 'This will clear all previous messages and start a new chat.'
    },
    ['close-chat']: {
      title: 'Close this chat?',
      text: 'Do you want to close this chat? This will permanently delete your conversation history with the bot.'
    },
    ['closed']: null,
    ['navigation-blocked']: {
      title: 'Leave this page?',
      text: 'The chatbot session is open, do you want to close the chat and leave this page? This will permanently delete your conversation history with the bot.'
    }
  });

  return (
    <>
      <Zoom
        in={!open}
        style={{
          transitionDelay: `500ms`,
          transitionDuration: `${open ? 1000 : 300}ms`
        }}
      >
        <Fab
          color="primary"
          size="medium"
          sx={{
            position: 'fixed',
            bottom: 30,
            right: 30,
            boxShadow: 'none',
            background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)',
            zIndex: t => t.zIndex.modal + 10
          }}
          data-testid="ai-chatbot_open-btn"
          onClick={handleExpandChat}
        >
          <ChatbotSvgIcon />
        </Fab>
      </Zoom>
      <Modal
        disableEscapeKeyDown
        disableScrollLock
        disableEnforceFocus
        disableAutoFocus
        disableRestoreFocus
        hideBackdrop
        keepMounted
        sx={{
          top: 'auto',
          left: 'auto',
          bottom: 30,
          right: 30,
          zIndex: t => t.zIndex.modal + 100
        }}
        open={open}
      >
        <Zoom in={open} style={{ transformOrigin: 'bottom right' }}>
          <Box
            sx={{
              flex: '1 1 0%',
              maxWidth: '800px',
              minWidth: '320px',
              width: '25vw',
              height: '60vh',
              minHeight: '120px',
              maxHeight: '1200px',
              backgroundColor: '#FFFFFF',
              outline: 'none',
              boxShadow:
                'rgba(0, 0, 0, 0.08) 0px 5px 22px 4px, rgba(0, 0, 0, 0.1) 0px 12px 17px 2px, rgba(0, 0, 0, 0.16) 0px 7px 8px -4px'
            }}
          >
            <Box
              sx={{
                position: 'relative',
                overflow: 'hidden',
                height: '100%',
                width: '100%',
                flexDirection: 'column',
                display: 'flex'
              }}
            >
              <Box sx={{ alignItems: 'center', position: 'sticky', top: 0, zIndex: 10, width: '100%' }}>
                <AIAssistantAppBar
                  onCloseClick={handleOpenChatCloseConfirmation}
                  onResetClick={handleOpenResetConfirmation}
                  onCollapseClick={handleCollapseChat}
                />
              </Box>
              <Box
                sx={{
                  height: 'calc(100% - 64px)',
                  position: 'relative',
                  width: '100%'
                }}
              >
                {(isFetchingSessionData || errorRetrievingSessionData || readyState !== ReadyState.OPEN) && (
                  <Box
                    sx={{
                      height: '100%',
                      width: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '15%',
                      gap: '12px',
                      position: 'absolute',
                      background: '#FFFFFF',
                      zIndex: 10000
                    }}
                  >
                    <Typography variant="h6" textAlign="center">
                      {(isFetchingSessionData && 'Initializing a new session') ||
                        (errorRetrievingSessionData && 'An error occured when initializing a new session') ||
                        connectionStatusMessage}
                    </Typography>
                    {(isFetchingSessionData || readyState !== ReadyState.OPEN) && <CircularProgress size="30px" />}
                  </Box>
                )}
                <Box
                  sx={{
                    height: '100%',
                    width: '100%',
                    overflowX: 'hidden',
                    overflowY: 'scroll',
                    display: 'flex',
                    ['-ms-overflow-style']: 'none' /* Internet Explorer 10+ */,
                    ['scrollbar-width']: 'none' /* Firefox */,
                    ['&::-webkit-scrollbar']: {
                      display: 'none' /* Safari and Chrome */
                    }
                  }}
                  component="div"
                  ref={containerRef}
                >
                  <Box
                    sx={{
                      flexDirection: 'column',
                      flex: '1 1 0%',
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      position: 'relative'
                    }}
                  >
                    <TransitionGroup
                      style={{
                        flex: '1 1 0%',
                        flexDirection: 'column',
                        display: 'flex',
                        width: '100%',
                        padding: '20px',
                        gap: '20px'
                      }}
                    >
                      <Zoom>
                        <Box flexGrow={1} marginBottom={messages.length ? '-20px' : 0} />
                      </Zoom>
                      {messages.map((messageBlock, index, arr) =>
                        messageBlock.type === 'response' ? (
                          <Zoom key={messageBlock.timestamp}>
                            <Box display="flex" alignItems="flex-end">
                              <Avatar
                                sx={{
                                  height: '44px',
                                  width: '44px',
                                  background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)',
                                  mr: '10px'
                                }}
                              >
                                <ChatbotSvgIcon />
                              </Avatar>
                              <Box display="flex" gap="10px" flexDirection="column">
                                <TransitionGroup
                                  style={{
                                    display: 'flex',
                                    gap: '10px',
                                    flexDirection: 'column',
                                    alignItems: 'flex-start'
                                  }}
                                >
                                  {messageBlock.messages.map(message => (
                                    <Zoom key={message.timestamp}>
                                      {message.type === 'error' ? (
                                        <Alert
                                          key={message.timestamp}
                                          severity="error"
                                          sx={{
                                            py: '4px',
                                            px: '12px',
                                            bgcolor: '#F9DEDD',
                                            color: '#000000',
                                            ['&  .MuiAlert-icon']: {
                                              color: 'inherit'
                                            },
                                            ['& .MuiAlert-message']: {
                                              overflowWrap: 'anywhere',
                                              whiteSpace: 'pre-wrap'
                                            }
                                          }}
                                        >
                                          {message.text}
                                        </Alert>
                                      ) : (
                                        <Typography
                                          variant="body2"
                                          px="16px"
                                          py="12px"
                                          bgcolor="rgba(0, 0, 0, 0.04)"
                                          sx={{ overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }}
                                          key={message.timestamp}
                                        >
                                          {message.text}
                                        </Typography>
                                      )}
                                    </Zoom>
                                  ))}
                                </TransitionGroup>
                                {processingStatusMessage &&
                                  processingStatus === 'in-progress' &&
                                  index === arr.length - 1 && (
                                    <Typography
                                      variant="body2"
                                      px="16px"
                                      py="12px"
                                      fontStyle="italic"
                                      color="#667085"
                                      sx={{ overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }}
                                    >
                                      {processingStatusMessage}
                                    </Typography>
                                  )}
                              </Box>
                            </Box>
                          </Zoom>
                        ) : (
                          <Zoom key={messageBlock.timestamp}>
                            <Box display="flex" justifyContent="flex-end">
                              <Typography
                                variant="body2"
                                ml="54px"
                                px="16px"
                                py="12px"
                                bgcolor="#121212"
                                color="#FFFFFF"
                                sx={{ overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }}
                              >
                                {messageBlock.text}
                              </Typography>
                            </Box>
                          </Zoom>
                        )
                      )}
                    </TransitionGroup>
                    <Box sx={{ position: 'sticky', bottom: '0', width: '100%', zIndex: '100', background: '#fff' }}>
                      <Fade
                        in={
                          readyState !== ReadyState.OPEN ||
                          !['awaiting', 'error', 'complete'].includes(processingStatus)
                        }
                      >
                        <Box
                          sx={{
                            background: '#ffffff',
                            position: 'absolute',
                            width: '100%',
                            height: '100%',
                            maxHeight: '100%',
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                            flexDirection: 'column',
                            zIndex: 1000,
                            borderTop: '1px solid #E0E0E0'
                          }}
                        >
                          <svg width={0} height={0}>
                            <defs>
                              <linearGradient id="chatbot_gradient" x1="100%" y1="27%" x2="0%" y2="73%">
                                <stop offset="7.17%" stopColor="rgb(69,108,243)" />
                                <stop offset="89.9%" stopColor="rgb(141,75,233)" />
                              </linearGradient>
                            </defs>
                          </svg>
                          <CircularProgress
                            size="25px"
                            sx={{
                              'svg circle': { stroke: 'url(#chatbot_gradient)' }
                            }}
                          />
                        </Box>
                      </Fade>
                      <Box
                        sx={{
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          borderTop: '1px solid #E0E0E0',
                          flexShrink: 0
                        }}
                      >
                        <TextField
                          size="small"
                          multiline
                          minRows={1}
                          maxRows={5}
                          variant="outlined"
                          placeholder="Ask a question..."
                          sx={{ flexGrow: 1, my: 'auto', '& fieldset': { border: 'none' } }}
                          value={message}
                          onChange={handleInputChange}
                          onKeyDown={handleKeyDown}
                          disabled={
                            readyState !== ReadyState.OPEN ||
                            !['awaiting', 'error', 'complete'].includes(processingStatus)
                          }
                          InputProps={{
                            sx: {
                              padding: '16px 8px 16px 20px',
                              border: 'none'
                            }
                          }}
                        />
                        <IconButton
                          sx={{
                            color: 'rgba(0, 0, 0, 0.26)',
                            mx: '6px',
                            ['&:not(.Mui-disabled)  svg']: { fill: 'url(#chatbot_gradient)' }
                          }}
                          disabled={
                            !message ||
                            readyState !== ReadyState.OPEN ||
                            !['awaiting', 'error', 'complete'].includes(processingStatus)
                          }
                          onClick={onMessageSubmit}
                        >
                          <svg width={0} height={0}>
                            <defs>
                              <linearGradient id="chatbot_gradient" x1="100%" y1="27%" x2="0%" y2="73%">
                                <stop offset="7.17%" stopColor="rgb(69,108,243)" />
                                <stop offset="89.9%" stopColor="rgb(141,75,233)" />
                              </linearGradient>
                            </defs>
                          </svg>
                          <SendRoundedIcon />
                        </IconButton>
                      </Box>
                    </Box>
                  </Box>
                </Box>
              </Box>
            </Box>
          </Box>
        </Zoom>
      </Modal>
      <AIAssistantActionConfirmationDialog
        open={confirmationDialogMode !== 'closed' || blocker.state === 'blocked'}
        onClose={blocker.state === 'blocked' ? () => blocker.reset() : handleCloseConfirmationDialog}
        title={
          blocker.state === 'blocked'
            ? confirmationModalMessages['navigation-blocked']?.title
            : confirmationModalMessages[confirmationDialogMode]?.title
        }
        text={
          blocker.state === 'blocked'
            ? confirmationModalMessages['navigation-blocked']?.text
            : confirmationModalMessages[confirmationDialogMode]?.text
        }
        onConfirm={
          blocker.state === 'blocked'
            ? () => blocker.proceed()
            : confirmationDialogMode === 'reset-chat'
              ? handleResetConfirm
              : handleCloseChatConfirm
        }
      />
    </>
  );
};

export const AIAssistant: React.FC = () => {
  const matches = useMatches();
  const routeMatch = matches.find(({ handle, data }) => handle && data);

  if (!routeMatch) return null;

  const [data, featuresMap] =
    routeMatch.handle instanceof RouteHandle ? [routeMatch.data, routeMatch.handle.getFeaturesMap()] : [null, null];

  const config = featuresMap?.['ai-assistant']?.generateConfig(data);

  if (!config) return null;

  const { siteId, enabled } = config;

  if (!enabled) return null;

  return <AIChatBotClusterWrapper siteId={siteId} />;
};

const AIChatBotClusterWrapper: React.FC<AIChatBotClusterProps> = ({ siteId }) => {
  return React.useMemo(() => <AIChatBotCluster siteId={siteId} />, [siteId]);
};

export default AIAssistant;
