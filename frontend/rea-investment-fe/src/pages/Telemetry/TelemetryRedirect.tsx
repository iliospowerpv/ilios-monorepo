import React from 'react';
import { Navigate, useParams } from 'react-router-dom';

export const TelemetryRedirect: React.FC = () => {
  const { siteId } = useParams<{ siteId: string }>();

  if (!siteId) {
    return <Navigate to="/projects" replace />;
  }

  return <Navigate to={`/projects/${siteId}/telemetry`} replace />;
};

export default TelemetryRedirect;
