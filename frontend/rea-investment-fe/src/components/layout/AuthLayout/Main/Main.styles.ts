import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';

export const MainContainer = styled(Box)(() => ({
  minHeight: '100vh',
  width: '100%',
  backgroundImage: 'url(/background.png)',
  backgroundSize: 'cover',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center'
}));

export const Offset = styled('div')(({ theme }) => ({
  height: theme.spacing(8)
}));

export const CardStyled = styled(Card)(({ theme }) => ({
  backgroundColor: theme.palette.common.white,
  width: '420px',
  padding: '40px 26px',
  borderRadius: theme.spacing(2),
  boxSizing: 'border-box'
}));

export const CardContentStyled = styled(CardContent)(() => ({
  padding: 0,
  '&:last-child': {
    padding: 0
  }
}));
