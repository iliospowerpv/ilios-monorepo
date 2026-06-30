import * as React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { AssistantDrawerShell } from './_shared/AssistantDrawerShell';
import { SourcesDisclosure } from './_shared/SourcesDisclosure';
import type { AssistantSource } from './_shared/assistant-types';
import theme from './_shared/appTheme';

// State 5 — the Sources disclosure expanded. Transparency-only: a LABELS-ONLY list of the curated
// FAQ entries (book icon) and read-only data tools (storage icon) that backed a reply. It never
// renders raw tool payloads. Rendered open here via the sandbox-only `defaultOpen` prop.
const SOURCES: AssistantSource[] = [
  { kind: 'faq', label: 'Reconciliation ladder', detail: 'Curated FAQ: how DD facts roll up to baselines' },
  { kind: 'tool', label: 'get_reconciliation_status', detail: 'Read-only: current ladder state for the project' },
  { kind: 'faq', label: 'Expected baselines', detail: 'Curated FAQ: weather-adjusted expected energy' },
  { kind: 'tool', label: 'list_project_facts', detail: 'Read-only: verified facts for the project' }
];

export function SourcesExpanded() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AssistantDrawerShell>
        <Box sx={{ px: 2, py: 2 }}>
          <Stack spacing={1} alignItems="flex-start">
            <Paper
              elevation={0}
              sx={{ px: 1.5, py: 1, maxWidth: '85%', borderRadius: 2, bgcolor: 'action.hover', color: 'text.primary' }}
            >
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                The reconciliation ladder rolls verified due-diligence facts up into the project’s
                weather-adjusted baseline. Here is what backed this answer:
              </Typography>
            </Paper>
            <SourcesDisclosure sources={SOURCES} defaultOpen />
          </Stack>
        </Box>
      </AssistantDrawerShell>
    </ThemeProvider>
  );
}
