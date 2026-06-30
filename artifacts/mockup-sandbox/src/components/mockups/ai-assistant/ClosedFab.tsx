import * as React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Fab from '@mui/material/Fab';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';

import theme from './_shared/appTheme';

// State 1 — the closed launcher. This is the exact FAB chrome from AssistantWidget (secondary color,
// SmartToy icon, fixed bottom-right) over a faux app page so the launcher reads in context. The FAB
// only renders in the real app once the backend `native_assistant_enabled` flag is on.
const FauxCard: React.FC<{ w?: number | string; h?: number }> = ({ w = '100%', h = 88 }) => (
  <Box sx={{ width: w, height: h, borderRadius: 2, bgcolor: '#FFFFFF', border: '1px solid #E8E9EE' }} />
);

export function ClosedFab() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ position: 'relative', minHeight: '100vh', bgcolor: '#F4F5F7', p: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
          Project Hub
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Portfolio overview
        </Typography>
        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <FauxCard />
          <FauxCard />
          <FauxCard />
        </Stack>
        <FauxCard h={220} />

        <Tooltip title="AI Assistant" placement="left">
          <Fab
            color="secondary"
            aria-label="Open AI Assistant"
            sx={{ position: 'fixed', bottom: 24, right: 24 }}
          >
            <SmartToyOutlinedIcon />
          </Fab>
        </Tooltip>
      </Box>
    </ThemeProvider>
  );
}
