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

import FolderIcon from '@mui/icons-material/Folder';
import AddIcon from '@mui/icons-material/Add';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

import { ApiClient } from '../../../../api';
import { useEntityContext } from '../../../../contexts/entityContext/entityContext';

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
  const [zipCode, setZipCode] = useState('');
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
        zip_code: zipCode,
        system_size_ac: 0,
        system_size_dc: 0,
        lon_lat_url: ''
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

  const handleCreateNew = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Project name is required');
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
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Project</InputLabel>
              <Select
                value={selectedProjectId}
                onChange={e => setSelectedProjectId(e.target.value as number)}
                label="Project"
              >
                {projects.map((project: { id: number; name: string }) => (
                  <MenuItem key={project.id} value={project.id}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <FolderIcon fontSize="small" color="action" />
                      {project.name}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
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
                  label="Address (optional)"
                  value={address}
                  onChange={e => setAddress(e.target.value)}
                  fullWidth
                />
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField label="City" value={city} onChange={e => setCity(e.target.value)} fullWidth />
                  <TextField label="State" value={state} onChange={e => setState(e.target.value)} sx={{ width: 100 }} />
                  <TextField
                    label="Zip"
                    value={zipCode}
                    onChange={e => setZipCode(e.target.value)}
                    sx={{ width: 100 }}
                  />
                </Box>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={createMutation.isPending || !name.trim()}
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
