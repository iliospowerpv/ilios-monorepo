import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import { SearchableSelect } from '../../../../components/common/SearchableSelect/SearchableSelect';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Chip from '@mui/material/Chip';
import Collapse from '@mui/material/Collapse';
import Checkbox from '@mui/material/Checkbox';
import ListItemText from '@mui/material/ListItemText';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

import { ApiClient } from '../../../../api';
import { useAccess } from '../../../../hooks/access/access';
import { SelectOrCreateUser } from '../../../../components/forms/SelectOrCreate';

interface InviteStepProps {
  companyId: number;
  companyName: string;
  projectId: number;
  projectName: string;
  invitedEmails: string[];
  onInviteSuccess: (email: string) => void;
  onComplete: () => void;
  onBack: () => void;
}

interface Project {
  id: number;
  name: string;
}

type RoleType = 'company_admin' | 'contributor' | 'read_only';

export const InviteStep: React.FC<InviteStepProps> = ({
  companyId,
  companyName,
  projectId,
  projectName,
  invitedEmails,
  onInviteSuccess,
  onComplete,
  onBack
}) => {
  const queryClient = useQueryClient();
  const { isSystemUser, isCompanyAdminFull } = useAccess(companyId);
  const canInvite = isSystemUser || isCompanyAdminFull;

  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [role, setRole] = useState<RoleType>('contributor');
  const [selectedProjects, setSelectedProjects] = useState<number[]>([projectId]);
  const [showProjectAssignment, setShowProjectAssignment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [lastInvitedEmail, setLastInvitedEmail] = useState<string | null>(null);

  const { data: projectsData } = useQuery({
    queryKey: ['onboarding-company-projects', companyId],
    queryFn: () => ApiClient.assetManagement.sites({ skip: 0, limit: 100 })
  });

  const { data: companyMembers } = useQuery({
    queryKey: ['company-members', companyId],
    queryFn: () => ApiClient.workspace.getCompanyMembers(companyId),
    enabled: !!companyId
  });

  const existingMemberUserIds = (companyMembers || []).map((m: { user_id: number }) => m.user_id);

  const projects: Project[] = (projectsData?.items ?? [])
    .filter((site: { company_id?: number }) => site.company_id === companyId)
    .map((site: { id: number; name: string }) => ({
      id: site.id,
      name: site.name
    }));

  const inviteMutation = useMutation({
    mutationFn: async () => {
      if (!selectedUserId) throw new Error('User is required');

      await ApiClient.workspace.addCompanyMember(companyId, {
        user_id: selectedUserId,
        company_id: companyId,
        role
      });

      return selectedUserId;
    },
    onSuccess: () => {
      setSuccessMessage(`User has been added to ${companyName}`);
      if (lastInvitedEmail) {
        onInviteSuccess(lastInvitedEmail);
      }
      setSelectedUserId(null);
      setRole('contributor');
      setLastInvitedEmail(null);
      queryClient.invalidateQueries({ queryKey: ['company-members', companyId] });
      setTimeout(() => setSuccessMessage(null), 3000);
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (detail?.message) {
        setError(detail.message);
      } else {
        setError(err.message || 'Failed to add user to company');
      }
    }
  });

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) {
      setError('Please select a user');
      return;
    }
    setError(null);
    inviteMutation.mutate();
  };

  const handleProjectChange = (newIds: number[]) => {
    setSelectedProjects(newIds);
  };

  return (
    <Box>
      <Card variant="outlined" sx={{ mb: 3, bgcolor: 'action.hover' }}>
        <CardContent sx={{ py: 1.5 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Inviting users to:
              </Typography>
              <Typography variant="subtitle1" fontWeight={600}>
                {companyName} / {projectName}
              </Typography>
            </Box>
            {invitedEmails.length > 0 && (
              <Chip icon={<CheckCircleIcon />} label={`${invitedEmails.length} invited`} color="success" size="small" />
            )}
          </Box>
        </CardContent>
      </Card>

      <Alert severity="info" sx={{ mb: 3 }}>
        This step is optional. You can skip it and invite users later from Portfolio Admin.
      </Alert>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {successMessage && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {successMessage}
        </Alert>
      )}

      {canInvite ? (
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Add User to Company
            </Typography>
            <form onSubmit={handleInvite}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <SelectOrCreateUser
                  value={selectedUserId}
                  onChange={setSelectedUserId}
                  canCreate={canInvite}
                  defaultCompanyId={companyId}
                  label="Select User"
                  excludeUserIds={existingMemberUserIds}
                />

                <SearchableSelect
                  options={[
                    { label: 'Admin', value: 'company_admin' },
                    { label: 'Contributor', value: 'contributor' },
                    { label: 'Read Only', value: 'read_only' }
                  ]}
                  value={role}
                  onChange={val => setRole(val as RoleType)}
                  label="Role"
                  disableClearable
                />

                {projects.length > 1 && (
                  <Box>
                    <Button
                      onClick={() => setShowProjectAssignment(!showProjectAssignment)}
                      endIcon={showProjectAssignment ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      sx={{ textTransform: 'none' }}
                    >
                      Assign Projects (Optional)
                    </Button>
                    <Collapse in={showProjectAssignment}>
                      <Box sx={{ pl: 2, pt: 1 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                          Optionally assign the user to specific projects
                        </Typography>
                        <Autocomplete
                          multiple
                          size="small"
                          options={projects}
                          getOptionLabel={option => option.name}
                          value={projects.filter(p => selectedProjects.includes(p.id))}
                          onChange={(_event, newValue) => handleProjectChange(newValue.map(v => v.id))}
                          disableCloseOnSelect
                          renderOption={(props, option, { selected }) => (
                            <li {...props}>
                              <Checkbox checked={selected} sx={{ mr: 1 }} />
                              <ListItemText primary={option.name} />
                            </li>
                          )}
                          renderTags={(value, getTagProps) =>
                            value.map((option, index) => (
                              <Chip {...getTagProps({ index })} key={option.id} label={option.name} size="small" />
                            ))
                          }
                          renderInput={params => <TextField {...params} label="Select Projects" />}
                          fullWidth
                        />
                      </Box>
                    </Collapse>
                  </Box>
                )}

                <Button
                  type="submit"
                  variant="contained"
                  disabled={inviteMutation.isPending || !selectedUserId}
                  startIcon={inviteMutation.isPending ? <CircularProgress size={16} /> : <PersonAddIcon />}
                >
                  Add User
                </Button>
              </Box>
            </form>
          </CardContent>
        </Card>
      ) : (
        <Alert severity="warning" sx={{ mb: 3 }}>
          You do not have permission to invite users. Only system administrators and company admins can add users.
        </Alert>
      )}

      {invitedEmails.length > 0 && (
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Users Added This Session
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {invitedEmails.map(email => (
                <Chip key={email} label={email} size="small" color="success" variant="outlined" />
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={onBack}>
          Back to Project
        </Button>
        <Button variant="contained" endIcon={<SkipNextIcon />} onClick={onComplete}>
          {invitedEmails.length > 0 ? 'Finish Setup' : 'Skip & Finish'}
        </Button>
      </Box>
    </Box>
  );
};

export default InviteStep;
