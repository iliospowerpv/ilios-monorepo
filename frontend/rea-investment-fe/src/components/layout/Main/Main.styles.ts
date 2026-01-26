import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';

const SIDEBAR_WIDTH_OPEN = 30;
const SIDEBAR_WIDTH_CLOSED = 8;

interface MainContainerProps {
  sidebarOpen?: boolean;
}

export const MainContainer = styled(Box, {
  shouldForwardProp: prop => prop !== 'sidebarOpen'
})<MainContainerProps>(({ theme, sidebarOpen }) => {
  const sidebarWidth = sidebarOpen ? theme.spacing(SIDEBAR_WIDTH_OPEN) : theme.spacing(SIDEBAR_WIDTH_CLOSED);

  return {
    padding: `${theme.spacing(10)} ${theme.spacing(3)} 0`,
    marginLeft: sidebarWidth,
    width: `calc(100% - ${sidebarWidth})`,
    maxWidth: `calc(100% - ${sidebarWidth})`,
    flexGrow: 1,
    backgroundColor: theme.palette.background.default,
    minHeight: '100vh',
    boxSizing: 'border-box',
    overflow: 'hidden',
    transition: theme.transitions.create(['margin-left', 'width', 'max-width'], {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen
    })
  };
});
