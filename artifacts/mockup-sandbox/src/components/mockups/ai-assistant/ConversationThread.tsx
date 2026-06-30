import * as React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import { AssistantDrawerShell } from './_shared/AssistantDrawerShell';
import { AssistantChatPanel, ChatUiMessage } from './_shared/AssistantChatPanel';
import theme from './_shared/appTheme';

// State 3 — a live conversation turn. User question (right, secondary bubble) + assistant reply
// (left, neutral bubble) with a collapsed Sources disclosure and the owner-scoped thumbs feedback
// shown in its active state. No action card here — that is exercised in ActionCardFocus.
const MESSAGES: ChatUiMessage[] = [
  {
    role: 'user',
    content: 'Which of my projects have telemetry data gaps right now?'
  },
  {
    role: 'assistant',
    id: 2,
    content:
      'Three projects currently have incomplete telemetry coverage over the last 7 days:\n\n' +
      '• Riverside Solar I — no inverter readings since Jun 24\n' +
      '• Helios II — weather station offline (POA missing)\n' +
      '• Crestline 3 — partial meter data (62% complete)\n\n' +
      'While a series is incomplete, expected-vs-actual energy stays as N/A rather than being shown ' +
      'as 0. Open each project’s Telemetry tab to review device eligibility and the latest sync.',
    sources: [
      { kind: 'faq', label: 'Telemetry completeness' },
      { kind: 'tool', label: 'list_site_health', detail: 'Read-only: per-project telemetry coverage' }
    ],
    feedback: 'up'
  }
];

export function ConversationThread() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AssistantDrawerShell>
        <AssistantChatPanel
          messages={MESSAGES}
          isSending={false}
          error={null}
          suggestedPrompts={[]}
          onSend={() => {}}
          onRetry={() => {}}
          onOpenCard={() => {}}
          onFeedback={() => {}}
        />
      </AssistantDrawerShell>
    </ThemeProvider>
  );
}
