import { styled } from '@mui/material/styles';
import AppBar from '@mui/material/AppBar';

export const HeaderStyled = styled(AppBar)(({ theme }) => ({
  backgroundColor: theme.palette.mode === 'light' ? '#1A1C27' : '#201E2B',
  boxShadow: 'none'
}));
