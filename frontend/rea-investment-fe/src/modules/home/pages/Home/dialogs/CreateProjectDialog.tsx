import React, { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
import { US_STATES } from '../../../../../constants/usStates';
import { SearchableSelect } from '../../../../../components/common/SearchableSelect/SearchableSelect';

interface CreateProjectDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateProjectDialog: React.FC<CreateProjectDialogProps> = ({ open, onClose, onSuccess }) => {
  const queryClient = useQueryClient();
  const { currentCompany } = useEntityContext();
  const [companyId, setCompanyId] = useState<number | ''>('');
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [county, setCounty] = useState('');
  const [zipCode, setZipCode] = useState('');
  const [systemSizeAc, setSystemSizeAc] = useState<number | ''>('');
  const [systemSizeDc, setSystemSizeDc] = useState<number | ''>('');
  const [lonLatUrl, setLonLatUrl] = useState('');
  const [templateId, setTemplateId] = useState<number | ''>('');
  const [error, setError] = useState<string | null>(null);

  const { data: companiesData } = useQuery({
    queryKey: ['home-accessible-companies'],
    queryFn: () => ApiClient.workspace.getWorkspace(),
    enabled: open
  });

  const { data: companySites } = useQuery({
    queryKey: ['company-sites-for-templates', companyId],
    queryFn: () => {
      const params: { company_id: number; limit: number } = { company_id: companyId as number, limit: 1 };
      return ApiClient.assetManagement.sites(params);
    },
    enabled: open && !!companyId
  });
  const representativeSiteId = companySites?.items?.[0]?.id;

  const { data: templatesData } = useQuery({
    queryKey: ['data-room-templates', { siteId: representativeSiteId, includeArchived: false }],
    queryFn: () => ApiClient.dueDiligence.listTemplates(representativeSiteId as number, false),
    enabled: open && !!representativeSiteId
  });
  const templates = templatesData?.items ?? [];

  useEffect(() => {
    if (open && currentCompany) {
      setCompanyId(currentCompany.id);
    }
  }, [open, currentCompany]);

  const createMutation = useMutation({
    mutationFn: () =>
      ApiClient.assetManagement.createSite({
        company_id: companyId as number,
        name,
        address,
        city,
        state,
        county: county || undefined,
        zip_code: zipCode,
        system_size_ac: (systemSizeAc as number) || 0,
        system_size_dc: (systemSizeDc as number) || 0,
        lon_lat_url: lonLatUrl,
        template_id: templateId || undefined
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['accessible-entities'] });
      resetForm();
      onSuccess();
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create project');
    }
  });

  const resetForm = () => {
    setCompanyId(currentCompany?.id ?? '');
    setName('');
    setAddress('');
    setCity('');
    setState('');
    setCounty('');
    setZipCode('');
    setSystemSizeAc('');
    setSystemSizeDc('');
    setLonLatUrl('');
    setTemplateId('');
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
    if (!name.trim()) {
      setError('Project name is required');
      return;
    }
    setError(null);
    createMutation.mutate();
  };

  const companies = companiesData?.companies ?? [];

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle>Create Project</DialogTitle>
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

            <TextField label="Project Name" value={name} onChange={e => setName(e.target.value)} required fullWidth />

            <TextField label="Address" value={address} onChange={e => setAddress(e.target.value)} fullWidth />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField label="City" value={city} onChange={e => setCity(e.target.value)} fullWidth />
              <SearchableSelect
                options={US_STATES.map(st => ({ label: st, value: st }))}
                value={state || null}
                onChange={val => setState(val as string)}
                label="State"
                sx={{ minWidth: 120 }}
              />
              <TextField
                label="Zip Code"
                value={zipCode}
                onChange={e => {
                  const val = e.target.value.replace(/\D/g, '').slice(0, 5);
                  setZipCode(val);
                }}
                sx={{ width: 120 }}
                inputProps={{ maxLength: 5 }}
              />
            </Box>

            <TextField label="County (optional)" value={county} onChange={e => setCounty(e.target.value)} fullWidth />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="System Size AC (kW)"
                type="number"
                value={systemSizeAc}
                onChange={e => setSystemSizeAc(e.target.value ? Number(e.target.value) : '')}
                fullWidth
                inputProps={{ min: 0, step: 0.01 }}
              />
              <TextField
                label="System Size DC (kW)"
                type="number"
                value={systemSizeDc}
                onChange={e => setSystemSizeDc(e.target.value ? Number(e.target.value) : '')}
                fullWidth
                inputProps={{ min: 0, step: 0.01 }}
              />
            </Box>

            <TextField
              label="Coordinates (Lat/Long)"
              value={lonLatUrl}
              onChange={e => setLonLatUrl(e.target.value)}
              fullWidth
              helperText="e.g. 41° 56' 54.3732&quot;"
            />

            {templates.length > 0 && (
              <SearchableSelect
                options={[
                  { label: 'Default structure (no template)', value: 0 },
                  ...templates.map(t => ({ label: t.name, value: t.id }))
                ]}
                value={templateId || 0}
                onChange={val => setTemplateId(val ? (val as number) : '')}
                label="Data Room Template (optional)"
                helperText="Scaffold this project's Data Room from a saved template."
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={createMutation.isPending || !companyId || !name.trim()}
            startIcon={createMutation.isPending ? <CircularProgress size={16} /> : null}
          >
            Create Project
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default CreateProjectDialog;
