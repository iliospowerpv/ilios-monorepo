import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import Skeleton from '@mui/material/Skeleton';
import { SearchableSelect } from '../../../../components/common/SearchableSelect/SearchableSelect';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import DeleteIcon from '@mui/icons-material/Delete';
import BusinessIcon from '@mui/icons-material/Business';

import { ApiClient } from '../../../../api';
import type { AddMemberRequest, UpdateMemberRequest } from '../../../../api';
import { useEntityContext } from '../../../../contexts/entityContext/entityContext';
import { AddMemberDialog } from './components';

const getStatusColor = (status: string): 'success' | 'warning' | 'error' => {
  switch (status) {
    case 'active':
      return 'success';
    case 'invited':
      return 'warning';
    case 'disabled':
      return 'error';
    default:
      return 'warning';
  }
};

export const CompanyAdminPage: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { currentCompany } = useEntityContext();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  const companyId = useMemo(() => currentCompany?.id ?? 0, [currentCompany]);
  const companyName = useMemo(() => currentCompany?.name ?? '', [currentCompany]);

  const {
    data: members,
    isLoading,
    error
  } = useQuery({
    queryKey: ['companyMembers', companyId],
    queryFn: () => ApiClient.workspace.getCompanyMembers(companyId),
    enabled: companyId > 0,
    staleTime: 5 * 60 * 1000
  });

  const addMemberMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: string }) => {
      const request: AddMemberRequest = {
        user_id: userId,
        company_id: companyId,
        role: role as 'company_admin' | 'contributor' | 'read_only'
      };
      return ApiClient.workspace.addCompanyMember(companyId, request);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companyMembers', companyId] });
      setIsAddDialogOpen(false);
    }
  });

  const updateMemberMutation = useMutation({
    mutationFn: ({ membershipId, role }: { membershipId: number; role: string }) => {
      const request: UpdateMemberRequest = {
        role: role as 'company_admin' | 'contributor' | 'read_only'
      };
      return ApiClient.workspace.updateCompanyMember(companyId, membershipId, request);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companyMembers', companyId] });
    }
  });

  const removeMemberMutation = useMutation({
    mutationFn: ({ membershipId }: { membershipId: number }) =>
      ApiClient.workspace.removeCompanyMember(companyId, membershipId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companyMembers', companyId] });
    }
  });

  const handleAddMember = (userId: number, role: string) => {
    addMemberMutation.mutate({ userId, role });
  };

  const handleRoleChange = (membershipId: number, newRole: string) => {
    updateMemberMutation.mutate({ membershipId, role: newRole });
  };

  const handleRemoveMember = (membershipId: number, userName: string) => {
    if (window.confirm(`Are you sure you want to remove ${userName} from this company?`)) {
      removeMemberMutation.mutate({ membershipId });
    }
  };

  if (!currentCompany) {
    return (
      <Box sx={{ p: 3 }}>
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <BusinessIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              No Company Selected
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 3 }}>
              Please select a company to manage its members.
            </Typography>
            <Button variant="contained" onClick={() => navigate('/workspace')}>
              Go to Workspace
            </Button>
          </CardContent>
        </Card>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load company members. You may not have permission to view this page.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Portfolio Admin
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Managing members for {companyName}
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<PersonAddIcon />} onClick={() => setIsAddDialogOpen(true)}>
          Add Member
        </Button>
      </Box>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Company Members
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>User</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Status</TableCell>
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
                        <Skeleton width={120} />
                      </TableCell>
                      <TableCell>
                        <Skeleton width={80} />
                      </TableCell>
                      <TableCell>
                        <Skeleton width={40} />
                      </TableCell>
                    </TableRow>
                  ))
                ) : members && members.length > 0 ? (
                  members.map(member => (
                    <TableRow key={member.membership_id}>
                      <TableCell>
                        {member.first_name} {member.last_name}
                      </TableCell>
                      <TableCell>{member.email}</TableCell>
                      <TableCell>
                        <SearchableSelect
                          options={[
                            { label: 'Admin', value: 'company_admin' },
                            { label: 'Contributor', value: 'contributor' },
                            { label: 'Read Only', value: 'read_only' }
                          ]}
                          value={member.role}
                          onChange={val => handleRoleChange(member.membership_id, val as string)}
                          disabled={updateMemberMutation.isPending}
                          size="small"
                          sx={{ minWidth: 120 }}
                          disableClearable
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={member.status}
                          color={getStatusColor(member.status)}
                          variant="filled"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() =>
                            handleRemoveMember(member.membership_id, `${member.first_name} ${member.last_name}`)
                          }
                          disabled={removeMemberMutation.isPending}
                          title="Remove member"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary" sx={{ py: 2 }}>
                        No members found for this company.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <AddMemberDialog
        open={isAddDialogOpen}
        onClose={() => setIsAddDialogOpen(false)}
        onAdd={handleAddMember}
        isAdding={addMemberMutation.isPending}
      />
    </Box>
  );
};

export default CompanyAdminPage;
