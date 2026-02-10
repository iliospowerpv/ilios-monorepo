import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import BusinessIcon from '@mui/icons-material/Business';
import AddIcon from '@mui/icons-material/Add';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

import { ApiClient } from '../../../../api';
import { useAuth } from '../../../../contexts/auth/auth';
import { useEntityContext } from '../../../../contexts/entityContext/entityContext';
import { US_STATES } from '../../../../constants/usStates';

interface CompanyStepProps {
  onComplete: (companyId: number, companyName: string) => void;
}

export const CompanyStep: React.FC<CompanyStepProps> = ({ onComplete }) => {
  const { user } = useAuth();
  const { currentCompany, setCurrentCompany } = useEntityContext();
  const isSystemUser = user?.is_system_user ?? false;

  const [mode, setMode] = useState<'select' | 'create' | null>(null);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanyEmail, setNewCompanyEmail] = useState('');
  const [newCompanyPhone, setNewCompanyPhone] = useState('');
  const [newCompanyAddress, setNewCompanyAddress] = useState('');
  const [newCompanyCity, setNewCompanyCity] = useState('');
  const [newCompanyState, setNewCompanyState] = useState('');
  const [newCompanyCounty, setNewCompanyCounty] = useState('');
  const [newCompanyZipCode, setNewCompanyZipCode] = useState('');
  const [error, setError] = useState<string | null>(null);

  const { data: workspaceData, isLoading: isLoadingCompanies } = useQuery({
    queryKey: ['onboarding-companies'],
    queryFn: () => ApiClient.workspace.getWorkspace()
  });

  const companies = workspaceData?.companies ?? [];

  const createMutation = useMutation({
    mutationFn: () =>
      ApiClient.companies.create({
        company_type: 'project_site_owner',
        name: newCompanyName,
        address: newCompanyAddress,
        city: newCompanyCity,
        state: newCompanyState,
        county: newCompanyCounty || null,
        zip_code: newCompanyZipCode,
        email: newCompanyEmail || null,
        phone: newCompanyPhone || null
      }),
    onSuccess: response => {
      const newCompanyId = response.id;
      if (newCompanyId) {
        setCurrentCompany({ id: newCompanyId, name: newCompanyName });
        onComplete(newCompanyId, newCompanyName);
      }
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create company');
    }
  });

  const handleContinueWithCurrent = () => {
    if (currentCompany) {
      onComplete(currentCompany.id, currentCompany.name);
    }
  };

  const handleSelectExisting = () => {
    if (selectedCompanyId === null) {
      setError('Please select a company');
      return;
    }
    const company = companies.find(c => c.company_id === selectedCompanyId);
    if (company) {
      setCurrentCompany({ id: company.company_id, name: company.company_name });
      onComplete(company.company_id, company.company_name);
    } else {
      setError('Selected company not found. Please try again.');
    }
  };

  const isCreateFormValid = () => {
    return (
      newCompanyName.trim().length >= 2 &&
      newCompanyAddress.trim() !== '' &&
      newCompanyCity.trim() !== '' &&
      newCompanyState !== '' &&
      /^[0-9]{5}$/.test(newCompanyZipCode) &&
      (!newCompanyPhone || /^[0-9]{10}$/.test(newCompanyPhone))
    );
  };

  const handleCreateNew = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCompanyName.trim()) {
      setError('Company name is required');
      return;
    }
    if (!newCompanyAddress.trim()) {
      setError('Address is required');
      return;
    }
    if (!newCompanyCity.trim()) {
      setError('City is required');
      return;
    }
    if (!newCompanyState) {
      setError('State is required');
      return;
    }
    if (!/^[0-9]{5}$/.test(newCompanyZipCode)) {
      setError('Zip code must be exactly 5 digits');
      return;
    }
    if (newCompanyPhone && !/^[0-9]{10}$/.test(newCompanyPhone)) {
      setError('Phone must be exactly 10 digits');
      return;
    }
    setError(null);
    createMutation.mutate();
  };

  if (isLoadingCompanies) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (currentCompany && mode === null) {
    return (
      <Box>
        <Card variant="outlined" sx={{ mb: 3, bgcolor: 'action.selected' }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <BusinessIcon color="primary" sx={{ fontSize: 40 }} />
              <Box sx={{ flex: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  Company Selected
                </Typography>
                <Typography variant="h6">{currentCompany.name}</Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Button variant="contained" size="large" endIcon={<ArrowForwardIcon />} onClick={handleContinueWithCurrent}>
            Continue with {currentCompany.name}
          </Button>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button variant="outlined" onClick={() => setMode('select')} sx={{ flex: 1 }}>
              Change Company
            </Button>
            {isSystemUser && (
              <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setMode('create')} sx={{ flex: 1 }}>
                Create New
              </Button>
            )}
          </Box>
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {(mode === null || mode === 'select') && companies.length > 0 && (
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Select an Existing Company
            </Typography>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Company</InputLabel>
              <Select
                value={selectedCompanyId !== null ? String(selectedCompanyId) : ''}
                onChange={e => {
                  const val = e.target.value as string;
                  setSelectedCompanyId(val ? Number(val) : null);
                }}
                label="Company"
              >
                {companies.map(company => (
                  <MenuItem key={company.company_id} value={String(company.company_id)}>
                    {company.company_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="contained"
              onClick={handleSelectExisting}
              disabled={selectedCompanyId === null}
              endIcon={<ArrowForwardIcon />}
            >
              Continue
            </Button>
          </CardContent>
        </Card>
      )}

      {companies.length > 0 && isSystemUser && mode !== 'create' && (
        <Divider sx={{ my: 3 }}>
          <Typography variant="body2" color="text.secondary">
            OR
          </Typography>
        </Divider>
      )}

      {isSystemUser && (mode === null || mode === 'create') && (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Create a New Company
            </Typography>
            <form onSubmit={handleCreateNew}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Company Name"
                  value={newCompanyName}
                  onChange={e => setNewCompanyName(e.target.value)}
                  required
                  fullWidth
                  autoFocus={mode === 'create'}
                  inputProps={{ minLength: 2, maxLength: 100 }}
                />
                <TextField
                  label="Address"
                  value={newCompanyAddress}
                  onChange={e => setNewCompanyAddress(e.target.value)}
                  required
                  fullWidth
                  inputProps={{ maxLength: 255 }}
                />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    label="City"
                    value={newCompanyCity}
                    onChange={e => setNewCompanyCity(e.target.value)}
                    required
                    fullWidth
                    inputProps={{ maxLength: 100 }}
                  />
                  <FormControl required sx={{ minWidth: 120 }}>
                    <InputLabel>State</InputLabel>
                    <Select
                      value={newCompanyState}
                      onChange={e => setNewCompanyState(e.target.value as string)}
                      label="State"
                    >
                      {US_STATES.map(st => (
                        <MenuItem key={st} value={st}>
                          {st}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <TextField
                    label="Zip Code"
                    value={newCompanyZipCode}
                    onChange={e => {
                      const val = e.target.value.replace(/\D/g, '').slice(0, 5);
                      setNewCompanyZipCode(val);
                    }}
                    required
                    sx={{ width: 120 }}
                    inputProps={{ maxLength: 5 }}
                  />
                </Box>
                <TextField
                  label="County (optional)"
                  value={newCompanyCounty}
                  onChange={e => setNewCompanyCounty(e.target.value)}
                  fullWidth
                  inputProps={{ maxLength: 100 }}
                />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    label="Email (optional)"
                    type="email"
                    value={newCompanyEmail}
                    onChange={e => setNewCompanyEmail(e.target.value)}
                    fullWidth
                    inputProps={{ maxLength: 100 }}
                  />
                  <TextField
                    label="Phone (optional, 10 digits)"
                    value={newCompanyPhone}
                    onChange={e => {
                      const val = e.target.value.replace(/\D/g, '').slice(0, 10);
                      setNewCompanyPhone(val);
                    }}
                    fullWidth
                    inputProps={{ maxLength: 10 }}
                  />
                </Box>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={createMutation.isPending || !isCreateFormValid()}
                  startIcon={createMutation.isPending ? <CircularProgress size={16} /> : <AddIcon />}
                >
                  Create Company
                </Button>
              </Box>
            </form>
          </CardContent>
        </Card>
      )}

      {!isSystemUser && companies.length === 0 && (
        <Alert severity="info">
          You do not have access to any companies yet. Please contact your administrator to get access.
        </Alert>
      )}

      {mode !== null && (
        <Button sx={{ mt: 2 }} onClick={() => setMode(null)}>
          Back
        </Button>
      )}
    </Box>
  );
};

export default CompanyStep;
