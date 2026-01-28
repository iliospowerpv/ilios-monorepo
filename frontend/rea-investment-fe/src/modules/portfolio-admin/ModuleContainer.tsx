import React from 'react';
import { Outlet } from 'react-router-dom';
import Box from '@mui/material/Box';

export const PortfolioAdminModuleContainer: React.FC = () => {
  return (
    <Box sx={{ minHeight: '100%' }}>
      <Outlet />
    </Box>
  );
};

export default PortfolioAdminModuleContainer;
