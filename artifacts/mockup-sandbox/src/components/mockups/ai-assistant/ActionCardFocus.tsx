import * as React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import { AssistantDrawerShell } from './_shared/AssistantDrawerShell';
import { AssistantChatPanel, ChatUiMessage } from './_shared/AssistantChatPanel';
import theme from './_shared/appTheme';

// State 4 — a propose-only action card. The assistant surfaces a validated deep link into an EXISTING
// workflow; it never starts it. The "Open" button navigates the user, and the caption makes the
// read-only boundary explicit ("You take this step — the assistant can’t.").
const MESSAGES: ChatUiMessage[] = [
  {
    role: 'user',
    content: 'How do I start onboarding the Helios II project?'
  },
  {
    role: 'assistant',
    id: 4,
    content:
      'Helios II looks ready to onboard — site details are complete and there’s no onboarding run in ' +
      'progress. The next governed step is the Project Onboarding workflow, where you’ll confirm the ' +
      'configuration and assign the operations team. I can take you straight there; you complete the ' +
      'handshake yourself.',
    action_cards: [
      {
        kind: 'workflow',
        title: 'Start Project Onboarding — Helios II',
        reason: 'Site details are complete and no onboarding run is currently in progress.',
        route: '/project-hub/companies/12/projects/48/onboarding',
        requires_user_action: true
      }
    ],
    sources: [
      { kind: 'faq', label: 'Onboarding workflow' },
      { kind: 'tool', label: 'get_workflow_advice', detail: 'Read-only: next-step advice for this project' }
    ],
    feedback: null
  }
];

export function ActionCardFocus() {
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
