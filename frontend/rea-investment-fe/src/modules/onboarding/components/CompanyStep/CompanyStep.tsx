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

interface CompanyStepProps {
  onComplete: (companyId: number, companyName: string) => void;
}

export const CompanyStep: React.FC<CompanyStepProps> = ({ onComplete }) => {
  const { user } = useAuth();
  const { currentCompany, setCurrentCompany } = useEntityContext();
  const isSystemUser = user?.is_system_user ?? false;

  const [mode, setMode] = useState<'select' | 'create' | null>(currentCompany ? null : null);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | ''>(currentCompany?.id ?? '');
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanyEmail, setNewCompanyEmail] = useState('');
  const [error, setError] = useState<string | null>(null);

  const { data: workspaceData, isLoading: isLoadingCompanies } = useQuery({
    queryKey: ['onboarding-companies'],
    queryFn: () => ApiClient.workspace.getWorkspace()
  });

  const companies = workspaceData?.companies ?? [];

  const createMutation = useMutation({
    mutationFn: () =>
      ApiClient.companies.create({
        company_type: 'owner',
        name: newCompanyName,
        email: newCompanyEmail || null,
        phone: null,
        address: null
      }),
    onSuccess: (response) => {
      const newCompanyId = (response as unknown as { id?: number }).id;
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
    if (!selectedCompanyId) {
      setError('Please select a company');
      return;
    }
    const company = companies.find(c => c.company_id === selectedCompanyId);
    if (company) {
      setCurrentCompany({ id: company.company_id, name: company.company_name });
      onComplete(company.company_id, company.company_name);
    }
  };

  const handleCreateNew = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCompanyName.trim()) {
      setError('Company name is required');
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
          <Button
            variant="contained"
            size="large"
            endIcon={<ArrowForwardIcon />}
            onClick={handleContinueWithCurrent}
          >
            Continue with {currentCompany.name}
          </Button>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              onClick={() => setMode('select')}
              sx={{ flex: 1 }}
            >
              Change Company
            </Button>
            {isSystemUser && (
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={() => setMode('create')}
                sx={{ flex: 1 }}
              >
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
                value={selectedCompanyId}
                onChange={e => setSelectedCompanyId(e.target.value as number)}
                label="Company"
              >
                {companies.map(company => (
                  <MenuItem key={company.company_id} value={company.company_id}>
                    {company.company_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="contained"
              onClick={handleSelectExisting}
              disabled={!selectedCompanyId}
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
                />
                <TextField
                  label="Email (optional)"
                  type="email"
                  value={newCompanyEmail}
                  onChange={e => setNewCompanyEmail(e.target.value)}
                  fullWidth
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={createMutation.isPending || !newCompanyName.trim()}
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
          You don't have access to any companies yet. Please contact your administrator to get access.
        </Alert>
      )}

      {mode !== null && (
        <Button
          sx={{ mt: 2 }}
          onClick={() => setMode(null)}
        >
          Back
        </Button>
      )}
    </Box>
  );
};

export default CompanyStep;
