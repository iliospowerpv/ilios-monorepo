import React, { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import { SearchableSelect } from '../../../../../components/common/SearchableSelect/SearchableSelect';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Checkbox from '@mui/material/Checkbox';
import ListItemText from '@mui/material/ListItemText';
import Collapse from '@mui/material/Collapse';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import Snackbar from '@mui/material/Snackbar';

import { ApiClient } from '../../../../../api';
import { useEntityContext } from '../../../../../contexts/entityContext/entityContext';
import { SelectOrCreateUser } from '../../../../../components/forms/SelectOrCreate';
import { useAccess } from '../../../../../hooks/access/access';

interface InviteUserDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface Project {
  id: number;
  name: string;
}

type RoleType = 'company_admin' | 'contributor' | 'read_only';

export const InviteUserDialog: React.FC<InviteUserDialogProps> = ({ open, onClose, onSuccess }) => {
  const { currentCompany } = useEntityContext();
  const [companyId, setCompanyId] = useState<number | ''>('');
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [role, setRole] = useState<RoleType>('contributor');
  const [selectedProjects, setSelectedProjects] = useState<number[]>([]);
  const [showProjectAssignment, setShowProjectAssignment] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { isSystemUser, isCompanyAdminFull } = useAccess(companyId || undefined);
  const canCreateUsers = isSystemUser || isCompanyAdminFull;

  const { data: companiesData } = useQuery({
    queryKey: ['invite-accessible-companies'],
    queryFn: () => ApiClient.workspace.getWorkspace(),
    enabled: open
  });

  const { data: projectsData } = useQuery({
    queryKey: ['invite-company-projects', companyId],
    queryFn: async () => {
      if (!companyId) return { items: [] };
      const response = await ApiClient.assetManagement.sites({ skip: 0, limit: 100 });
      return response;
    },
    enabled: open && !!companyId
  });

  useEffect(() => {
    if (open && currentCompany) {
      setCompanyId(currentCompany.id);
    }
  }, [open, currentCompany]);

  useEffect(() => {
    setSelectedProjects([]);
    setShowProjectAssignment(false);
  }, [companyId]);

  const inviteMutation = useMutation({
    mutationFn: async () => {
      if (!companyId || !selectedUserId) throw new Error('Company and user are required');

      const response = await ApiClient.workspace.addCompanyMember(companyId as number, {
        user_id: selectedUserId,
        company_id: companyId as number,
        role
      });

      return response;
    },
    onSuccess: () => {
      setSuccessMessage('User has been added to the company');
      resetForm();
      onSuccess();
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to add user to company');
    }
  });

  const resetForm = () => {
    setCompanyId(currentCompany?.id ?? '');
    setSelectedUserId(null);
    setRole('contributor');
    setSelectedProjects([]);
    setShowProjectAssignment(false);
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyId) {
      setError('Please select a company');
      return;
    }
    if (!selectedUserId) {
      setError('Please select a user');
      return;
    }
    setError(null);
    inviteMutation.mutate();
  };

  const companies = companiesData?.companies ?? [];
  const projects: Project[] = (projectsData?.items ?? []).map((site: { id: number; name: string }) => ({
    id: site.id,
    name: site.name
  }));

  const handleProjectChange = (newIds: number[]) => {
    setSelectedProjects(newIds);
  };

  return (
    <>
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <form onSubmit={handleSubmit}>
          <DialogTitle>Add User to Company</DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
              {error && <Alert severity="error">{error}</Alert>}

              <SearchableSelect
                options={companies.map(company => ({
                  label: company.company_name,
                  value: company.company_id
                }))}
                value={companyId || null}
                onChange={val => setCompanyId(val as number)}
                label="Company"
                required
              />

              <SelectOrCreateUser
                value={selectedUserId}
                onChange={setSelectedUserId}
                canCreate={canCreateUsers}
                defaultCompanyId={companyId ? (companyId as number) : undefined}
                label="Select User"
                required
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

              {projects.length > 0 && (
                <Box>
                  <Button
                    onClick={() => setShowProjectAssignment(!showProjectAssignment)}
                    endIcon={showProjectAssignment ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    sx={{ mb: 1, textTransform: 'none' }}
                  >
                    Assign Projects (Optional)
                  </Button>
                  <Collapse in={showProjectAssignment}>
                    <Box sx={{ pl: 2 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                        Optionally assign the user to specific projects within this company
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
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose} disabled={inviteMutation.isPending}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={inviteMutation.isPending || !companyId || !selectedUserId}
              startIcon={inviteMutation.isPending ? <CircularProgress size={16} /> : null}
            >
              Add User
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <Snackbar
        open={!!successMessage}
        autoHideDuration={4000}
        onClose={() => setSuccessMessage(null)}
        message={successMessage}
      />
    </>
  );
};

export default InviteUserDialog;
