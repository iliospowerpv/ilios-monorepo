import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Autocomplete from '@mui/material/Autocomplete';
import { SearchableSelect } from '../../../../../components/common/SearchableSelect/SearchableSelect';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';

import { ApiClient } from '../../../../../api';

interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
}

interface AddMemberDialogProps {
  open: boolean;
  onClose: () => void;
  onAdd: (userId: number, role: string) => void;
  isAdding: boolean;
}

export const AddMemberDialog: React.FC<AddMemberDialogProps> = ({ open, onClose, onAdd, isAdding }) => {
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [role, setRole] = useState<string>('contributor');

  const { data: users, isLoading: isLoadingUsers } = useQuery({
    queryKey: ['allUsers'],
    queryFn: async () => {
      const response = await ApiClient.user.users({ skip: 0, limit: 1000 });
      return response.items as User[];
    },
    enabled: open
  });

  const handleAdd = () => {
    if (selectedUser) {
      onAdd(selectedUser.id, role);
      setSelectedUser(null);
      setRole('contributor');
    }
  };

  const handleClose = () => {
    setSelectedUser(null);
    setRole('contributor');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Member</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <Autocomplete
            options={users || []}
            getOptionLabel={user => `${user.first_name} ${user.last_name} (${user.email})`}
            value={selectedUser}
            onChange={(_, newValue) => setSelectedUser(newValue)}
            loading={isLoadingUsers}
            renderInput={params => (
              <TextField
                {...params}
                label="Select User"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {isLoadingUsers ? <CircularProgress size={20} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  )
                }}
              />
            )}
          />
          <SearchableSelect
            options={[
              { label: 'Company Admin', value: 'company_admin' },
              { label: 'Contributor', value: 'contributor' },
              { label: 'Read Only', value: 'read_only' }
            ]}
            value={role}
            onChange={val => setRole(val as string)}
            label="Role"
            disableClearable
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={isAdding}>
          Cancel
        </Button>
        <Button onClick={handleAdd} variant="contained" disabled={!selectedUser || isAdding}>
          {isAdding ? 'Adding...' : 'Add Member'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddMemberDialog;
