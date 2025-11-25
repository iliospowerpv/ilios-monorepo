import * as React from 'react';
import Box from '@mui/material/Box';
import { HeaderStyled } from './Header.styles';
import { Logo } from '../Logo/Logo';
import Typography from '@mui/material/Typography';

export const Header: React.FC = () => (
  <HeaderStyled position="fixed" data-testid="header__component">
    <Box px={t => t.spacing(18)}>
      <Box display="flex" flexDirection="column" height="64px">
        <Logo />
        <Typography variant="subtitle2" fontSize="10px">
          the sun’s operating system ™
        </Typography>
      </Box>
    </Box>
  </HeaderStyled>
);
