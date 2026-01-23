import * as React from 'react';
import { Outlet } from 'react-router-dom';
import { MainContainer } from './Main.styles';
import { useSidebar } from '../../../contexts/sidebar';

export const Main: React.FC = () => {
  const { isOpen } = useSidebar();

  return (
    <MainContainer component="main" data-testid="main__component" sidebarOpen={isOpen}>
      <Outlet />
    </MainContainer>
  );
};
