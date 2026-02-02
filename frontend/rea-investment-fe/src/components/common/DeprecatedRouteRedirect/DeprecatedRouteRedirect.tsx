import React from 'react';
import { Navigate, useParams } from 'react-router-dom';
import type { ProjectHubTab } from '../ProjectPicker';

interface DeprecatedRouteRedirectProps {
  targetTab: ProjectHubTab;
}

export const DeprecatedRouteRedirect: React.FC<DeprecatedRouteRedirectProps> = ({ targetTab }) => {
  const { siteId } = useParams<{ siteId: string }>();

  if (!siteId) {
    return <Navigate to="/home" replace />;
  }

  const tabPath = targetTab === 'overview' ? '' : `/${targetTab}`;
  const targetPath = `/project-hub/projects/${siteId}${tabPath}`;

  return <Navigate to={targetPath} replace />;
};

export default DeprecatedRouteRedirect;
