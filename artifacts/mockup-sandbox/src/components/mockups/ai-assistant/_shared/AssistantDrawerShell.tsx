import * as React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import CloseIcon from '@mui/icons-material/Close';
import AddCommentOutlinedIcon from '@mui/icons-material/AddCommentOutlined';
import HistoryIcon from '@mui/icons-material/History';

// Static reproduction of the AssistantWidget Drawer chrome (header + divider + content slot) so the
// real chat components can be previewed inside the exact panel surface they ship in. The drawer
// itself is portal/overlay-driven in the app; here we render its paper inline at the canonical width.
interface AssistantDrawerShellProps {
  children: React.ReactNode;
}

export const AssistantDrawerShell: React.FC<AssistantDrawerShellProps> = ({ children }) => {
  return (
    <Box
      sx={{
        width: '100%',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.paper',
        borderLeft: 1,
        borderColor: 'divider'
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
            <IconButton size="small" aria-label="New conversation">
              <AddCommentOutlinedIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Conversation history">
            <IconButton size="small" aria-label="Toggle conversation history">
              <HistoryIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Close">
            <IconButton size="small" aria-label="Close assistant">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>
      <Divider />
      <Box sx={{ flex: 1, minHeight: 0 }}>{children}</Box>
    </Box>
  );
};
