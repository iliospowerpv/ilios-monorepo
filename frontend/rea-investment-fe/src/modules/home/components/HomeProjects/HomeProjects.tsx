import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import FolderIcon from '@mui/icons-material/Folder';
import BusinessIcon from '@mui/icons-material/Business';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import Skeleton from '@mui/material/Skeleton';

import type { WorkspaceProject } from '../../../../api/workspace';

interface HomeProjectsProps {
  projects: WorkspaceProject[];
  isLoading?: boolean;
}

export const HomeProjects: React.FC<HomeProjectsProps> = ({ projects, isLoading }) => {
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Your Projects
          </Typography>
          <Grid container spacing={2}>
            {[1, 2, 3].map(i => (
              <Grid item xs={12} md={6} lg={4} key={i}>
                <Skeleton variant="rectangular" height={140} sx={{ borderRadius: 1 }} />
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    );
  }

  if (projects.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Your Projects
          </Typography>
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <FolderIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
            <Typography color="text.secondary">You don&apos;t have access to any projects yet.</Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Your Projects
        </Typography>
        <Grid container spacing={2}>
          {projects.map(project => {
            const location = [project.city, project.state].filter(Boolean).join(', ');

            return (
              <Grid item xs={12} md={6} lg={4} key={project.project_id}>
                <Card
                  variant="outlined"
                  sx={{
                    height: '100%',
                    '&:hover': {
                      borderColor: 'primary.main',
                      boxShadow: 1
                    }
                  }}
                >
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
                        <FolderIcon color="primary" />
                        <Typography variant="subtitle1" fontWeight={500} noWrap>
                          {project.project_name}
                        </Typography>
                      </Box>
                    </Box>

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                      <BusinessIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                      <Chip size="small" label={project.company_name} variant="outlined" />
                    </Box>

                    {location && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                        <LocationOnIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                        <Typography variant="body2" color="text.secondary">
                          {location}
                        </Typography>
                      </Box>
                    )}

                    {(project.system_size_ac || project.system_size_dc) && (
                      <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mb: 1 }}>
                        {project.system_size_ac ? `${project.system_size_ac} kW AC` : ''}
                        {project.system_size_ac && project.system_size_dc ? ' / ' : ''}
                        {project.system_size_dc ? `${project.system_size_dc} kW DC` : ''}
                      </Typography>
                    )}

                    <Button
                      variant="outlined"
                      size="small"
                      endIcon={<OpenInNewIcon />}
                      onClick={() => navigate(`/project-hub/projects/${project.project_id}`)}
                      fullWidth
                    >
                      Open Project
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default HomeProjects;
