import * as React from 'react';
import Paper from '@mui/material/Paper';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Typography from '@mui/material/Typography';
import CloseIcon from '@mui/icons-material/Close';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';

import { LAUNCHER_MARGIN, type LauncherSide } from './useAssistantLauncherPosition';

interface AssistantLauncherCalloutProps {
  // Which screen edge the launcher rests against, and its vertical offset — the callout anchors next
  // to it.
  side: LauncherSide;
  y: number;
  title: string;
  body: string;
  ctaLabel: string;
  // Opens the existing read-only assistant drawer. Navigational only — never an action.
  onOpen: () => void;
  onDismiss: () => void;
}

// Approx. launcher (extended FAB) height; used to offset the callout when it must sit below it.
const LAUNCHER_HEIGHT = 56;
// Below this vertical offset there is not enough room above the launcher, so drop the callout below.
const ABOVE_THRESHOLD = 180;

// A small, non-modal, dismissible coachmark anchored beside the draggable assistant launcher. It is
// purely navigational: its CTA opens the existing read-only assistant drawer — it NEVER executes,
// previews, or starts anything. Reused for one-time first-run guidance and the per-step workflow
// nudge.
export const AssistantLauncherCallout: React.FC<AssistantLauncherCalloutProps> = ({
  side,
  y,
  title,
  body,
  ctaLabel,
  onOpen,
  onDismiss
}) => {
  const placeAbove = y > ABOVE_THRESHOLD;
  return (
    <Paper
      elevation={8}
      role="status"
      sx={theme => ({
        position: 'fixed',
        zIndex: theme.zIndex.drawer + 1,
        width: 264,
        maxWidth: 'calc(100vw - 32px)',
        p: 1.5,
        borderRadius: 2,
        border: `1px solid ${theme.palette.divider}`,
        ...(side === 'left' ? { left: LAUNCHER_MARGIN } : { right: LAUNCHER_MARGIN }),
        ...(placeAbove ? { top: y, transform: 'translateY(calc(-100% - 12px))' } : { top: y + LAUNCHER_HEIGHT + 12 })
      })}
    >
      <Stack direction="row" spacing={1} alignItems="flex-start">
        <SmartToyOutlinedIcon color="secondary" fontSize="small" sx={{ mt: 0.25 }} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
            {title}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
            {body}
          </Typography>
        </Box>
        <IconButton size="small" onClick={onDismiss} aria-label="Dismiss" sx={{ mt: -0.5, mr: -0.5 }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Stack>
      <Stack direction="row" justifyContent="flex-end" spacing={1} sx={{ mt: 1 }}>
        <Button size="small" color="inherit" onClick={onDismiss}>
          Not now
        </Button>
        <Button size="small" variant="contained" color="secondary" onClick={onOpen}>
          {ctaLabel}
        </Button>
      </Stack>
    </Paper>
  );
};
