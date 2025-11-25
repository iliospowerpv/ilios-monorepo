import * as React from 'react';
import SvgIcon from '@mui/material/SvgIcon';
import Box from '@mui/material/Box';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../contexts/auth/auth';

export const CompanyLogo: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const hasMyPortfolioAccess = user?.role?.permissions?.['Investor Dashboard']?.view;

  return (
    <Box
      data-testid="company-logo__component"
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        cursor: 'pointer',
        width: theme => theme.spacing(8),
        height: theme => theme.spacing(8)
      }}
      onClick={() => {
        navigate(hasMyPortfolioAccess ? '/my-portfolio' : '/dashboard');
      }}
    >
      <SvgIcon sx={{ fontSize: 16 }}>
        <svg width="10" height="16" viewBox="0 0 10 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M8.06188 0H10V2.16485H8.06188V0ZM1.93812 4.07168H0V6.23652H1.93812V4.07168ZM1.93812 8.14785H0V16H1.93812V8.14785ZM4.0329 16V2.17725H5.97101V16H4.0329ZM8.06189 4.07168H10V16H8.06189V4.07168Z"
            fill="white"
          />
        </svg>
      </SvgIcon>
    </Box>
  );
};
