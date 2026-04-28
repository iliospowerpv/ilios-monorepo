import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import { SearchableSelect } from '../../../../components/common/SearchableSelect/SearchableSelect';
import TextField from '@mui/material/TextField';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';

import AddIcon from '@mui/icons-material/Add';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

import { ApiClient } from '../../../../api';
import { useEntityContext } from '../../../../contexts/entityContext/entityContext';
import { US_STATES } from '../../../../constants/usStates';

interface ProjectStepProps {
  companyId: number;
  companyName: string;
  onComplete: (projectId: number, projectName: string) => void;
  onBack: () => void;
}

export const ProjectStep: React.FC<ProjectStepProps> = ({ companyId, companyName, onComplete, onBack }) => {
  const { setCurrentProject } = useEntityContext();

  const [mode, setMode] = useState<'select' | 'create'>('create');
  const [selectedProjectId, setSelectedProjectId] = useState<number | ''>('');
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [county, setCounty] = useState('');
  const [zipCode, setZipCode] = useState('');
  const [systemSizeAc, setSystemSizeAc] = useState('');
  const [systemSizeDc, setSystemSizeDc] = useState('');
  const [lonLatUrl, setLonLatUrl] = useState('');
  const [error, setError] = useState<string | null>(null);

  const { data: sitesData, isLoading: isLoadingProjects } = useQuery({
    queryKey: ['onboarding-projects', companyId],
    queryFn: () => ApiClient.assetManagement.sites({ skip: 0, limit: 100 })
  });

  const projects = (sitesData?.items ?? []).filter((site: { company_id?: number }) => site.company_id === companyId);

  const createMutation = useMutation({
    mutationFn: () =>
      ApiClient.assetManagement.createSite({
        company_id: companyId,
        name,
        address,
        city,
        state,
        county: county || undefined,
        zip_code: zipCode,
        system_size_ac: parseFloat(systemSizeAc) || 0,
        system_size_dc: parseFloat(systemSizeDc) || 0,
        lon_lat_url: lonLatUrl
      }),
    onSuccess: response => {
      if (response.id) {
        setCurrentProject({ id: response.id, name });
        onComplete(response.id, name);
      }
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create project');
    }
  });

  const handleSelectExisting = () => {
    if (!selectedProjectId) {
      setError('Please select a project');
      return;
    }
    const project = projects.find((p: { id: number }) => p.id === selectedProjectId);
    if (project) {
      setCurrentProject({ id: project.id, name: project.name });
      onComplete(project.id, project.name);
    }
  };

  const isCreateFormValid = () => {
    return (
      name.trim() !== '' &&
      address.trim() !== '' &&
      city.trim() !== '' &&
      state !== '' &&
      /^[0-9]{5}$/.test(zipCode) &&
      lonLatUrl.trim() !== ''
    );
  };

  const handleCreateNew = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Project name is required');
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
    if (!lonLatUrl.trim()) {
      setError('Coordinates are required');
      return;
    }
    setError(null);
    createMutation.mutate();
  };

  if (isLoadingProjects) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Card variant="outlined" sx={{ mb: 3, bgcolor: 'action.hover' }}>
        <CardContent sx={{ py: 1.5 }}>
          <Typography variant="body2" color="text.secondary">
            Creating project under company:
          </Typography>
          <Typography variant="subtitle1" fontWeight={600}>
            {companyName}
          </Typography>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {projects.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant={mode === 'create' ? 'contained' : 'outlined'}
              size="small"
              onClick={() => setMode('create')}
            >
              Create New
            </Button>
            <Button
              variant={mode === 'select' ? 'contained' : 'outlined'}
              size="small"
              onClick={() => setMode('select')}
            >
              Select Existing
            </Button>
          </Box>
        </Box>
      )}

      {mode === 'select' && projects.length > 0 && (
        <Card variant="outlined" sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Select an Existing Project
            </Typography>
            <SearchableSelect
              options={projects.map((project: { id: number; name: string }) => ({
                label: project.name,
                value: project.id
              }))}
              value={selectedProjectId || null}
              onChange={val => setSelectedProjectId(val as number)}
              label="Project"
              sx={{ mb: 2 }}
            />
            <Button
              variant="contained"
              onClick={handleSelectExisting}
              disabled={!selectedProjectId}
              endIcon={<ArrowForwardIcon />}
            >
              Continue
            </Button>
          </CardContent>
        </Card>
      )}

      {mode === 'create' && (
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Create a New Project
            </Typography>
            <form onSubmit={handleCreateNew}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Project Name"
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
                />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField label="City" value={city} onChange={e => setCity(e.target.value)} required fullWidth />
                  <SearchableSelect
                    options={US_STATES.map(st => ({ label: st, value: st }))}
                    value={state || null}
                    onChange={val => setState(val as string)}
                    label="State"
                    required
                    sx={{ minWidth: 120 }}
                  />
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
                />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField
                    label="System Size AC (kW)"
                    type="number"
                    value={systemSizeAc}
                    onChange={e => setSystemSizeAc(e.target.value)}
                    fullWidth
                    inputProps={{ min: 0, step: 0.01 }}
                  />
                  <TextField
                    label="System Size DC (kW)"
                    type="number"
                    value={systemSizeDc}
                    onChange={e => setSystemSizeDc(e.target.value)}
                    fullWidth
                    inputProps={{ min: 0, step: 0.01 }}
                  />
                </Box>
                <TextField
                  label="Coordinates (Lat/Long)"
                  value={lonLatUrl}
                  onChange={e => setLonLatUrl(e.target.value)}
                  required
                  fullWidth
                  helperText="e.g. 41° 56' 54.3732&quot;"
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={createMutation.isPending || !isCreateFormValid()}
                  startIcon={createMutation.isPending ? <CircularProgress size={16} /> : <AddIcon />}
                >
                  Create Project
                </Button>
              </Box>
            </form>
          </CardContent>
        </Card>
      )}

      <Button sx={{ mt: 3 }} startIcon={<ArrowBackIcon />} onClick={onBack}>
        Back to Company
      </Button>
    </Box>
  );
};

export default ProjectStep;
