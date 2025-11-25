import React from 'react';
import Box from '@mui/material/Box';

import type { SignUpScreenProps } from './types';

export const BlankScreen: React.FC<SignUpScreenProps> = () => (
  <Box
    position="fixed"
    top="0"
    left="0"
    height="100vh"
    width="100vw"
    sx={{ bgcolor: 'white', zIndex: theme => theme.zIndex.appBar }}
  />
);
