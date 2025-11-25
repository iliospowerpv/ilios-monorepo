import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';

export const LogoContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  width: theme.spacing(8),
  height: theme.spacing(8)
}));
