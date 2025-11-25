import * as React from 'react';
import { Outlet } from 'react-router-dom';

import { MainContainer, Offset, CardStyled, CardContentStyled } from './Main.styles';

export const Main: React.FC = () => (
  <MainContainer component="main" data-testid="main__component">
    <Offset />
    <CardStyled>
      <CardContentStyled>
        <Outlet />
      </CardContentStyled>
    </CardStyled>
  </MainContainer>
);
