import React, { useEffect } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import BusinessIcon from '@mui/icons-material/Business';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import Chip from '@mui/material/Chip';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAccessibleEntities } from '../../hooks/useAccessibleEntities';
import { useEntityContext } from '../../contexts/entityContext';
import { buildLensRoute, ModuleType } from '../../utils/routing';

export const ProjectView: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { getProjectById, getCompanyById, isLoading } = useAccessibleEntities();
  const { setCurrentCompany, setCurrentProject, setCurrentScope, currentProject, currentCompany } = useEntityContext();
  const navigate = useNavigate();

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

      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          Quick Links
        </Typography>
        <Grid container spacing={2}>
          {[
            { module: 'asset-management' as ModuleType, label: 'Asset Management', icon: <AccountBalanceIcon /> },
            { module: 'finance' as ModuleType, label: 'Finance', icon: <AccountBalanceWalletIcon /> },
            { module: 'operations-and-maintenance' as ModuleType, label: 'O&M', icon: <WhatshotIcon /> },
            { module: 'due-diligence' as ModuleType, label: 'Due Diligence', icon: <FactCheckIcon /> }
          ].map(({ module, label, icon }) => (
            <Grid item key={module}>
              <Paper
                sx={{
                  p: 2,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  '&:hover': { bgcolor: 'action.hover' }
                }}
                onClick={() => navigate(buildLensRoute(module, 'project', { projectId: project.id }))}
              >
                {icon}
                {label}
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
};

export default ProjectView;
