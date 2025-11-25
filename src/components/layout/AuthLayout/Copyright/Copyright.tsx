import React from 'react';
import Typography from '@mui/material/Typography';

import { CopyrightStyled } from './Copyright.styles';

export const Copyright: React.FC = () => {
  return (
    <CopyrightStyled data-testid="copyright__component">
      <Typography variant="body2" color="common.white" align="center" fontSize="12px">
        {`Copyright © 2022 iliOS. All right reserved.`}
      </Typography>
    </CopyrightStyled>
  );
};
