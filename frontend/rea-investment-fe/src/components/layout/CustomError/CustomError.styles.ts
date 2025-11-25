import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';

export const ContainerStyled = styled(Box)(() => ({
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  height: 'calc(100vh - 80px)',
  padding: '80px 24px 0',
  marginLeft: '64px',
  maxWidth: 'calc(100% - 64px)',
  width: '100%'
}));

export const ContainerStyledForReport = styled(Box)(() => ({
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  height: 'calc(80vh - 80px)',
  padding: '40px 24px 0',
  marginLeft: '64px',
  maxWidth: 'calc(100% - 64px)',
  width: '100%'
}));

export const SectionStyled = styled(Box)(() => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  width: '480px',
  textAlign: 'center'
}));

export const iconStyles = {
  color: (theme: { color: { blueGray: any } }) => theme.color.blueGray,
  fontSize: '48px',
  marginBottom: '32px'
};
