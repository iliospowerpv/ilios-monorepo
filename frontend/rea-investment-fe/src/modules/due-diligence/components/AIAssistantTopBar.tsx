import React from 'react';

import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import IconButton from '@mui/material/IconButton';
import RefreshIcon from '@mui/icons-material/Refresh';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CloseIcon from '@mui/icons-material/Close';

interface AIAssistantAppBarProps {
  onCloseClick: () => void;
  onResetClick: () => void;
  onCollapseClick: () => void;
}

export const AIAssistantAppBar: React.FC<AIAssistantAppBarProps> = ({
  onCollapseClick,
  onCloseClick,
  onResetClick
}) => (
  <AppBar
    sx={{
      boxShadow: 'none',
      background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)',
      height: '64px',
      justifyContent: 'center'
    }}
    position="static"
    component="div"
  >
    <Toolbar sx={{ paddingX: '20px !important' }}>
      <Typography variant="h6">Illuminate Chatbot</Typography>
      <Box sx={{ flexGrow: 1, mr: '12px' }} />
      <Box display="flex" color="#FFFFFF" gap="4px">
        <Tooltip
          componentsProps={{
            tooltip: { sx: { bgcolor: '#121212' } },
            popper: {
              modifiers: [
                {
                  name: 'offset',
                  options: {
                    offset: [0, -10]
                  }
                }
              ]
            }
          }}
          title="Reset Conversation"
        >
          <IconButton color="inherit" data-testid="ai-chatbot_reset-conversation-btn" onClick={onResetClick}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
        <Tooltip
          componentsProps={{
            tooltip: { sx: { bgcolor: '#121212' } },
            popper: {
              modifiers: [
                {
                  name: 'offset',
                  options: {
                    offset: [0, -10]
                  }
                }
              ]
            }
          }}
          title="Collapse"
        >
          <IconButton color="inherit" data-testid="ai-chatbot_collapse-btn" onClick={onCollapseClick}>
            <ExpandMoreIcon />
          </IconButton>
        </Tooltip>
        <Tooltip
          componentsProps={{
            tooltip: { sx: { bgcolor: '#121212' } },
            popper: {
              modifiers: [
                {
                  name: 'offset',
                  options: {
                    offset: [0, -10]
                  }
                }
              ]
            }
          }}
          title="Close the chat"
        >
          <IconButton color="inherit" data-testid="ai-chatbot_close-conversation-btn" onClick={onCloseClick}>
            <CloseIcon />
          </IconButton>
        </Tooltip>
      </Box>
    </Toolbar>
  </AppBar>
);

export default AIAssistantAppBar;
