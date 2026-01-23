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

export const CardStyled = styled(Card)(({ theme }) => {
  const isLight = theme.palette.mode === 'light';
  return {
    backgroundColor: isLight ? '#FFFFFF' : '#1F1F1F',
    width: '420px',
    padding: '40px 26px',
    borderRadius: theme.shape.borderRadius,
    boxSizing: 'border-box',
    boxShadow: isLight ? '0 8px 32px rgba(0, 0, 0, 0.12)' : '0 8px 32px rgba(0, 0, 0, 0.4)'
  };
});

export const CardContentStyled = styled(CardContent)(() => ({
  padding: 0,
  '&:last-child': {
    padding: 0
  }
}));
