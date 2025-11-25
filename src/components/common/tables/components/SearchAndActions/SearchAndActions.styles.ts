import { styled } from '@mui/system';
import { TextField } from '@mui/material';

export const SearchField = styled(TextField)(() => ({
  height: '40px',
  width: '320px',
  '.MuiOutlinedInput-root': {
    borderRadius: 0
  },
  '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
    '&::before, &:hover::before, &.Mui-focused::after': {
      borderBottomColor: 'transparent',
      transform: 'scaleX(0)'
    }
  }
}));

export const SearchAndActionsContainer = styled('div')(() => ({
  marginBottom: '16px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '16px'
}));

export const SearchBarItem = styled('div')(() => ({
  display: 'flex',
  alignItems: 'center',
  gap: '16px'
}));
