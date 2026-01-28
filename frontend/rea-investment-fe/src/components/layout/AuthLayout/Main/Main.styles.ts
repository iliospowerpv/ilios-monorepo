import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';

export const MainContainer = styled(Box)(() => ({
  minHeight: '100vh',
  width: '100%',
  background: `
    radial-gradient(ellipse at 50% 100%, rgba(138, 43, 226, 0.6) 0%, transparent 50%),
    radial-gradient(ellipse at 100% 0%, rgba(70, 100, 200, 0.8) 0%, transparent 40%),
    radial-gradient(ellipse at 0% 50%, rgba(80, 60, 160, 0.5) 0%, transparent 40%),
    linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #1a1a2e 100%)
  `,
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
