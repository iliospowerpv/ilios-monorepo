import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Alert from '@mui/material/Alert';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import AddBusinessIcon from '@mui/icons-material/AddBusiness';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import BusinessIcon from '@mui/icons-material/Business';
import FolderIcon from '@mui/icons-material/Folder';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import DeleteIcon from '@mui/icons-material/Delete';
import PeopleIcon from '@mui/icons-material/People';
import DomainIcon from '@mui/icons-material/Domain';

import { ApiClient } from '../../../../api';
import { AddCompanyDialog, AddUserDialog } from '../../components/dialogs';
import { EntityDirectoryTab } from '../../components/entities';
import { useNotify } from '../../../../contexts/notifications/notifications';
import { useAuth } from '../../../../contexts/auth/auth';

export const PortfolioLevelPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const notify = useNotify();
  const { user } = useAuth();
  const [isAddCompanyOpen, setIsAddCompanyOpen] = useState(false);
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const [removeMemberDialog, setRemoveMemberDialog] = useState<{ open: boolean; member: any | null }>({
    open: false,
    member: null
  });

  const isSystemAdmin = user?.is_system_user;

  const { data: workspace, isLoading } = useQuery({
    queryKey: ['workspace'],
    queryFn: () => ApiClient.workspace.getWorkspace(),
    staleTime: 5 * 60 * 1000
  });

  const { data: portfolioMembersData, isLoading: isLoadingMembers } = useQuery({
    queryKey: ['portfolioMembers'],
    queryFn: () => ApiClient.workspace.getPortfolioMembers(),
    enabled: isSystemAdmin,
    staleTime: 5 * 60 * 1000
  });

  const removeMemberMutation = useMutation({
    mutationFn: (accessId: number) => ApiClient.workspace.removePortfolioMember(accessId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolioMembers'] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      notify('Member removed from portfolio');
      setRemoveMemberDialog({ open: false, member: null });
    },
    onError: () => {
      notify('Failed to remove member');
    }
  });

  const companies = workspace?.companies || [];
  const summary = workspace?.summary;
  const portfolioMembers = portfolioMembersData?.members || [];

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Portfolio Admin
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Manage all companies, projects, and users across the portfolio
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" startIcon={<PersonAddIcon />} onClick={() => setIsAddUserOpen(true)}>
            Add User
          </Button>
          <Button variant="contained" startIcon={<AddBusinessIcon />} onClick={() => setIsAddCompanyOpen(true)}>
            Add Company
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <BusinessIcon sx={{ fontSize: 40, color: 'primary.main' }} />
                <Box>
                  <Typography variant="h3" component="div">
                    {isLoading ? <Skeleton width={60} /> : summary?.companies_count || 0}
                  </Typography>
                  <Typography color="text.secondary">Companies</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <FolderIcon sx={{ fontSize: 40, color: 'success.main' }} />
                <Box>
                  <Typography variant="h3" component="div">
                    {isLoading ? <Skeleton width={60} /> : summary?.projects_count || 0}
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
                <PersonAddIcon sx={{ fontSize: 40, color: 'warning.main' }} />
                <Box>
                  <Typography variant="h3" component="div">
                    {isLoading ? <Skeleton width={60} /> : summary?.pending_tasks_count || 0}
                  </Typography>
                  <Typography color="text.secondary">Pending Tasks</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} sx={{ mb: 2 }}>
            <Tab icon={<BusinessIcon />} iconPosition="start" label="Companies" />
            <Tab icon={<DomainIcon />} iconPosition="start" label="Entity Directory" />
            {isSystemAdmin && <Tab icon={<PeopleIcon />} iconPosition="start" label="Portfolio Members" />}
          </Tabs>

          {activeTab === 0 && (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Company Name</TableCell>
                    <TableCell align="center">Projects</TableCell>
                    <TableCell>Access Source</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {isLoading ? (
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
                  ) : companies.length > 0 ? (
                    companies.map(company => (
                      <TableRow
                        key={company.company_id}
                        hover
                        sx={{ cursor: 'pointer' }}
                        onClick={() => navigate(`/portfolio-admin/companies/${company.company_id}`)}
                      >
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <BusinessIcon fontSize="small" color="action" />
                            {company.company_name}
                          </Box>
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            size="small"
                            label={`${company.project_count} project${company.project_count !== 1 ? 's' : ''}`}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={company.access_source}
                            color={company.access_source === 'membership' ? 'primary' : 'default'}
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
                          No companies found. Add your first company to get started.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {activeTab === 1 && companies.length > 0 && <EntityDirectoryTab portfolioId={companies[0].company_id} />}

          {activeTab === 1 && companies.length === 0 && (
            <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
              Add a company first to manage the entity directory.
            </Typography>
          )}

          {activeTab === 2 && isSystemAdmin && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                Portfolio members have access to all companies and projects within their assigned portfolio hub(s).
                Manage access carefully.
              </Alert>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Email</TableCell>
                      <TableCell>Portfolio Hub</TableCell>
                      <TableCell>Role</TableCell>
                      <TableCell>Status</TableCell>
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
                            <Skeleton width={100} />
                          </TableCell>
                          <TableCell>
                            <Skeleton width={80} />
                          </TableCell>
                          <TableCell>
                            <Skeleton width={60} />
                          </TableCell>
                          <TableCell>
                            <Skeleton width={40} />
                          </TableCell>
                        </TableRow>
                      ))
                    ) : portfolioMembers.length > 0 ? (
                      portfolioMembers.map(member => (
                        <TableRow key={member.access_id}>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <PeopleIcon fontSize="small" color="action" />
                              {member.first_name} {member.last_name}
                            </Box>
                          </TableCell>
                          <TableCell>{member.email}</TableCell>
                          <TableCell>
                            {member.portfolio_hub_company_name ? (
                              <Chip size="small" label={member.portfolio_hub_company_name} variant="outlined" />
                            ) : (
                              <Typography variant="body2" color="text.secondary">
                                Unassigned
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={
                                member.role === 'company_admin'
                                  ? 'Admin'
                                  : member.role === 'contributor'
                                    ? 'Contributor'
                                    : 'Read Only'
                              }
                              color={member.role === 'company_admin' ? 'primary' : 'default'}
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={member.status}
                              color={
                                member.status === 'active'
                                  ? 'success'
                                  : member.status === 'invited'
                                    ? 'warning'
                                    : 'error'
                              }
                            />
                          </TableCell>
                          <TableCell align="right">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => setRemoveMemberDialog({ open: true, member })}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} align="center">
                          <Typography color="text.secondary" sx={{ py: 3 }}>
                            No portfolio-level users. Click Add User to grant access to a portfolio hub.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={removeMemberDialog.open} onClose={() => setRemoveMemberDialog({ open: false, member: null })}>
        <DialogTitle>Remove Portfolio Member</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to remove{' '}
            <strong>
              {removeMemberDialog.member?.first_name} {removeMemberDialog.member?.last_name}
            </strong>{' '}
            from portfolio-level access?
          </Typography>
          <Alert severity="info" sx={{ mt: 2 }}>
            This will only remove their portfolio-level access. Any direct company or project memberships will be
            preserved.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRemoveMemberDialog({ open: false, member: null })}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            onClick={() =>
              removeMemberDialog.member && removeMemberMutation.mutate(removeMemberDialog.member.access_id)
            }
            disabled={removeMemberMutation.isPending}
          >
            {removeMemberMutation.isPending ? 'Removing...' : 'Remove'}
          </Button>
        </DialogActions>
      </Dialog>

      <AddCompanyDialog open={isAddCompanyOpen} onClose={() => setIsAddCompanyOpen(false)} />

      <AddUserDialog open={isAddUserOpen} onClose={() => setIsAddUserOpen(false)} level="portfolio" />
    </Box>
  );
};

export default PortfolioLevelPage;
