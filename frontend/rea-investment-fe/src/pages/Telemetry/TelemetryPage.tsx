import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import { Link as RouterLink } from 'react-router-dom';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import BusinessIcon from '@mui/icons-material/Business';

import { ApiClient } from '../../api';
import { useEntityContext } from '../../contexts/entityContext';
import { useAccessibleEntities } from '../../hooks/useAccessibleEntities';
import { Telemetry } from '../../modules/project-hub/pages/AssetManagementSiteDetails/tabs/Telemetry';

export const TelemetryPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { setCurrentCompany, setCurrentProject, setCurrentScope, currentProject, currentCompany } = useEntityContext();
  const { getProjectById, getCompanyById, isLoading: isLoadingEntities } = useAccessibleEntities();

  const projectIdNum = projectId ? parseInt(projectId, 10) : null;
  const project = projectIdNum ? getProjectById(projectIdNum) : null;
  const company = project ? getCompanyById(project.company_id) : null;

  const { data: siteDetails, isLoading: isLoadingSite } = useQuery({
    queryKey: ['site', 'details', { siteId: projectIdNum }],
    queryFn: () => ApiClient.assetManagement.getSiteById(projectIdNum!),
    enabled: !!projectIdNum
  });

  useEffect(() => {
    if (project) {
      if (!currentProject || currentProject.id !== project.id) {
        setCurrentProject({ id: project.id, name: project.name });
      }
      if (company && (!currentCompany || currentCompany.id !== company.id)) {
        setCurrentCompany({ id: company.id, name: company.name });
      }
      setCurrentScope('project');
    }
  }, [project, company, currentProject, currentCompany, setCurrentProject, setCurrentCompany, setCurrentScope]);

  if (isLoadingEntities || isLoadingSite) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!project || !projectIdNum) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography color="error">Project not found or you do not have access.</Typography>
      </Box>
    );
  }

  if (!siteDetails) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography color="error">Unable to load project details.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Breadcrumbs sx={{ mb: 3 }}>
        {company && (
          <Link
            component={RouterLink}
            to={`/companies/${company.id}`}
            underline="hover"
            sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
          >
            <BusinessIcon fontSize="small" />
            {company.name}
          </Link>
        )}
        <Link
          component={RouterLink}
          to={`/project-hub/projects/${project.id}`}
          underline="hover"
          sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
        >
          <SolarPowerIcon fontSize="small" />
          {project.name}
        </Link>
        <Typography color="text.primary">Telemetry</Typography>
      </Breadcrumbs>

      <Telemetry siteDetails={siteDetails} />
    </Box>
  );
};

export const createTelemetryHandle = () => ({
  breadcrumb: 'Telemetry'
});

export default TelemetryPage;
