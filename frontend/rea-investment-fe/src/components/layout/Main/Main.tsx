import * as React from 'react';
import { Outlet } from 'react-router-dom';
import { MainContainer } from './Main.styles';

export const Main: React.FC = () => (
  <>
    <MainContainer component="main" data-testid="main__component">
      <Outlet />
    </MainContainer>
  </>
);
