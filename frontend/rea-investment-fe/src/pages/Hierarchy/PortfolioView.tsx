import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';
import FolderSpecialIcon from '@mui/icons-material/FolderSpecial';
import { useAccessibleEntities } from '../../hooks/useAccessibleEntities';
import { useNavigate } from 'react-router-dom';
import { useEntityContext } from '../../contexts/entityContext';

export const PortfolioView: React.FC = () => {
  const { companies, projects, isLoading } = useAccessibleEntities();
  const navigate = useNavigate();
  const { setCurrentCompany, setCurrentScope } = useEntityContext();

  const handleCompanyClick = (company: { id: number; name: string }) => {
    setCurrentCompany(company);
    setCurrentScope('company');
    navigate(`/project-hub/companies/${company.id}`);
  };

  if (isLoading) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography>Loading portfolio...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 4 }}>
        <FolderSpecialIcon sx={{ fontSize: 40, color: 'primary.main' }} />
        <Typography variant="h4" fontWeight={600}>
          Portfolio Overview
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Companies
            </Typography>
            <Typography variant="h3" color="primary.main">
              {companies.length}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Projects
            </Typography>
            <Typography variant="h3" color="primary.main">
              {projects.length}
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          Companies
        </Typography>
        <Grid container spacing={2}>
          {companies.map(company => (
            <Grid item xs={12} sm={6} md={4} key={company.id}>
              <Paper
                sx={{
                  p: 2,
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'action.hover' }
                }}
                onClick={() => handleCompanyClick(company)}
              >
                <Typography variant="subtitle1" fontWeight={500}>
                  {company.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {projects.filter(p => p.company_id === company.id).length} projects
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
};

export default PortfolioView;
