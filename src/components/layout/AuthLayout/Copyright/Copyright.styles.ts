import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';

export const CopyrightStyled = styled(Box)(({ theme }) => ({
  position: 'absolute',
  bottom: 0,
  left: 0,
  right: 0,
  padding: theme.spacing(2)
}));
