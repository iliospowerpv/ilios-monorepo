import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';

import { ApiClient } from '../../../../../api';
import { useEntityContext } from '../../../../../contexts/entityContext/entityContext';

interface CreateCompanyDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateCompanyDialog: React.FC<CreateCompanyDialogProps> = ({ open, onClose, onSuccess }) => {
  const navigate = useNavigate();
  const { setCurrentCompany } = useEntityContext();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      ApiClient.companies.create({
        company_type: 'owner',
        name,
        email: email || null,
        phone: phone || null,
        address: address || null
      }),
    onSuccess: response => {
      const newCompanyId = (response as unknown as { id?: number }).id;
      if (newCompanyId) {
        setCurrentCompany({ id: newCompanyId, name });
        navigate(`/companies/${newCompanyId}`);
      }
      resetForm();
      onSuccess();
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create company');
    }
  });

  const resetForm = () => {
    setName('');
    setEmail('');
    setPhone('');
    setAddress('');
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Company name is required');
      return;
    }
    setError(null);
    createMutation.mutate();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>Create Company</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}

            <TextField
              label="Company Name"
              value={name}
              onChange={e => setName(e.target.value)}
              required
              fullWidth
              autoFocus
            />

            <TextField label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} fullWidth />

            <TextField label="Phone" value={phone} onChange={e => setPhone(e.target.value)} fullWidth />

            <TextField
              label="Address"
              value={address}
              onChange={e => setAddress(e.target.value)}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={createMutation.isPending || !name.trim()}
            startIcon={createMutation.isPending ? <CircularProgress size={16} /> : null}
          >
            Create Company
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default CreateCompanyDialog;
