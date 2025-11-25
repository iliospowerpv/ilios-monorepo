import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { styled } from '@mui/system';

export const BoardContainer = styled(Box)(({ theme }) => ({
  background: theme.palette.common.white,
  display: 'flex',
  height: '100%',
  justifyContent: 'space-between',
  overflowX: 'auto',
  overflowY: 'auto'
}));

export const ColumnHeader = styled(Box)(({ theme }) => ({
  background: theme.palette.common.black,
  height: '52px',
  padding: '16px',
  display: 'flex',
  alignItems: 'center'
}));

export const Column = styled(Box)(() => ({
  flex: 1,
  margin: '8px',
  '&:first-of-type': {
    marginLeft: 0
  },
  '&:last-of-type': {
    marginRight: 0
  }
}));

export const TaskList = styled(Box)(({ theme }) => ({
  background: theme.palette.background.default,
  minHeight: '100px',
  height: 'calc(100% - 56px)',
  display: 'flex',
  flexDirection: 'column',
  minWidth: '270px',
  padding: '0 16px 16px'
}));

export const Title = styled(Typography)(({ theme }) => ({
  color: theme.palette.common.white,
  fontSize: '14px',
  fontWeight: 500,
  lineHeight: '20px'
}));

export const TaskContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  border: '1px solid #0000001F',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'flex-start',
  padding: '16px',
  minHeight: '116px',
  width: '100%',
  background: theme.palette.common.white,
  marginTop: '16px'
}));

export const Header = styled(Box)(() => ({
  height: '24px',
  width: '100%',
  marginBottom: '8px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between'
}));

export const Footer = styled(Box)(() => ({
  height: '24px',
  width: '100%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'end'
}));
