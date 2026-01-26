import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import Grid from '@mui/material/Grid';
import SearchIcon from '@mui/icons-material/Search';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAccessibleEntities } from '../../hooks/useAccessibleEntities';
import { useEntityContext } from '../../contexts/entityContext';

export const ProjectsPickerView: React.FC = () => {
  const [searchParams] = useSearchParams();
  const companyIdParam = searchParams.get('companyId');
  const companyIdFilter = companyIdParam ? parseInt(companyIdParam, 10) : null;

  const { projects, getProjectsByCompanyId, isLoading, getCompanyById } = useAccessibleEntities();
  const [search, setSearch] = useState('');
  const navigate = useNavigate();
  const { setCurrentProject, setCurrentCompany, setCurrentScope, currentCompany } = useEntityContext();

  const baseProjects = companyIdFilter ? getProjectsByCompanyId(companyIdFilter) : projects;
  const filteredProjects = search
    ? baseProjects.filter(
        p =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.company_name.toLowerCase().includes(search.toLowerCase())
      )
    : baseProjects;

  const filterCompany = companyIdFilter ? getCompanyById(companyIdFilter) : null;

  const handleProjectClick = (project: { id: number; name: string; company_id: number; company_name: string }) => {
    if (!currentCompany || currentCompany.id !== project.company_id) {
      setCurrentCompany({ id: project.company_id, name: project.company_name });
    }
    setCurrentProject({ id: project.id, name: project.name });
    setCurrentScope('project');
    navigate(`/projects/${project.id}`);
  };

  if (isLoading) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography>Loading projects...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <SolarPowerIcon sx={{ fontSize: 40, color: 'primary.main' }} />
        <Typography variant="h4" fontWeight={600}>
          Select a Project
        </Typography>
      </Box>

      {filterCompany && (
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Showing projects for <strong>{filterCompany.name}</strong>
        </Typography>
      )}

      <TextField
        placeholder="Search projects..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        fullWidth
        sx={{ mb: 4, maxWidth: 400 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          )
        }}
      />

      <Grid container spacing={2}>
        {filteredProjects.map(project => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
            <Paper
              sx={{
                p: 3,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                '&:hover': {
                  bgcolor: 'action.hover',
                  transform: 'translateY(-2px)',
                  boxShadow: 2
                }
              }}
              onClick={() => handleProjectClick(project)}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <SolarPowerIcon color="primary" />
                <Box>
                  <Typography variant="subtitle1" fontWeight={500}>
                    {project.name}
                  </Typography>
                  {!companyIdFilter && (
                    <Typography variant="body2" color="text.secondary">
                      {project.company_name}
                    </Typography>
                  )}
                </Box>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {filteredProjects.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <Typography color="text.secondary">
            {search ? 'No projects match your search.' : 'No projects available.'}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default ProjectsPickerView;
