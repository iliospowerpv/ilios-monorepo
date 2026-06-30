import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import Stack from '@mui/material/Stack';
import AddIcon from '@mui/icons-material/Add';
import PhotoCameraIcon from '@mui/icons-material/PhotoCamera';
import UploadIcon from '@mui/icons-material/Upload';
import DownloadIcon from '@mui/icons-material/Download';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import EditIcon from '@mui/icons-material/Edit';
import ArchiveIcon from '@mui/icons-material/Archive';
import UnarchiveIcon from '@mui/icons-material/Unarchive';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';

import { ApiClient, DataRoomTemplateSummary } from '../../../../../../../../api';
import { useNotify } from '../../../../../../../../contexts/notifications/notifications';

interface ManageTemplatesDialogProps {
  open: boolean;
  onClose: () => void;
  siteId: number;
  canEdit: boolean;
}

type FormMode = null | 'capture' | 'blank' | 'import' | 'rename';

const templatesQueryKey = (siteId: number, includeArchived: boolean) => [
  'data-room-templates',
  { siteId, includeArchived }
];

export const ManageTemplatesDialog: React.FC<ManageTemplatesDialogProps> = ({ open, onClose, siteId, canEdit }) => {
  const queryClient = useQueryClient();
  const notify = useNotify();

  const [includeArchived, setIncludeArchived] = useState(false);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [importText, setImportText] = useState('');
  const [renameTarget, setRenameTarget] = useState<DataRoomTemplateSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: templatesQueryKey(siteId, includeArchived),
    queryFn: () => ApiClient.dueDiligence.listTemplates(siteId, includeArchived),
    enabled: open
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['data-room-templates'] });
  };

  const resetForm = () => {
    setFormMode(null);
    setFormName('');
    setFormDescription('');
    setImportText('');
    setRenameTarget(null);
    setError(null);
  };

  const onMutationError = (err: any) => {
    setError(err?.response?.data?.detail || err?.response?.data?.message || 'Operation failed');
  };

  const captureMutation = useMutation({
    mutationFn: () =>
      ApiClient.dueDiligence.createTemplateFromDataRoom(siteId, formName.trim(), formDescription || undefined),
    onSuccess: () => {
      notify('Template captured from this Data Room');
      invalidate();
      resetForm();
    },
    onError: onMutationError
  });

  const blankMutation = useMutation({
    mutationFn: () => ApiClient.dueDiligence.createTemplate(siteId, formName.trim(), formDescription || undefined),
    onSuccess: () => {
      notify('Template created from the default blueprint');
      invalidate();
      resetForm();
    },
    onError: onMutationError
  });

  const importMutation = useMutation({
    mutationFn: () => {
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(importText);
      } catch {
        throw { response: { data: { message: 'Invalid JSON. Paste an exported template file.' } } };
      }
      return ApiClient.dueDiligence.importTemplate(siteId, parsed, formName.trim() || undefined);
    },
    onSuccess: () => {
      notify('Template imported');
      invalidate();
      resetForm();
    },
    onError: onMutationError
  });

  const renameMutation = useMutation({
    mutationFn: (templateId: number) =>
      ApiClient.dueDiligence.updateTemplate(siteId, templateId, {
        name: formName.trim(),
        description: formDescription
      }),
    onSuccess: () => {
      notify('Template updated');
      invalidate();
      resetForm();
    },
    onError: onMutationError
  });

  const duplicateMutation = useMutation({
    mutationFn: (templateId: number) => ApiClient.dueDiligence.duplicateTemplate(siteId, templateId),
    onSuccess: () => {
      notify('Template duplicated');
      invalidate();
    },
    onError: onMutationError
  });

  const archiveMutation = useMutation({
    mutationFn: ({ templateId, archived }: { templateId: number; archived: boolean }) =>
      archived
        ? ApiClient.dueDiligence.restoreTemplate(siteId, templateId)
        : ApiClient.dueDiligence.archiveTemplate(siteId, templateId),
    onSuccess: (_data, variables) => {
      notify(variables.archived ? 'Template restored' : 'Template archived');
      invalidate();
    },
    onError: onMutationError
  });

  const deleteMutation = useMutation({
    mutationFn: (templateId: number) => ApiClient.dueDiligence.deleteTemplate(siteId, templateId),
    onSuccess: () => {
      notify('Template deleted');
      invalidate();
    },
    onError: onMutationError
  });

  const handleExport = async (template: DataRoomTemplateSummary) => {
    try {
      const payload = await ApiClient.dueDiligence.exportTemplate(siteId, template.id);
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${template.name.replace(/[^a-z0-9-_]+/gi, '_')}.template.json`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      onMutationError(err);
    }
  };

  const startRename = (template: DataRoomTemplateSummary) => {
    setRenameTarget(template);
    setFormName(template.name);
    setFormDescription(template.description || '');
    setFormMode('rename');
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    setIncludeArchived(false);
    onClose();
  };

  const submitting =
    captureMutation.isPending || blankMutation.isPending || importMutation.isPending || renameMutation.isPending;

  const handleFormSubmit = () => {
    setError(null);
    if (formMode !== 'import' && !formName.trim()) {
      setError('Name is required');
      return;
    }
    if (formMode === 'capture') captureMutation.mutate();
    else if (formMode === 'blank') blankMutation.mutate();
    else if (formMode === 'import') importMutation.mutate();
    else if (formMode === 'rename' && renameTarget) renameMutation.mutate(renameTarget.id);
  };

  const templates = data?.items ?? [];

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Data Room Templates</DialogTitle>
      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {canEdit && (
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
            <Button
              size="small"
              variant="outlined"
              startIcon={<PhotoCameraIcon />}
              onClick={() => {
                resetForm();
                setFormMode('capture');
              }}
            >
              Capture from this Data Room
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={() => {
                resetForm();
                setFormMode('blank');
              }}
            >
              New from default
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<UploadIcon />}
              onClick={() => {
                resetForm();
                setFormMode('import');
              }}
            >
              Import
            </Button>
          </Stack>
        )}

        {formMode && (
          <Box sx={{ mb: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {formMode === 'capture' && 'Capture current Data Room structure'}
              {formMode === 'blank' && 'New template from the default blueprint'}
              {formMode === 'import' && 'Import a template'}
              {formMode === 'rename' && `Edit "${renameTarget?.name}"`}
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {formMode === 'import' && (
                <TextField
                  label="Exported template JSON"
                  value={importText}
                  onChange={e => setImportText(e.target.value)}
                  fullWidth
                  multiline
                  minRows={4}
                  required
                />
              )}
              <TextField
                label={formMode === 'import' ? 'Name (optional override)' : 'Template name'}
                value={formName}
                onChange={e => setFormName(e.target.value)}
                fullWidth
                required={formMode !== 'import'}
              />
              {formMode !== 'import' && (
                <TextField
                  label="Description (optional)"
                  value={formDescription}
                  onChange={e => setFormDescription(e.target.value)}
                  fullWidth
                  multiline
                  rows={2}
                />
              )}
              <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                <Button onClick={resetForm} disabled={submitting}>
                  Cancel
                </Button>
                <Button variant="contained" onClick={handleFormSubmit} disabled={submitting}>
                  {submitting ? 'Saving...' : 'Save'}
                </Button>
              </Box>
            </Box>
          </Box>
        )}

        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="subtitle2">Templates ({templates.length})</Typography>
          <FormControlLabel
            control={
              <Switch size="small" checked={includeArchived} onChange={e => setIncludeArchived(e.target.checked)} />
            }
            label="Show archived"
          />
        </Box>
        <Divider sx={{ mb: 1 }} />

        {isLoading || isFetching ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress size={32} />
          </Box>
        ) : templates.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
            No templates yet. {canEdit ? 'Capture this Data Room to create one.' : ''}
          </Typography>
        ) : (
          <Stack divider={<Divider flexItem />} spacing={0}>
            {templates.map(template => (
              <Box
                key={template.id}
                sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 1.25, gap: 2 }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body1" sx={{ fontWeight: 500 }} noWrap>
                      {template.name}
                    </Typography>
                    {template.is_archived && <Chip size="small" label="Archived" color="default" />}
                  </Box>
                  {template.description && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }} noWrap>
                      {template.description}
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {template.section_count} sections · {template.document_count} documents
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', flexShrink: 0 }}>
                  <Tooltip title="Export">
                    <IconButton size="small" onClick={() => handleExport(template)}>
                      <DownloadIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  {canEdit && (
                    <>
                      <Tooltip title="Duplicate">
                        <IconButton size="small" onClick={() => duplicateMutation.mutate(template.id)}>
                          <ContentCopyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Rename / edit">
                        <IconButton size="small" onClick={() => startRename(template)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={template.is_archived ? 'Restore' : 'Archive'}>
                        <IconButton
                          size="small"
                          onClick={() =>
                            archiveMutation.mutate({ templateId: template.id, archived: template.is_archived })
                          }
                        >
                          {template.is_archived ? <UnarchiveIcon fontSize="small" /> : <ArchiveIcon fontSize="small" />}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => {
                            if (window.confirm(`Delete template "${template.name}"? This cannot be undone.`)) {
                              deleteMutation.mutate(template.id);
                            }
                          }}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </>
                  )}
                </Box>
              </Box>
            ))}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ManageTemplatesDialog;
