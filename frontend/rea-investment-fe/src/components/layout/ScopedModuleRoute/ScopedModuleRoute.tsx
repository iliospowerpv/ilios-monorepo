import React, { useEffect, useRef } from 'react';
import { useParams, Outlet, Navigate } from 'react-router-dom';
import { useEntityContext, ScopeType } from '../../../contexts/entityContext';
import { useAccessibleEntities } from '../../../hooks/useAccessibleEntities';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';

interface ScopedModuleRouteProps {
  scope: ScopeType;
  children?: React.ReactNode;
}

export const ScopedModuleRoute: React.FC<ScopedModuleRouteProps> = ({ scope, children }) => {
  const params = useParams<{ companyId?: string; projectId?: string }>();
  const { setCurrentScope, setCurrentCompany, setCurrentProject, currentScope, currentCompany, currentProject } =
    useEntityContext();
  const { getCompanyById, getProjectById, isLoading, isFetching, refetch } = useAccessibleEntities();

  const attemptedRefetchRef = useRef<string | null>(null);

  const entityId = scope === 'company' ? params.companyId : scope === 'project' ? params.projectId : null;
  const refetchKey = `${scope}:${entityId ?? ''}`;

  useEffect(() => {
    attemptedRefetchRef.current = null;
  }, [refetchKey]);

  useEffect(() => {
    if (isLoading) return;

    if (scope === 'portfolio') {
      if (currentScope !== 'portfolio') {
        setCurrentScope('portfolio');
      }
    } else if (scope === 'company' && params.companyId) {
      const companyId = parseInt(params.companyId, 10);
      if (currentCompany?.id !== companyId) {
        const company = getCompanyById(companyId);
        if (company) {
          setCurrentCompany({ id: company.id, name: company.name });
          setCurrentScope('company');
        }
      } else if (currentScope !== 'company') {
        setCurrentScope('company');
      }
    } else if (scope === 'project' && params.projectId) {
      const projectId = parseInt(params.projectId, 10);
      const project = getProjectById(projectId);
      if (project) {
        if (currentCompany?.id !== project.company_id) {
          const company = getCompanyById(project.company_id);
          if (company) {
            setCurrentCompany({ id: company.id, name: company.name });
          }
        }
        if (currentProject?.id !== projectId) {
          setCurrentProject({ id: project.id, name: project.name });
        }
        if (currentScope !== 'project') {
          setCurrentScope('project');
        }
      }
    }
  }, [
    scope,
    params.companyId,
    params.projectId,
    isLoading,
    currentScope,
    currentCompany,
    currentProject,
    setCurrentScope,
    setCurrentCompany,
    setCurrentProject,
    getCompanyById,
    getProjectById
  ]);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', minHeight: 200 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (scope === 'company' && params.companyId) {
    const companyId = parseInt(params.companyId, 10);
    const company = getCompanyById(companyId);
    if (!company) {
      if (attemptedRefetchRef.current !== refetchKey) {
        attemptedRefetchRef.current = refetchKey;
        refetch();
        return (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', minHeight: 200 }}>
            <CircularProgress size={28} />
          </Box>
        );
      }
      if (isFetching) {
        return (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', minHeight: 200 }}>
            <CircularProgress size={28} />
          </Box>
        );
      }
      return <Navigate to="/companies" replace />;
    }
  }

  if (scope === 'project' && params.projectId) {
    const projectId = parseInt(params.projectId, 10);
    const project = getProjectById(projectId);
    if (!project) {
      if (attemptedRefetchRef.current !== refetchKey) {
        attemptedRefetchRef.current = refetchKey;
        refetch();
        return (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', minHeight: 200 }}>
            <CircularProgress size={28} />
          </Box>
        );
      }
      if (isFetching) {
        return (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', minHeight: 200 }}>
            <CircularProgress size={28} />
          </Box>
        );
      }
      return <Navigate to="/projects" replace />;
    }
  }

  return children ? <>{children}</> : <Outlet />;
};

export default ScopedModuleRoute;
