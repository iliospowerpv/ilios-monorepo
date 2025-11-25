import React from 'react';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';

const LoadingComponent: React.FC = () => (
  <Box display="flex" alignItems="center" justifyContent="center" mt="40px" data-testid="loading__component">
    <CircularProgress color="inherit" size={40} />
  </Box>
);

export default LoadingComponent;
