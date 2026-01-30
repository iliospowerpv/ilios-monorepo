import React, { useEffect } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import BusinessIcon from '@mui/icons-material/Business';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import { useParams, useNavigate } from 'react-router-dom';
import { useAccessibleEntities } from '../../hooks/useAccessibleEntities';
import { useEntityContext } from '../../contexts/entityContext';
import { buildLensRoute, ModuleType } from '../../utils/routing';

export const CompanyView: React.FC = () => {
  const { companyId } = useParams<{ companyId: string }>();
  const { getProjectsByCompanyId, isLoading, getCompanyById } = useAccessibleEntities();
  const { setCurrentCompany, setCurrentProject, setCurrentScope, currentCompany } = useEntityContext();
  const navigate = useNavigate();

  const companyIdNum = companyId ? parseInt(companyId, 10) : null;
  const company = companyIdNum ? getCompanyById(companyIdNum) : null;
  const companyProjects = companyIdNum ? getProjectsByCompanyId(companyIdNum) : [];

  useEffect(() => {
    if (company && (!currentCompany || currentCompany.id !== company.id)) {
      setCurrentCompany({ id: company.id, name: company.name });
      setCurrentScope('company');
    }
  }, [company, currentCompany, setCurrentCompany, setCurrentScope]);

  const handleProjectClick = (project: { id: number; name: string }) => {
    setCurrentProject(project);
    setCurrentScope('project');
    navigate(`/projects/${project.id}`);
  };

  if (isLoading) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography>Loading company...</Typography>
      </Box>
    );
  }

  if (!company) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography color="error">Company not found or you do not have access.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 4 }}>
        <BusinessIcon sx={{ fontSize: 40, color: 'primary.main' }} />
        <Typography variant="h4" fontWeight={600}>
          {company.name}
        </Typography>
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Projects
            </Typography>
            <Typography variant="h3" color="primary.main">
              {companyProjects.length}
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Quick Actions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {[
                { module: 'asset-management' as ModuleType, label: 'Asset Management', icon: <AccountBalanceIcon /> },
                { module: 'finance' as ModuleType, label: 'Finance', icon: <AccountBalanceWalletIcon /> },
                { module: 'operations-and-maintenance' as ModuleType, label: 'O&M', icon: <WhatshotIcon /> },
                { module: 'due-diligence' as ModuleType, label: 'Due Diligence', icon: <FactCheckIcon /> }
              ].map(({ module, label, icon }) => (
                <Button
                  key={module}
                  variant="outlined"
                  startIcon={icon}
                  fullWidth
                  sx={{ justifyContent: 'flex-start' }}
                  onClick={() => navigate(buildLensRoute(module, 'company', { companyId: company.id }))}
                >
                  {label}
                </Button>
              ))}
            </Box>
          </Paper>
        </Grid>
      </Grid>

      <Box>
        <Typography variant="h5" gutterBottom>
          Projects
        </Typography>
        {companyProjects.length === 0 ? (
          <Typography color="text.secondary">No projects in this company.</Typography>
        ) : (
          <Grid container spacing={2}>
            {companyProjects.map(project => (
              <Grid item xs={12} sm={6} md={4} key={project.id}>
                <Paper
                  sx={{
                    p: 2,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' }
                  }}
                  onClick={() => handleProjectClick(project)}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <SolarPowerIcon color="primary" />
                    <Typography variant="subtitle1" fontWeight={500}>
                      {project.name}
                    </Typography>
                  </Box>
                </Paper>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>
    </Box>
  );
};

export default CompanyView;
