import React, { useEffect } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import BusinessIcon from '@mui/icons-material/Business';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import SettingsInputAntennaIcon from '@mui/icons-material/SettingsInputAntenna';
import Chip from '@mui/material/Chip';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAccessibleEntities } from '../../hooks/useAccessibleEntities';
import { useEntityContext } from '../../contexts/entityContext';
import { useProjectNavigation, type ProjectHubTab } from '../../components/common/ProjectPicker';

export const ProjectView: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { getProjectById, getCompanyById, isLoading } = useAccessibleEntities();
  const { setCurrentCompany, setCurrentProject, setCurrentScope, currentProject, currentCompany } = useEntityContext();
  const navigate = useNavigate();
  const { navigateToProjectHub } = useProjectNavigation();

  const projectIdNum = projectId ? parseInt(projectId, 10) : null;
  const project = projectIdNum ? getProjectById(projectIdNum) : null;
  const company = project ? getCompanyById(project.company_id) : null;

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

  if (isLoading) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography>Loading project...</Typography>
      </Box>
    );
  }

  if (!project) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography color="error">Project not found or you do not have access.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <SolarPowerIcon sx={{ fontSize: 40, color: 'primary.main' }} />
        <Typography variant="h4" fontWeight={600}>
          {project.name}
        </Typography>
      </Box>

      {company && (
        <Box sx={{ mb: 4 }}>
          <Chip
            icon={<BusinessIcon />}
            label={company.name}
            component={Link}
            to={`/companies/${company.id}`}
            clickable
            variant="outlined"
          />
        </Box>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Project Overview
            </Typography>
            <Typography variant="body1" color="text.secondary">
              This is the canonical project view. Use the module sidebar to navigate to specific project views (Asset
              Management, O&M, Due Diligence, Finance, etc.).
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mt: 1 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {[
                { tab: 'overview' as ProjectHubTab, label: 'Asset Management', icon: <AccountBalanceIcon /> },
                { tab: 'finance' as ProjectHubTab, label: 'Finance', icon: <AccountBalanceWalletIcon /> },
                { tab: 'om' as ProjectHubTab, label: 'O&M', icon: <WhatshotIcon /> },
                { tab: 'data-room' as ProjectHubTab, label: 'Data Room', icon: <FactCheckIcon /> }
              ].map(({ tab, label, icon }) => (
                <Button
                  key={tab}
                  variant="outlined"
                  startIcon={icon}
                  fullWidth
                  sx={{ justifyContent: 'flex-start' }}
                  onClick={() => navigateToProjectHub(project.id, tab)}
                >
                  {label}
                </Button>
              ))}
              <Button
                variant="outlined"
                startIcon={<SettingsInputAntennaIcon />}
                fullWidth
                sx={{ justifyContent: 'flex-start' }}
                onClick={() => navigate(`/projects/${project.id}/telemetry`)}
              >
                Telemetry
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ProjectView;
