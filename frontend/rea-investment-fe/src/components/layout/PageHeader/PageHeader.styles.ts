import { styled } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Toolbar from '@mui/material/Toolbar';
import AppBar from '@mui/material/AppBar';
import Menu from '@mui/material/Menu';

export const HeaderMenuAvatar = styled(Avatar)(({ theme }) => ({
  width: 48,
  height: 48,
  marginRight: theme.spacing(1),
  backgroundColor: theme.color.blueGray,
  fontSize: '16px',
  fontWeight: '600'
}));

export const HeaderToolbar = styled(Toolbar)(({ theme }) => ({
  height: theme.spacing(8),
  minHeight: `${theme.spacing(8)} !important`,
  padding: `0 !important`,
  color: theme.palette.text.secondary
}));

export const Header = styled(AppBar)(({ theme }) => ({
  left: theme.spacing(8),
  width: `calc(100% - ${theme.spacing(8)})`,
  backgroundColor: theme.palette.background.paper,
  boxShadow: 'none'
}));

export const MenuStyled = styled(Menu)(({ theme }) => ({
  '& .MuiPaper-root': {
    minWidth: 180,
    backgroundColor: theme.palette.background.paper
  }
}));
