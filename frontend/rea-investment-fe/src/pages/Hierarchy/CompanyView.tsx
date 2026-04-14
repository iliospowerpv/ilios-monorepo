import React, { useEffect, useCallback, useMemo } from 'react';
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
import { ProjectPicker, useProjectNavigation, type ProjectHubTab } from '../../components/common/ProjectPicker';

export const CompanyView: React.FC = () => {
  const { companyId } = useParams<{ companyId: string }>();
  const { getProjectsByCompanyId, isLoading, getCompanyById } = useAccessibleEntities();
  const { setCurrentCompany, setCurrentProject, setCurrentScope, currentCompany, currentProject } = useEntityContext();
  const navigate = useNavigate();
  const { navigateToProjectHub } = useProjectNavigation();
  const [pickerOpen, setPickerOpen] = React.useState(false);
  const [pickerTab, setPickerTab] = React.useState<ProjectHubTab | null>(null);

  const companyIdNum = companyId ? parseInt(companyId, 10) : null;
  const company = companyIdNum ? getCompanyById(companyIdNum) : null;
  const companyProjects = useMemo(
    () => (companyIdNum ? getProjectsByCompanyId(companyIdNum) : []),
    [companyIdNum, getProjectsByCompanyId]
  );

  useEffect(() => {
    if (company && (!currentCompany || currentCompany.id !== company.id)) {
      setCurrentCompany({ id: company.id, name: company.name });
      setCurrentScope('company');
    }
  }, [company, currentCompany, setCurrentCompany, setCurrentScope]);

  const handleProjectClick = (project: { id: number; name: string }) => {
    setCurrentProject(project);
    setCurrentScope('project');
    navigate(`/project-hub/projects/${project.id}`);
  };

  const handleProjectHubAction = useCallback(
    (tab: ProjectHubTab) => {
      const lastProjectInCompany =
        currentProject && companyIdNum && companyProjects.some(p => p.id === currentProject.id) ? currentProject : null;

      if (lastProjectInCompany) {
        navigateToProjectHub(lastProjectInCompany.id, tab);
      } else {
        setPickerTab(tab);
        setPickerOpen(true);
      }
    },
    [currentProject, companyIdNum, companyProjects, navigateToProjectHub]
  );

  const handlePickerSelect = useCallback(
    (project: { id: number; name: string }) => {
      setCurrentProject({ id: project.id, name: project.name });
      setCurrentScope('project');
      navigateToProjectHub(project.id, pickerTab || 'overview');
      setPickerOpen(false);
      setPickerTab(null);
    },
    [setCurrentProject, setCurrentScope, navigateToProjectHub, pickerTab]
  );

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
                  onClick={() => handleProjectHubAction(tab)}
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

      <ProjectPicker
        open={pickerOpen}
        onClose={() => {
          setPickerOpen(false);
          setPickerTab(null);
        }}
        onSelect={handlePickerSelect}
        title={`Select a Project for ${
          pickerTab === 'data-room'
            ? 'Data Room'
            : pickerTab === 'finance'
              ? 'Finance'
              : pickerTab === 'om'
                ? 'O&M'
                : 'Asset Management'
        }`}
        companyId={companyIdNum}
      />
    </Box>
  );
};

export default CompanyView;
