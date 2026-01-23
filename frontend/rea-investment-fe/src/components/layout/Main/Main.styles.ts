import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';

interface MainContainerProps {
  sidebarOpen?: boolean;
}

export const MainContainer = styled(Box, {
  shouldForwardProp: prop => prop !== 'sidebarOpen'
})<MainContainerProps>(({ theme, sidebarOpen }) => ({
  padding: `${theme.spacing(10)} ${theme.spacing(3)} 0`,
  marginLeft: sidebarOpen ? theme.spacing(30) : theme.spacing(8),
  maxWidth: `calc(100% - ${sidebarOpen ? theme.spacing(30) : theme.spacing(8)})`,
  flexGrow: 1,
  backgroundColor: theme.palette.background.default,
  minHeight: '100vh',
  transition: theme.transitions.create(['margin-left', 'max-width'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.enteringScreen
  })
}));
