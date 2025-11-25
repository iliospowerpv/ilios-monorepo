import { styled } from '@mui/material/styles';
import MuiDrawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Toolbar from '@mui/material/Toolbar';
import Divider from '@mui/material/Divider';

export const SidebarDrawer = styled(MuiDrawer, { shouldForwardProp: prop => prop !== 'open' })(({ theme, open }) => ({
  '& .MuiDrawer-paper': {
    position: 'relative',
    whiteSpace: 'nowrap',
    backgroundColor: theme.color.black,
    width: theme.spacing(30),
    borderRight: 'none',
    transition: theme.transitions.create('width', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen
    }),
    boxSizing: 'border-box',
    ...(!open && {
      overflowX: 'hidden',
      transition: theme.transitions.create('width', {
        easing: theme.transitions.easing.sharp,
        duration: theme.transitions.duration.leavingScreen
      }),
      width: theme.spacing(8)
    })
  }
}));

export const SidebarContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  position: 'fixed',
  zIndex: theme.zIndex.drawer,
  height: '100vh',
  color: theme.color.black
}));

export const SidebarHead = styled(Toolbar)(() => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-start',
  padding: `0 !important`,
  color: '#ffffff'
}));

export const SidebarToggleButtonContainer = styled(Box)(({ theme }) => ({
  position: 'absolute',
  right: 0,
  top: 0,
  zIndex: theme.zIndex.drawer,
  backgroundColor: '#ffffff',
  borderRadius: '50%',
  transform: `translate(50%, calc(${theme.spacing(8)} - 50%))`
}));

export const SidebarDivider = styled(Divider)(() => ({
  backgroundColor: '#e0e0e0'
}));
