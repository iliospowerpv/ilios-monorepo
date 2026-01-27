import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/auth/auth';

const ModuleGate: React.FC<React.PropsWithChildren> = ({ children }) => {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated || !user) return <Navigate to="/login" replace />;

  return <>{children}</>;
};

export const ModuleContainer: React.FC<React.PropsWithChildren> = ({ children }) => {
  return <ModuleGate>{children}</ModuleGate>;
};

export default ModuleContainer;
