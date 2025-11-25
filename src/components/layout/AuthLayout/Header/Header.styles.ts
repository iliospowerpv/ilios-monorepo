import { styled } from '@mui/material/styles';
import AppBar from '@mui/material/AppBar';

export const HeaderStyled = styled(AppBar)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  boxShadow: 'none'
}));
