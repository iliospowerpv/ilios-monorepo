import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Companies from '../Companies/Companies';

export const DueDiligencePage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        Companies
      </Typography>
      <Companies />
    </Box>
  );
};

export default DueDiligencePage;
