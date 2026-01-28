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
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import Divider from '@mui/material/Divider';
import AddIcon from '@mui/icons-material/Add';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import BusinessIcon from '@mui/icons-material/Business';
import FolderIcon from '@mui/icons-material/Folder';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SettingsIcon from '@mui/icons-material/Settings';
import AssessmentIcon from '@mui/icons-material/Assessment';

import { ApiClient } from '../../../../api';
import { AddProjectDialog, AddUserDialog } from '../../components/dialogs';

export const CompanyLevelPage: React.FC = () => {
  const navigate = useNavigate();
  const { companyId } = useParams<{ companyId: string }>();
  const [isAddProjectOpen, setIsAddProjectOpen] = useState(false);
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);

  const companyIdNum = parseInt(companyId || '0', 10);

  const { data: company, isLoading: isLoadingCompany } = useQuery({
    queryKey: ['company', companyIdNum],
    queryFn: () => ApiClient.companies.company(companyIdNum),
    enabled: companyIdNum > 0,
    staleTime: 5 * 60 * 1000
  });

  const { data: sites, isLoading: isLoadingSites } = useQuery({
    queryKey: ['companySites', companyIdNum],
    queryFn: () => ApiClient.assetManagement.sites({ skip: 0, limit: 100, search: String(companyIdNum) } as any),
    enabled: companyIdNum > 0,
    staleTime: 5 * 60 * 1000
  });

  const { data: members, isLoading: isLoadingMembers } = useQuery({
    queryKey: ['companyMembers', companyIdNum],
    queryFn: () => ApiClient.workspace.getCompanyMembers(companyIdNum),
    enabled: companyIdNum > 0,
    staleTime: 5 * 60 * 1000
  });

  const companyName = company?.name || 'Company';
  const projectList = sites?.items || [];
  const memberCount = members?.length || 0;

  return (
    <Box sx={{ p: 3 }}>
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          component="button"
          underline="hover"
          color="inherit"
          onClick={() => navigate('/portfolio-admin')}
          sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
        >
          <ArrowBackIcon fontSize="small" />
          Portfolio
        </Link>
        <Typography color="text.primary">{companyName}</Typography>
      </Breadcrumbs>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <BusinessIcon color="primary" />
            <Typography variant="h4" component="h1">
              {isLoadingCompany ? <Skeleton width={200} /> : companyName}
            </Typography>
          </Box>
          <Typography variant="subtitle1" color="text.secondary">
            Manage projects and users for this company
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<PersonAddIcon />}
            onClick={() => setIsAddUserOpen(true)}
          >
            Add User
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setIsAddProjectOpen(true)}
          >
            Add Project
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <FolderIcon sx={{ fontSize: 40, color: 'success.main' }} />
                <Box>
                  <Typography variant="h3" component="div">
                    {isLoadingSites ? <Skeleton width={40} /> : projectList.length}
                  </Typography>
                  <Typography color="text.secondary">Projects</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <PersonAddIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                <Box>
                  <Typography variant="h3" component="div">
                    {isLoadingMembers ? <Skeleton width={40} /> : memberCount}
                  </Typography>
                  <Typography color="text.secondary">Users</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Quick Links
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  size="small"
                  startIcon={<AssessmentIcon />}
                  onClick={() => navigate(`/asset-management/sites?company_id=${companyIdNum}`)}
                >
                  Asset Management
                </Button>
                <Button
                  size="small"
                  startIcon={<SettingsIcon />}
                  onClick={() => navigate(`/settings/my-company`)}
                >
                  Settings
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Projects
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Project Name</TableCell>
                      <TableCell>Location</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {isLoadingSites ? (
                      [1, 2, 3].map(i => (
                        <TableRow key={i}>
                          <TableCell><Skeleton /></TableCell>
                          <TableCell><Skeleton /></TableCell>
                          <TableCell><Skeleton width={80} /></TableCell>
                          <TableCell><Skeleton width={40} /></TableCell>
                        </TableRow>
                      ))
                    ) : projectList.length > 0 ? (
                      projectList.map((project: any) => (
                        <TableRow
                          key={project.id}
                          hover
                          sx={{ cursor: 'pointer' }}
                          onClick={() => navigate(`/portfolio-admin/projects/${project.id}`)}
                        >
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <FolderIcon fontSize="small" color="action" />
                              {project.name}
                            </Box>
                          </TableCell>
                          <TableCell>{project.state}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={project.status || 'Active'}
                              color="success"
                            />
                          </TableCell>
                          <TableCell align="right">
                            <IconButton size="small">
                              <ChevronRightIcon />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} align="center">
                          <Typography color="text.secondary" sx={{ py: 3 }}>
                            No projects found. Add your first project to this company.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <AddProjectDialog
        open={isAddProjectOpen}
        onClose={() => setIsAddProjectOpen(false)}
        companyId={companyIdNum}
        companyName={companyName}
      />

      <AddUserDialog
        open={isAddUserOpen}
        onClose={() => setIsAddUserOpen(false)}
        level="company"
        entityId={companyIdNum}
        entityName={companyName}
      />
    </Box>
  );
};

export default CompanyLevelPage;
