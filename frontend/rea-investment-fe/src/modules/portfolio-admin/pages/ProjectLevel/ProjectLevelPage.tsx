import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import Skeleton from '@mui/material/Skeleton';
import Chip from '@mui/material/Chip';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import Divider from '@mui/material/Divider';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import FolderIcon from '@mui/icons-material/Folder';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BusinessIcon from '@mui/icons-material/Business';
import BoltIcon from '@mui/icons-material/Bolt';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

import { ApiClient } from '../../../../api';
import { AddUserDialog } from '../../components/dialogs';

const getStatusColor = (status: string | undefined): 'success' | 'warning' | 'error' | 'default' => {
  switch (status?.toLowerCase()) {
    case 'active':
    case 'operational':
      return 'success';
    case 'pending':
    case 'in_progress':
      return 'warning';
    case 'inactive':
    case 'error':
      return 'error';
    default:
      return 'default';
  }
};

export const ProjectLevelPage: React.FC = () => {
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);

  const projectIdNum = parseInt(projectId || '0', 10);

  const { data: project, isLoading } = useQuery({
    queryKey: ['site', projectIdNum],
    queryFn: () => ApiClient.assetManagement.getSiteById(projectIdNum),
    enabled: projectIdNum > 0,
    staleTime: 5 * 60 * 1000
  });

  const projectName = project?.name || 'Project';
  const companyId = project?.company?.id;
  const companyName = project?.company?.name || 'Company';

  const readinessScore = React.useMemo(() => {
    if (!project) return 0;
    let score = 0;
    if (project.name) score += 15;
    if (project.address) score += 15;
    if (project.city) score += 10;
    if (project.state) score += 10;
    if (project.zip_code) score += 10;
    if (project.system_size_ac) score += 20;
    if (project.system_size_dc) score += 20;
    return score;
  }, [project]);

  const getReadinessColor = (score: number) => {
    if (score >= 80) return 'success';
    if (score >= 50) return 'warning';
    return 'error';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          component="button"
          underline="hover"
          color="inherit"
          onClick={() => navigate('/portfolio-admin')}
        >
          Portfolio
        </Link>
        {companyId && (
          <Link
            component="button"
            underline="hover"
            color="inherit"
            onClick={() => navigate(`/portfolio-admin/companies/${companyId}`)}
            sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
          >
            <ArrowBackIcon fontSize="small" />
            {companyName}
          </Link>
        )}
        <Typography color="text.primary">{projectName}</Typography>
      </Breadcrumbs>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <FolderIcon color="success" />
            <Typography variant="h4" component="h1">
              {isLoading ? <Skeleton width={200} /> : projectName}
            </Typography>
            {project && (
              <Chip
                size="small"
                label="Active"
                color="success"
              />
            )}
          </Box>
          <Typography variant="subtitle1" color="text.secondary">
            Project overview and administration
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<PersonAddIcon />}
          onClick={() => setIsAddUserOpen(true)}
        >
          Add User
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Project Overview
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              {isLoading ? (
                <Box>
                  {[1, 2, 3, 4].map(i => (
                    <Skeleton key={i} height={40} sx={{ mb: 1 }} />
                  ))}
                </Box>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <LocationOnIcon color="action" />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Location
                        </Typography>
                        <Typography variant="body1">
                          {project?.city}, {project?.state} {project?.zip_code}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <BusinessIcon color="action" />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Company
                        </Typography>
                        <Typography variant="body1">{companyName}</Typography>
                      </Box>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <BoltIcon color="action" />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          System Size (AC)
                        </Typography>
                        <Typography variant="body1">
                          {project?.system_size_ac ? `${project.system_size_ac} MW` : 'Not specified'}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                      <BoltIcon color="action" />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          System Size (DC)
                        </Typography>
                        <Typography variant="body1">
                          {project?.system_size_dc ? `${project.system_size_dc} MW` : 'Not specified'}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LocationOnIcon color="action" />
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Full Address
                        </Typography>
                        <Typography variant="body1">
                          {project?.address || 'Not specified'}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Project Status
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              {isLoading ? (
                <Skeleton height={100} />
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                      <CheckCircleIcon color="success" sx={{ fontSize: 40, mb: 1 }} />
                      <Typography variant="h6">{project?.state || 'Active'}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Current State
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                      <BoltIcon color="warning" sx={{ fontSize: 40, mb: 1 }} />
                      <Typography variant="h6">
                        {project?.system_size_ac ? `${project.system_size_ac} MW` : '—'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Capacity
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                      {readinessScore >= 80 ? (
                        <CheckCircleIcon color="success" sx={{ fontSize: 40, mb: 1 }} />
                      ) : (
                        <WarningIcon color="warning" sx={{ fontSize: 40, mb: 1 }} />
                      )}
                      <Typography variant="h6">{readinessScore}%</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Data Completeness
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Data Readiness
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2">Completeness</Typography>
                  <Chip
                    size="small"
                    label={`${readinessScore}%`}
                    color={getReadinessColor(readinessScore)}
                  />
                </Box>
                <Box
                  sx={{
                    height: 8,
                    bgcolor: 'grey.200',
                    borderRadius: 1,
                    overflow: 'hidden'
                  }}
                >
                  <Box
                    sx={{
                      height: '100%',
                      width: `${readinessScore}%`,
                      bgcolor: `${getReadinessColor(readinessScore)}.main`,
                      transition: 'width 0.3s ease'
                    }}
                  />
                </Box>
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {readinessScore >= 80
                  ? 'Project data is complete and ready for operations.'
                  : readinessScore >= 50
                  ? 'Some project information is missing. Consider updating the project details.'
                  : 'Critical project information is missing. Please complete the project setup.'}
              </Typography>

              <Button
                fullWidth
                variant="outlined"
                onClick={() => navigate(`/asset-management/sites/${projectIdNum}`)}
              >
                Edit Project Details
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Divider sx={{ mb: 2 }} />
              
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Button
                  fullWidth
                  variant="text"
                  onClick={() => navigate(`/asset-management/sites/${projectIdNum}`)}
                  sx={{ justifyContent: 'flex-start' }}
                >
                  View in Asset Management
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  onClick={() => navigate(`/operations-and-maintenance/sites/${projectIdNum}`)}
                  sx={{ justifyContent: 'flex-start' }}
                >
                  Operations & Maintenance
                </Button>
                <Button
                  fullWidth
                  variant="text"
                  onClick={() => navigate(`/due-diligence/sites/${projectIdNum}`)}
                  sx={{ justifyContent: 'flex-start' }}
                >
                  Due Diligence
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <AddUserDialog
        open={isAddUserOpen}
        onClose={() => setIsAddUserOpen(false)}
        level="project"
        entityId={projectIdNum}
        entityName={projectName}
      />
    </Box>
  );
};

export default ProjectLevelPage;
