import React, { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import { SearchableSelect } from '../../../../components/common/SearchableSelect/SearchableSelect';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';


import { ApiClient } from '../../../../api';
import type { UpdateMemberRequest, CompanyMember, RoleProfile } from '../../../../api';
import { useNotify } from '../../../../contexts/notifications/notifications';

export type AccessLevel = 'company' | 'project';

interface EditUserDialogProps {
  open: boolean;
  onClose: () => void;
  level: AccessLevel;
  entityId: number;
  entityName?: string;
  member: CompanyMember | null;
  onSuccess?: () => void;
}

type RoleType = 'company_admin' | 'contributor' | 'read_only';

const ROLE_DESCRIPTIONS: Record<RoleType, string> = {
  company_admin: 'Full administrative access including user management and settings',
  contributor: 'Can view and edit data but cannot manage users or settings',
  read_only: 'Can only view data without making any changes'
};

export const EditUserDialog: React.FC<EditUserDialogProps> = ({
  open,
  onClose,
  level,
  entityId,
  entityName,
  member,
  onSuccess
}) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [error, setError] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<RoleType>('read_only');
  const [selectedRoleProfileKey, setSelectedRoleProfileKey] = useState<string | null>(null);

  const { data: roleProfiles, isLoading: isLoadingProfiles } = useQuery({
    queryKey: ['roleProfiles', entityId],
    queryFn: () => ApiClient.workspace.getRoleProfilesByCompany(entityId),
    enabled: open && level === 'company',
    staleTime: 5 * 60 * 1000
  });

  useEffect(() => {
    if (open && member) {
      setSelectedRole(member.role);
      setSelectedRoleProfileKey(member.role_profile_key || null);
    }
  }, [open, member]);

  const availableProfiles: RoleProfile[] = roleProfiles || [];

  const updateMemberMutation = useMutation({
    mutationFn: async (params: { role: RoleType; roleProfileKey?: string | null }) => {
      if (!member) throw new Error('No member selected');

      if (level === 'company') {
        const request: UpdateMemberRequest = {
          role: params.role,
          role_profile_key: params.roleProfileKey || undefined
        };
        return ApiClient.workspace.updateCompanyMember(entityId, member.membership_id, request);
      }
      throw new Error('Unsupported level for update');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companyMembers', entityId] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      notify('User updated successfully');
      handleClose();
      onSuccess?.();
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || err.response?.data?.message || 'Failed to update user');
    }
  });

  const handleSubmit = () => {
    if (!member) {
      setError('No member selected');
      return;
    }

    updateMemberMutation.mutate({
      role: selectedRole,
      roleProfileKey: selectedRoleProfileKey
    });
  };

  const handleClose = () => {
    setSelectedRole('read_only');
    setSelectedRoleProfileKey(null);
    setError(null);
    onClose();
  };

  const selectedProfile = availableProfiles.find(p => p.key === selectedRoleProfileKey);
  const memberName = member ? `${member.first_name} ${member.last_name}` : '';

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit User Access{entityName ? ` - ${entityName}` : ''}</DialogTitle>
      <DialogContent>
        {member && (
          <Box sx={{ mb: 3, mt: 1, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {memberName}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {member.email}
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <SearchableSelect
            options={[
              { label: 'Admin', value: 'company_admin' },
              { label: 'Contributor', value: 'contributor' },
              { label: 'Read Only', value: 'read_only' }
            ]}
            value={selectedRole}
            onChange={val => setSelectedRole(val as RoleType)}
            label="Role"
            helperText={ROLE_DESCRIPTIONS[selectedRole]}
            disableClearable
            fullWidth
          />

          {level === 'company' && (
            <SearchableSelect
              options={[
                { label: 'None - Use base role only', value: '' },
                ...availableProfiles.map(profile => ({
                  label: profile.label,
                  value: profile.key
                }))
              ]}
              value={selectedRoleProfileKey || ''}
              onChange={val => setSelectedRoleProfileKey((val as string) || null)}
              label="Role Profile (Optional)"
              helperText={selectedProfile ? selectedProfile.description : (!selectedRoleProfileKey ? 'Optionally assign a role profile for specialized module access' : undefined)}
              disabled={isLoadingProfiles}
              disableClearable
              fullWidth
            />
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={updateMemberMutation.isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={updateMemberMutation.isPending}
          startIcon={updateMemberMutation.isPending ? <CircularProgress size={16} /> : null}
        >
          {updateMemberMutation.isPending ? 'Saving...' : 'Save Changes'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EditUserDialog;
