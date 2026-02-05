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
import Tooltip from '@mui/material/Tooltip';
import AddIcon from '@mui/icons-material/Add';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import BusinessIcon from '@mui/icons-material/Business';
import FolderIcon from '@mui/icons-material/Folder';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SettingsIcon from '@mui/icons-material/Settings';
import AssessmentIcon from '@mui/icons-material/Assessment';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import ContactsIcon from '@mui/icons-material/Contacts';

import { ApiClient } from '../../../../api';
import { ContactsList } from '../../components/contacts';
import { FinanceIntegrationsSection, FinanceHealthCard } from '../../components/finance';
import type { CompanyMember } from '../../../../api';
import {
  AddProjectDialog,
  AddUserDialog,
  EditUserDialog,
  RemoveUserDialog,
  EditCompanyDialog
} from '../../components/dialogs';

const getRoleLabel = (role: string): string => {
  switch (role) {
    case 'company_admin':
      return 'Admin';
    case 'contributor':
      return 'Contributor';
    case 'read_only':
      return 'Read Only';
    default:
      return role;
  }
};

const getRoleColor = (role: string): 'primary' | 'secondary' | 'default' => {
  switch (role) {
    case 'company_admin':
      return 'primary';
    case 'contributor':
      return 'secondary';
    default:
      return 'default';
  }
};

export const CompanyLevelPage: React.FC = () => {
  const navigate = useNavigate();
  const { companyId } = useParams<{ companyId: string }>();
  const [isAddProjectOpen, setIsAddProjectOpen] = useState(false);
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);
  const [isEditUserOpen, setIsEditUserOpen] = useState(false);
  const [isRemoveUserOpen, setIsRemoveUserOpen] = useState(false);
  const [isEditCompanyOpen, setIsEditCompanyOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<CompanyMember | null>(null);

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
  const memberList = members || [];
  const memberCount = memberList.length;

  const handleEditUser = (member: CompanyMember) => {
    setSelectedMember(member);
    setIsEditUserOpen(true);
  };

  const handleRemoveUser = (member: CompanyMember) => {
    setSelectedMember(member);
    setIsRemoveUserOpen(true);
  };

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
          <Tooltip title="Edit Company">
            <IconButton onClick={() => setIsEditCompanyOpen(true)} color="primary">
              <EditIcon />
            </IconButton>
          </Tooltip>
          <Button variant="outlined" startIcon={<PersonAddIcon />} onClick={() => setIsAddUserOpen(true)}>
            Add User
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setIsAddProjectOpen(true)}>
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
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<AssessmentIcon />}
                  onClick={() => navigate(`/project-hub/sites?company_id=${companyIdNum}`)}
                  sx={{ justifyContent: 'flex-start' }}
                >
                  Asset Management
                </Button>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<SettingsIcon />}
                  onClick={() => navigate(`/settings/my-company`)}
                  sx={{ justifyContent: 'flex-start' }}
                >
                  Settings
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Users
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Email</TableCell>
                      <TableCell>Role</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {isLoadingMembers ? (
                      [1, 2, 3].map(i => (
                        <TableRow key={i}>
                          <TableCell>
                            <Skeleton />
                          </TableCell>
                          <TableCell>
                            <Skeleton />
                          </TableCell>
                          <TableCell>
                            <Skeleton width={80} />
                          </TableCell>
                          <TableCell>
                            <Skeleton width={60} />
                          </TableCell>
                        </TableRow>
                      ))
                    ) : memberList.length > 0 ? (
                      memberList.map((member: CompanyMember) => (
                        <TableRow key={member.membership_id} hover>
                          <TableCell>
                            {member.first_name} {member.last_name}
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" color="text.secondary">
                              {member.email}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip size="small" label={getRoleLabel(member.role)} color={getRoleColor(member.role)} />
                          </TableCell>
                          <TableCell align="right">
                            <Tooltip title="Edit user">
                              <IconButton size="small" onClick={() => handleEditUser(member)}>
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title="Remove user">
                              <IconButton size="small" color="error" onClick={() => handleRemoveUser(member)}>
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} align="center">
                          <Typography color="text.secondary" sx={{ py: 3 }}>
                            No users found. Add users to grant them access to this company.
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

        <Grid item xs={12} lg={6}>
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
                          <TableCell>
                            <Skeleton />
                          </TableCell>
                          <TableCell>
                            <Skeleton />
                          </TableCell>
                          <TableCell>
                            <Skeleton width={80} />
                          </TableCell>
                          <TableCell>
                            <Skeleton width={40} />
                          </TableCell>
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
                            <Chip size="small" label={project.status || 'Active'} color="success" />
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

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <ContactsIcon color="primary" />
            <Typography variant="h6">Contacts</Typography>
          </Box>
          <ContactsList scopeType="company" scopeId={companyIdNum} />
        </CardContent>
      </Card>

      <FinanceHealthCard companyId={companyIdNum} />

      <FinanceIntegrationsSection companyId={companyIdNum} />

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

      <EditUserDialog
        open={isEditUserOpen}
        onClose={() => {
          setIsEditUserOpen(false);
          setSelectedMember(null);
        }}
        level="company"
        entityId={companyIdNum}
        entityName={companyName}
        member={selectedMember}
      />

      <RemoveUserDialog
        open={isRemoveUserOpen}
        onClose={() => {
          setIsRemoveUserOpen(false);
          setSelectedMember(null);
        }}
        level="company"
        entityId={companyIdNum}
        entityName={companyName}
        member={selectedMember}
      />

      <EditCompanyDialog
        open={isEditCompanyOpen}
        onClose={() => setIsEditCompanyOpen(false)}
        company={
          company
            ? {
                id: company.id,
                name: company.name,
                company_type: company.company_type,
                email: company.email,
                phone: company.phone,
                address: company.address
              }
            : null
        }
      />
    </Box>
  );
};

export default CompanyLevelPage;
