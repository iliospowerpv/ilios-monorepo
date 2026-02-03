import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

import { ApiClient } from '../../../../api';
import type { CompanyMember, ProjectMember } from '../../../../api';
import { useNotify } from '../../../../contexts/notifications/notifications';

export type AccessLevel = 'company' | 'project' | 'portfolio';

interface RemoveUserDialogProps {
  open: boolean;
  onClose: () => void;
  level: AccessLevel;
  entityId: number;
  entityName?: string;
  member: CompanyMember | ProjectMember | null;
  onSuccess?: () => void;
}

export const RemoveUserDialog: React.FC<RemoveUserDialogProps> = ({
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

  const removeMemberMutation = useMutation({
    mutationFn: async () => {
      if (!member) throw new Error('No member selected');

      if (level === 'company') {
        return ApiClient.workspace.removeCompanyMember(entityId, (member as CompanyMember).membership_id);
      } else if (level === 'project') {
        const projectMember = member as ProjectMember;
        if (!projectMember.membership_id) {
          throw new Error('Cannot remove inherited access - user must be removed from the company or portfolio level');
        }
        return ApiClient.workspace.removeProjectMember(entityId, projectMember.membership_id);
      } else if (level === 'portfolio') {
        return ApiClient.workspace.removePortfolioMember((member as any).access_id);
      }
      throw new Error('Unsupported level for removal');
    },
    onSuccess: () => {
      if (level === 'company') {
        queryClient.invalidateQueries({ queryKey: ['companyMembers', entityId] });
      } else if (level === 'project') {
        queryClient.invalidateQueries({ queryKey: ['projectMembers', entityId] });
      } else if (level === 'portfolio') {
        queryClient.invalidateQueries({ queryKey: ['portfolioMembers'] });
      }
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      notify('User removed successfully');
      handleClose();
      onSuccess?.();
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || err.response?.data?.message || 'Failed to remove user');
    }
  });

  const handleConfirm = () => {
    if (!member) {
      setError('No member selected');
      return;
    }
    removeMemberMutation.mutate();
  };

  const handleClose = () => {
    setError(null);
    onClose();
  };

  const memberName = member ? `${member.first_name} ${member.last_name}` : '';
  const levelLabel =
    level === 'company'
      ? entityName || 'this company'
      : level === 'project'
        ? entityName || 'this project'
        : 'the portfolio';

  const isInheritedAccess =
    level === 'project' && member && (member as ProjectMember).access_source !== 'direct_project' ? true : false;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Remove User Access</DialogTitle>
      <DialogContent>
        <Alert severity="warning" icon={<WarningAmberIcon />} sx={{ mb: 3, mt: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Confirm Removal
          </Typography>
          <Typography variant="body2">
            Are you sure you want to remove <strong>{memberName}</strong> from {levelLabel}? This action cannot be
            undone.
          </Typography>
        </Alert>

        {isInheritedAccess && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              This user has inherited access from a higher level (company or portfolio). You can only remove their
              direct project access here. To fully remove their access, update their permissions at the company or
              portfolio level.
            </Typography>
          </Alert>
        )}

        {member && (
          <Box sx={{ p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {memberName}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {member.email}
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={removeMemberMutation.isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={handleConfirm}
          disabled={removeMemberMutation.isPending || isInheritedAccess}
          startIcon={removeMemberMutation.isPending ? <CircularProgress size={16} /> : null}
        >
          {removeMemberMutation.isPending ? 'Removing...' : 'Remove User'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RemoveUserDialog;
