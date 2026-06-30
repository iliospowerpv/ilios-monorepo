import * as React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';

import { AssistantDrawerShell } from './_shared/AssistantDrawerShell';
import { AssistantChatPanel } from './_shared/AssistantChatPanel';
import type { AssistantSuggestedPrompt } from './_shared/assistant-types';
import theme from './_shared/appTheme';

// State 2 — open drawer, empty chat. Shows the read-only header strapline, the empty-state hint, and
// the page-aware suggested-prompt chips. The prompts are static UI examples — no business data fetch.
const PROMPTS: AssistantSuggestedPrompt[] = [
  { label: 'What needs my attention?', prompt: 'What needs my attention across my projects right now?' },
  { label: 'Start a project onboarding', prompt: 'How do I start onboarding a new project?' },
  { label: 'Which projects have data gaps?', prompt: 'Which of my projects have telemetry or baseline data gaps?' },
  { label: 'Explain the reconciliation ladder', prompt: 'Explain the due diligence reconciliation ladder.' }
];

export function DrawerSuggestedPrompts() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AssistantDrawerShell>
        <AssistantChatPanel
          messages={[]}
          isSending={false}
          error={null}
          suggestedPrompts={PROMPTS}
          suggestedContextLabel="Project Hub overview"
          onSend={() => {}}
          onRetry={() => {}}
          onOpenCard={() => {}}
          onFeedback={() => {}}
        />
      </AssistantDrawerShell>
    </ThemeProvider>
  );
}
