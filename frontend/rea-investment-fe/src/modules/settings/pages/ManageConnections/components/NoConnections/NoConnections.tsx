import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

const NoConnections: React.FC = () => (
  <Box
    data-testid="no-connections__component"
    sx={{
      border: '1px solid #0000001F',
      alignContent: 'center',
      height: '80px',
      color: 'text.secondary'
    }}
  >
    <Typography variant="body2" textAlign="center" gutterBottom>
      No connections yet
    </Typography>
  </Box>
);

export default NoConnections;
