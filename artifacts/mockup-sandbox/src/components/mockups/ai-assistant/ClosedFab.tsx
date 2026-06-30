import * as React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Fab from '@mui/material/Fab';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';

import { getTheme } from './_shared/appTheme';

// State 1 — the restyled closed launcher. This mirrors the AssistantWidget FAB after Task #86:
// an extended FAB using the Ilios purple CTA gradient, the SmartToy icon and an "AI Assistant" label,
// draggable and snapped to a screen edge. The FAB only renders in the real app once the backend
// `native_assistant_enabled` flag is on, so this isolated mockup stands in for an authenticated view.
const FauxCard: React.FC<{ w?: number | string; h?: number; dark?: boolean }> = ({ w = '100%', h = 88, dark }) => (
  <Box
    sx={{
      width: w,
      height: h,
      borderRadius: 2,
      bgcolor: dark ? '#1F1F1F' : '#FFFFFF',
      border: dark ? '1px solid #2C2C2C' : '1px solid #E8E9EE'
    }}
  />
);

type LauncherSide = 'left' | 'right';

const Launcher: React.FC<{ side?: LauncherSide; top?: number }> = ({ side = 'right', top }) => (
  <Tooltip title="AI Assistant" placement="left">
    <Fab
      variant="extended"
      aria-label="Open AI Assistant"
      sx={{
        position: 'fixed',
        top: top ?? 'auto',
        bottom: top == null ? 24 : 'auto',
        left: side === 'left' ? 24 : 'auto',
        right: side === 'right' ? 24 : 'auto',
        gap: 1,
        px: 2.5,
        color: '#FFFFFF',
        background: theme => theme.custom.gradient.ctaDefault,
        boxShadow: 4,
        '&:hover': { background: theme => theme.custom.gradient.ctaHover }
      }}
    >
      <SmartToyOutlinedIcon sx={{ mr: 1 }} />
      AI Assistant
    </Fab>
  </Tooltip>
);

const Page: React.FC<{ mode: 'light' | 'dark'; side?: LauncherSide; top?: number; caption: string }> = ({
  mode,
  side,
  top,
  caption
}) => {
  const isDark = mode === 'dark';
  return (
    <ThemeProvider theme={getTheme(mode)}>
      <CssBaseline />
      <Box sx={{ position: 'relative', minHeight: '100vh', bgcolor: isDark ? '#1A1C27' : '#F4F5F7', p: 4 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>
          Project Hub
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Portfolio overview
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 3, display: 'block' }}>
          {caption}
        </Typography>
        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <FauxCard dark={isDark} />
          <FauxCard dark={isDark} />
          <FauxCard dark={isDark} />
        </Stack>
        <FauxCard h={220} dark={isDark} />
        <Launcher side={side} top={top} />
      </Box>
    </ThemeProvider>
  );
};

export function ClosedFab() {
  return <Page mode="light" caption="Light mode — anchored bottom-right (default)" />;
}

export function ClosedFabDark() {
  return <Page mode="dark" caption="Dark mode — anchored bottom-right (default)" />;
}

export function ClosedFabRepositioned() {
  return <Page mode="light" side="left" top={120} caption="Repositioned — dragged & snapped to the left edge" />;
}
