import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';

import { ApiClient } from '../../../../../api';
import { COMPANY_TYPES } from '../../../../../constants';
import { US_STATES } from '../../../../../constants/usStates';

interface CreateCompanyDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateCompanyDialog: React.FC<CreateCompanyDialogProps> = ({ open, onClose, onSuccess }) => {
  const queryClient = useQueryClient();
  const [companyType, setCompanyType] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [county, setCounty] = useState('');
  const [zipCode, setZipCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      ApiClient.companies.create({
        company_type: companyType,
        name,
        address,
        city,
        state,
        county: county || null,
        zip_code: zipCode,
        email: email || null,
        phone: phone ? normalizePhone(phone) : null
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['accessible-entities'] });
      resetForm();
      onSuccess();
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create company');
    }
  });

  const normalizePhone = (val: string): string => val.replace(/\D/g, '').replace(/^1(\d{10})$/, '$1');

  const resetForm = () => {
    setCompanyType('');
    setName('');
    setEmail('');
    setPhone('');
    setAddress('');
    setCity('');
    setState('');
    setCounty('');
    setZipCode('');
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyType) {
      setError('Company type is required');
      return;
    }
    if (!name.trim()) {
      setError('Company name is required');
      return;
    }
    if (!address.trim()) {
      setError('Address is required');
      return;
    }
    if (!city.trim()) {
      setError('City is required');
      return;
    }
    if (!state) {
      setError('State is required');
      return;
    }
    if (!/^[0-9]{5}$/.test(zipCode)) {
      setError('Zip code must be exactly 5 digits');
      return;
    }
    if (phone && normalizePhone(phone).length !== 10) {
      setError('Phone number must contain exactly 10 digits');
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

            <FormControl required fullWidth>
              <InputLabel>Company Type</InputLabel>
              <Select value={companyType} onChange={e => setCompanyType(e.target.value as string)} label="Company Type">
                {COMPANY_TYPES.map(type => (
                  <MenuItem key={type} value={type}>
                    {type}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Company Name"
              value={name}
              onChange={e => setName(e.target.value)}
              required
              fullWidth
              autoFocus
            />

            <TextField
              label="Address"
              value={address}
              onChange={e => setAddress(e.target.value)}
              required
              fullWidth
              inputProps={{ maxLength: 255 }}
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="City"
                value={city}
                onChange={e => setCity(e.target.value)}
                required
                fullWidth
                inputProps={{ maxLength: 100 }}
              />
              <FormControl required sx={{ minWidth: 120 }}>
                <InputLabel>State</InputLabel>
                <Select value={state} onChange={e => setState(e.target.value as string)} label="State">
                  {US_STATES.map(st => (
                    <MenuItem key={st} value={st}>
                      {st}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label="Zip Code"
                value={zipCode}
                onChange={e => {
                  const val = e.target.value.replace(/\D/g, '').slice(0, 5);
                  setZipCode(val);
                }}
                required
                sx={{ width: 120 }}
                inputProps={{ maxLength: 5 }}
              />
            </Box>

            <TextField
              label="County (optional)"
              value={county}
              onChange={e => setCounty(e.target.value)}
              fullWidth
              inputProps={{ maxLength: 100 }}
            />

            <TextField label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} fullWidth />

            <TextField label="Phone" value={phone} onChange={e => setPhone(e.target.value)} fullWidth />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={
              createMutation.isPending ||
              !companyType ||
              !name.trim() ||
              !address.trim() ||
              !city.trim() ||
              !state ||
              !/^[0-9]{5}$/.test(zipCode)
            }
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
