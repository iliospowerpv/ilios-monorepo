import { styled } from '@mui/system';

export const HeaderActionsContainer = styled('div')(() => ({
  marginBottom: '16px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '16px'
}));

export const FooterActionsContainer = styled('div')(() => ({
  marginTop: '16px',
  display: 'flex',
  alignItems: 'center',
  gap: '16px'
}));
