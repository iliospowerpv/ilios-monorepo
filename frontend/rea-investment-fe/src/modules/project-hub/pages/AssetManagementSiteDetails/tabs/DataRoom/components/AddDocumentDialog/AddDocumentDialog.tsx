import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { debounce } from 'lodash';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import CircularProgress from '@mui/material/CircularProgress';
import UploadFileIcon from '@mui/icons-material/UploadFile';

import { SearchableSelect } from '../../../../../../../../components/common/SearchableSelect/SearchableSelect';
import { ApiClient } from '../../../../../../../../api';
import { useNotify } from '../../../../../../../../contexts/notifications/notifications';

interface SectionOption {
  id: number;
  name: string;
}

export interface AddDocumentPrefill {
  name?: string;
  sectionId?: number | null;
}

interface AddDocumentDialogProps {
  open: boolean;
  onClose: () => void;
  siteId: number;
  sections: SectionOption[];
  onNavigateToDocument: (documentId: number) => void;
  prefill?: AddDocumentPrefill | null;
}

export const AddDocumentDialog: React.FC<AddDocumentDialogProps> = ({
  open,
  onClose,
  siteId,
  sections,
  onNavigateToDocument,
  prefill
}) => {
  const notify = useNotify();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sectionId, setSectionId] = useState<number | ''>('');
  const [confirmSeparate, setConfirmSeparate] = useState(false);
  const [debouncedName, setDebouncedName] = useState('');

  const updateDebouncedName = useMemo(
    () =>
      debounce((value: string) => {
        setDebouncedName(value);
        // A new typed name invalidates a prior "create separate anyway" confirmation.
        setConfirmSeparate(false);
      }, 400),
    []
  );

  useEffect(() => {
    updateDebouncedName(name.trim());
  }, [name, updateDebouncedName]);

  useEffect(() => () => updateDebouncedName.cancel(), [updateDebouncedName]);

  useEffect(() => {
    if (open) {
      const initialName = prefill?.name ?? '';
      setName(initialName);
      setDescription('');
      setSectionId(prefill?.sectionId ?? '');
      setConfirmSeparate(false);
      // Seed the debounced value so a prefilled name runs the duplicate check immediately.
      setDebouncedName(initialName.trim());
    }
    // Intentionally keyed off `open` only: the prefill is read once when the dialog opens
    // so it never clobbers what the user is actively typing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const { data: duplicateResult, isFetching: isCheckingDuplicates } = useQuery({
    queryKey: ['site', 'duplicate-check', { siteId, name: debouncedName }],
    queryFn: () => ApiClient.dueDiligence.checkDuplicateDocument(siteId, debouncedName),
    enabled: open && !!siteId && debouncedName.length >= 2
  });

  const candidates = useMemo(() => duplicateResult?.candidates ?? [], [duplicateResult]);
  const hasMatch = candidates.length > 0;

  const createMutation = useMutation({
    mutationFn: () =>
      ApiClient.dueDiligence.createCustomDocument(siteId, sectionId as number, name.trim(), description || undefined),
    onSuccess: () => {
      notify('Document created successfully');
      queryClient.invalidateQueries({ queryKey: ['site', 'diligence', { siteId }] });
      queryClient.invalidateQueries({ queryKey: ['site', 'data-room-guidance', { siteId }] });
      onClose();
    },
    onError: (error: any) => {
      notify(error?.response?.data?.detail || 'Failed to create document');
    }
  });

  const handleCreate = () => {
    if (!name.trim() || !sectionId) {
      notify('Please fill in all required fields');
      return;
    }
    // Guided guardrail: when an existing identity looks like a match, the user must
    // explicitly confirm they want a separate second document before we create one.
    if (hasMatch && !confirmSeparate) {
      notify('A similar document already exists. Confirm you want a separate document, or upload a new version.');
      return;
    }
    createMutation.mutate();
  };

  const handleUploadVersion = (documentId: number) => {
    onClose();
    onNavigateToDocument(documentId);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add New Document</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Document Name"
            value={name}
            onChange={e => setName(e.target.value)}
            fullWidth
            required
            inputProps={{ 'data-testid': 'add-document-name' }}
            InputProps={{
              endAdornment: isCheckingDuplicates ? <CircularProgress size={18} /> : undefined
            }}
          />

          {hasMatch && (
            <Alert
              severity="info"
              icon={false}
              data-testid="add-document-match-alert"
              sx={{ '& .MuiAlert-message': { width: '100%' } }}
            >
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                A similar document already exists
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                To keep one document per item, upload a new version to an existing document instead of creating a
                duplicate.
              </Typography>
              <Stack spacing={1}>
                {candidates.map(candidate => (
                  <Box
                    key={candidate.document_id}
                    display="flex"
                    alignItems="center"
                    justifyContent="space-between"
                    gap={1}
                  >
                    <Box minWidth={0}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }} noWrap>
                        {candidate.name}
                      </Typography>
                      <Box display="flex" alignItems="center" gap={0.5} flexWrap="wrap">
                        <Chip
                          size="small"
                          label={candidate.match_type === 'exact' ? 'Exact match' : 'Similar'}
                          color={candidate.match_type === 'exact' ? 'primary' : 'default'}
                          variant="outlined"
                        />
                        {candidate.section_name && (
                          <Typography variant="caption" color="text.secondary">
                            {candidate.section_name}
                          </Typography>
                        )}
                        <Typography variant="caption" color="text.secondary">
                          · {candidate.files_count} version{candidate.files_count === 1 ? '' : 's'}
                        </Typography>
                        {candidate.is_archived && (
                          <Chip size="small" label="Archived" variant="outlined" color="warning" />
                        )}
                      </Box>
                    </Box>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<UploadFileIcon />}
                      onClick={() => handleUploadVersion(candidate.document_id)}
                      data-testid={`add-document-upload-version-${candidate.document_id}`}
                      sx={{ flexShrink: 0 }}
                    >
                      Upload version
                    </Button>
                  </Box>
                ))}
              </Stack>
              <FormControlLabel
                sx={{ mt: 1 }}
                control={
                  <Checkbox
                    size="small"
                    checked={confirmSeparate}
                    onChange={e => setConfirmSeparate(e.target.checked)}
                    inputProps={{ 'data-testid': 'add-document-confirm-separate' }}
                  />
                }
                label={<Typography variant="body2">Create a separate document anyway</Typography>}
              />
            </Alert>
          )}

          <TextField
            label="Description (optional)"
            value={description}
            onChange={e => setDescription(e.target.value)}
            fullWidth
            multiline
            rows={2}
          />
          <SearchableSelect
            options={sections.map(section => ({ label: section.name, value: section.id }))}
            value={sectionId || null}
            onChange={val => setSectionId(val as number)}
            label="Section"
            required
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} data-testid="add-document-cancel">
          Cancel
        </Button>
        <Button
          onClick={handleCreate}
          variant="contained"
          data-testid="add-document-submit"
          disabled={createMutation.isPending || (hasMatch && !confirmSeparate)}
        >
          {createMutation.isPending ? 'Creating...' : hasMatch ? 'Create Separate Document' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddDocumentDialog;
