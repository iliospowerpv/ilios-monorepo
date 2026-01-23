import * as React from 'react';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import LightModeIcon from '@mui/icons-material/LightMode';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import Tooltip from '@mui/material/Tooltip';
import { HeaderStyled } from './Header.styles';
import { Logo } from '../Logo/Logo';
import Typography from '@mui/material/Typography';
import { useThemeMode } from '../../../../contexts/theme/theme';

export const Header: React.FC = () => {
  const { mode, toggleTheme } = useThemeMode();

  return (
    <HeaderStyled position="fixed" data-testid="header__component">
      <Box px={t => t.spacing(18)} display="flex" justifyContent="space-between" alignItems="center" width="100%">
        <Box display="flex" flexDirection="column" height="64px">
          <Logo />
          <Typography variant="subtitle2" fontSize="10px">
            the sun&apos;s operating system &trade;
          </Typography>
        </Box>
        <Tooltip title={mode === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}>
          <IconButton onClick={toggleTheme} sx={{ color: '#ffffff' }}>
            {mode === 'light' ? <DarkModeIcon /> : <LightModeIcon />}
          </IconButton>
        </Tooltip>
      </Box>
    </HeaderStyled>
  );
};
