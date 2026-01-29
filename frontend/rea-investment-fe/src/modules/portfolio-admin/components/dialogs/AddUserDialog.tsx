import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import InfoIcon from '@mui/icons-material/Info';

import { ApiClient } from '../../../../api';
import type { AddMemberRequest, AddPortfolioMemberRequest, AddProjectMemberRequest } from '../../../../api';
import { useNotify } from '../../../../contexts/notifications/notifications';
import { SelectOrCreateUser } from '../../../../components/forms/SelectOrCreate';

export type AccessLevel = 'portfolio' | 'company' | 'project';

interface AddUserDialogProps {
  open: boolean;
  onClose: () => void;
  level: AccessLevel;
  entityId?: number;
  entityName?: string;
  parentCompanyId?: number;
  onSuccess?: () => void;
}

type RoleType = 'company_admin' | 'contributor' | 'read_only';

interface AccessLevelInfo {
  title: string;
  description: string;
  severity: 'warning' | 'info';
  supported: boolean;
  unsupportedMessage?: string;
}

const ACCESS_LEVEL_INFO: Record<AccessLevel, AccessLevelInfo> = {
  portfolio: {
    title: 'Portfolio-Level Access',
    description:
      'This user will have access to ALL companies and ALL projects in the portfolio. Only grant this level to users who need visibility across the entire organization.',
    severity: 'warning',
    supported: true
  },
  company: {
    title: 'Company-Level Access',
    description:
      'This user will have access to ALL projects within this company. They will be able to view and interact with all project data under this company.',
    severity: 'warning',
    supported: true
  },
  project: {
    title: 'Project-Level Access',
    description: 'This user will only have access to this specific project. This is the most restricted access level.',
    severity: 'info',
    supported: true
  }
};

const ROLE_DESCRIPTIONS: Record<RoleType, string> = {
  company_admin: 'Full administrative access including user management and settings',
  contributor: 'Can view and edit data but cannot manage users or settings',
  read_only: 'Can only view data without making any changes'
};

export const AddUserDialog: React.FC<AddUserDialogProps> = ({
  open,
  onClose,
  level,
  entityId,
  entityName,
  parentCompanyId,
  onSuccess
}) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [error, setError] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedRole, setSelectedRole] = useState<RoleType>('read_only');
  const [confirmAccess, setConfirmAccess] = useState(false);
  const [selectedCompanyForCreate, setSelectedCompanyForCreate] = useState<number | null>(null);

  const { data: workspace } = useQuery({
    queryKey: ['workspace'],
    queryFn: () => ApiClient.workspace.getWorkspace(),
    enabled: level === 'portfolio',
    staleTime: 5 * 60 * 1000
  });

  const companies = workspace?.companies || [];

  const getDefaultCompanyId = (): number | undefined => {
    if (level === 'company' && entityId) {
      return entityId;
    }
    if (level === 'project' && parentCompanyId) {
      return parentCompanyId;
    }
    if (level === 'portfolio' && selectedCompanyForCreate) {
      return selectedCompanyForCreate;
    }
    return undefined;
  };

  const addMemberMutation = useMutation({
    mutationFn: async (params: { userId: number; role: RoleType }) => {
      if (level === 'portfolio') {
        const request: AddPortfolioMemberRequest = {
          user_id: params.userId,
          role: params.role
        };
        return ApiClient.workspace.addPortfolioMember(request);
      } else if (level === 'company' && entityId) {
        const request: AddMemberRequest = {
          user_id: params.userId,
          company_id: entityId,
          role: params.role
        };
        return ApiClient.workspace.addCompanyMember(entityId, request);
      } else if (level === 'project' && entityId) {
        const projectRole = params.role === 'company_admin' ? 'project_admin' : params.role;
        const request: AddProjectMemberRequest = {
          user_id: params.userId,
          role: projectRole as 'project_admin' | 'contributor' | 'read_only'
        };
        return ApiClient.workspace.addProjectMember(entityId, request);
      }
      throw new Error('Unsupported level for add member');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companyMembers'] });
      queryClient.invalidateQueries({ queryKey: ['portfolioMembers'] });
      queryClient.invalidateQueries({ queryKey: ['projectMembers'] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      notify('User added successfully');
      handleClose();
      onSuccess?.();
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || err.response?.data?.message || 'Failed to add user');
    }
  });

  const handleSubmit = () => {
    if (!selectedUserId) {
      setError('Please select a user');
      return;
    }

    if (!ACCESS_LEVEL_INFO[level].supported) {
      setError(ACCESS_LEVEL_INFO[level].unsupportedMessage || 'This feature is not yet available.');
      return;
    }

    addMemberMutation.mutate({
      userId: selectedUserId,
      role: selectedRole
    });
  };

  const levelInfo = ACCESS_LEVEL_INFO[level];
  const isSupported = levelInfo.supported;

  const handleClose = () => {
    setSelectedUserId(null);
    setSelectedRole('read_only');
    setConfirmAccess(false);
    setSelectedCompanyForCreate(null);
    setError(null);
    onClose();
  };

  const levelLabel =
    level === 'portfolio' ? 'Portfolio' : level === 'company' ? entityName || 'Company' : entityName || 'Project';

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add User to {levelLabel}</DialogTitle>
      <DialogContent>
        {!isSupported && (
          <Alert severity="warning" icon={<WarningAmberIcon />} sx={{ mb: 3, mt: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
              Coming Soon
            </Typography>
            <Typography variant="body2">{levelInfo.unsupportedMessage}</Typography>
          </Alert>
        )}

        {isSupported && (
          <Alert
            severity={levelInfo.severity}
            icon={levelInfo.severity === 'warning' ? <WarningAmberIcon /> : <InfoIcon />}
            sx={{ mb: 3, mt: 1 }}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
              {levelInfo.title}
            </Typography>
            <Typography variant="body2">{levelInfo.description}</Typography>
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {isSupported && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {level === 'portfolio' && (
              <FormControl fullWidth size="small">
                <InputLabel>Company for New User</InputLabel>
                <Select
                  value={selectedCompanyForCreate ? String(selectedCompanyForCreate) : ''}
                  onChange={e => setSelectedCompanyForCreate(Number(e.target.value) || null)}
                  label="Company for New User"
                  disabled={companies.length === 0}
                >
                  <MenuItem value="">
                    <em>
                      {companies.length === 0 ? 'Loading companies...' : 'Select a company to enable user creation'}
                    </em>
                  </MenuItem>
                  {companies.map(c => (
                    <MenuItem key={c.company_id} value={String(c.company_id)}>
                      {c.company_name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            {level === 'project' && !parentCompanyId && (
              <Alert severity="warning" sx={{ py: 1 }}>
                Unable to determine parent company for this project. User creation is disabled.
              </Alert>
            )}

            <SelectOrCreateUser
              value={selectedUserId}
              onChange={setSelectedUserId}
              canCreate={true}
              defaultCompanyId={getDefaultCompanyId()}
              label="Select User"
              required
            />

            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select value={selectedRole} onChange={e => setSelectedRole(e.target.value as RoleType)} label="Role">
                <MenuItem value="company_admin">Admin</MenuItem>
                <MenuItem value="contributor">Contributor</MenuItem>
                <MenuItem value="read_only">Read Only</MenuItem>
              </Select>
            </FormControl>

            <Alert severity="info" icon={<InfoIcon />}>
              <Typography variant="body2">
                <strong>
                  {selectedRole === 'company_admin'
                    ? 'Admin'
                    : selectedRole === 'contributor'
                      ? 'Contributor'
                      : 'Read Only'}
                  :
                </strong>{' '}
                {ROLE_DESCRIPTIONS[selectedRole]}
              </Typography>
            </Alert>

            {level !== 'project' && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <input
                  type="checkbox"
                  id="confirm-access"
                  checked={confirmAccess}
                  onChange={e => setConfirmAccess(e.target.checked)}
                />
                <label htmlFor="confirm-access">
                  <Typography variant="body2">
                    I understand that this user will have access to{' '}
                    {level === 'portfolio' ? 'all companies and projects' : 'all projects in this company'}
                  </Typography>
                </label>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={addMemberMutation.isPending}>
          {isSupported ? 'Cancel' : 'Close'}
        </Button>
        {isSupported && (
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={!selectedUserId || addMemberMutation.isPending || (level !== 'project' && !confirmAccess)}
            startIcon={addMemberMutation.isPending ? <CircularProgress size={16} /> : null}
          >
            {addMemberMutation.isPending ? 'Adding...' : 'Add User'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default AddUserDialog;
