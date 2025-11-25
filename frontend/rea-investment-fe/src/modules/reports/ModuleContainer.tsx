import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';

import { useAuth } from '../../contexts/auth/auth';

const ModuleGate: React.FC<React.PropsWithChildren> = ({ children }) => {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated || !user) return <Navigate to="/login" replace />;
  if (user.is_system_user || user.role?.permissions?.['Reports']?.view) {
    return <>{children}</>;
  }

  return <Navigate to="/" replace />;
};

export const ModuleContainer: React.FC = () => (
  <ModuleGate>
    <Outlet />
  </ModuleGate>
);

export default ModuleContainer;
