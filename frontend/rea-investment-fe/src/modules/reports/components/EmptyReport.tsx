import React from 'react';
import Typography from '@mui/material/Typography';
import AddchartIcon from '@mui/icons-material/Addchart';

import {
  SectionStyled,
  iconStyles,
  ContainerStyledForReport
} from '../../../components/layout/CustomError/CustomError.styles';

const EmptyReport: React.FC = () => {
  return (
    <ContainerStyledForReport>
      <SectionStyled>
        <AddchartIcon sx={iconStyles} />
        <Typography variant="h4" fontWeight="600" color="text.primary" marginBottom="16px" gutterBottom>
          Select Report Criteria
        </Typography>
        <Typography variant="body2" color="text.secondary" marginBottom="32px" gutterBottom>
          Please select a company, site, report type, and date range to generate a report.
        </Typography>
      </SectionStyled>
    </ContainerStyledForReport>
  );
};

export default EmptyReport;
