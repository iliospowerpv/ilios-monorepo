import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';

export const MainContainer = styled(Box)(({ theme }) => ({
  padding: `${theme.spacing(10)} ${theme.spacing(3)} 0`,
  marginLeft: theme.spacing(8),
  maxWidth: `calc(100% - ${theme.spacing(8)})`,
  flexGrow: 1,
  backgroundColor: '#ffffff',
  minHeight: '100vh'
}));
