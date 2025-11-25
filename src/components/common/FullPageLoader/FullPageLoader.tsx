import React from 'react';
import { Backdrop, CircularProgress } from '@mui/material';

interface FullPageLoaderProps {
  open: boolean;
}

const FullPageLoader: React.FC<FullPageLoaderProps> = ({ open }) => {
  return (
    <Backdrop sx={{ color: '#fff', zIndex: theme => theme.zIndex.modal + 1 }} open={open}>
      <CircularProgress color="inherit" />
    </Backdrop>
  );
};

export default FullPageLoader;
