import { styled } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Toolbar from '@mui/material/Toolbar';
import AppBar from '@mui/material/AppBar';
import Menu from '@mui/material/Menu';

const SIDEBAR_WIDTH_OPEN = 30;
const SIDEBAR_WIDTH_CLOSED = 8;

export const HeaderMenuAvatar = styled(Avatar)(({ theme }) => ({
  width: 48,
  height: 48,
  marginRight: theme.spacing(1),
  background: 'linear-gradient(87deg, #C5AFF0 0%, #456CF3 100%)',
  fontSize: '16px',
  fontWeight: '600',
  color: '#FFFFFF'
}));

export const HeaderToolbar = styled(Toolbar)(({ theme }) => ({
  height: theme.spacing(8),
  minHeight: `${theme.spacing(8)} !important`,
  padding: `0 !important`,
  color: theme.palette.text.secondary
}));

interface HeaderProps {
  sidebarOpen?: boolean;
}

export const Header = styled(AppBar, {
  shouldForwardProp: prop => prop !== 'sidebarOpen'
})<HeaderProps>(({ theme, sidebarOpen }) => {
  const sidebarWidth = sidebarOpen ? theme.spacing(SIDEBAR_WIDTH_OPEN) : theme.spacing(SIDEBAR_WIDTH_CLOSED);

  return {
    left: sidebarWidth,
    width: `calc(100% - ${sidebarWidth})`,
    backgroundColor: theme.palette.background.paper,
    boxShadow: 'none',
    transition: theme.transitions.create(['left', 'width'], {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen
    })
  };
});

export const MenuStyled = styled(Menu)(({ theme }) => ({
  '& .MuiPaper-root': {
    minWidth: 180,
    backgroundColor: theme.palette.background.paper
  }
}));
