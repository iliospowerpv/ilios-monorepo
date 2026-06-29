import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import CircularProgress from '@mui/material/CircularProgress';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import type { WorkflowStepSchema, PreviewResponse, WorkflowErrorPayload } from './types';

interface WizardReviewStepProps {
  step: WorkflowStepSchema;
  preview: PreviewResponse | null;
  previewLoading: boolean;
  previewError: WorkflowErrorPayload | null;
  reconfirm: boolean;
  executing: boolean;
  confirmLabel: string;
  // When set, this execute step uploads a file: render a file picker and require a selection.
  multipartFileField?: string | null;
  selectedFile?: File | null;
  onFileChange?: (file: File | null) => void;
  onConfirm: () => void;
  onBack: () => void;
  onExit: () => void;
}

export const WizardReviewStep: React.FC<WizardReviewStepProps> = ({
  step,
  preview,
  previewLoading,
  previewError,
  reconfirm,
  executing,
  confirmLabel,
  multipartFileField,
  selectedFile,
  onFileChange,
  onConfirm,
  onBack,
  onExit
}) => {
  const governed = step.confirmation === 'governed';
  const requiresFile = !!multipartFileField;
  const [acknowledged, setAcknowledged] = useState(false);

  if (previewLoading && !preview) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  const confirmDisabled =
    executing || !preview || !!previewError || (governed && !acknowledged) || (requiresFile && !selectedFile);

  return (
    <Box>
      {step.help && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {step.help}
        </Typography>
      )}

      {previewError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <AlertTitle>{previewError.message ?? 'Some details are missing or invalid.'}</AlertTitle>
          {previewError.errors && (
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {Object.entries(previewError.errors).map(([key, message]) => (
                <li key={key}>
                  {key}: {message}
                </li>
              ))}
            </ul>
          )}
        </Alert>
      )}

      {reconfirm && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          The details changed since you reviewed them. Please review again and confirm.
        </Alert>
      )}

      {governed && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <AlertTitle>Governed action</AlertTitle>
          This changes operational truth and is recorded for audit. Review carefully before confirming.
        </Alert>
      )}

      {preview?.warnings?.map(warning => (
        <Alert severity="warning" sx={{ mb: 1 }} key={warning}>
          {warning}
        </Alert>
      ))}

      {preview && preview.summary.length > 0 && (
        <Box sx={{ my: 2, border: 1, borderColor: 'divider', borderRadius: 1, overflow: 'hidden' }}>
          {preview.summary.map((item, index) => (
            <Box key={item.label}>
              {index > 0 && <Divider />}
              <Stack direction="row" justifyContent="space-between" spacing={2} sx={{ px: 2, py: 1.25 }}>
                <Typography variant="body2" color="text.secondary">
                  {item.label}
                </Typography>
                <Typography variant="body2" fontWeight={500} sx={{ textAlign: 'right' }}>
                  {item.value ?? '—'}
                </Typography>
              </Stack>
            </Box>
          ))}
        </Box>
      )}

      {requiresFile && (
        <Box sx={{ my: 2 }}>
          <Button variant="outlined" component="label" disabled={executing}>
            {selectedFile ? 'Change file' : 'Choose file'}
            <input type="file" hidden onChange={event => onFileChange?.(event.target.files?.[0] ?? null)} />
          </Button>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {selectedFile ? selectedFile.name : 'No file selected.'}
          </Typography>
        </Box>
      )}

      {governed && (
        <FormControlLabel
          control={<Checkbox checked={acknowledged} onChange={event => setAcknowledged(event.target.checked)} />}
          label="I understand this is a governed change and confirm it."
        />
      )}

      <Stack direction="row" justifyContent="space-between" sx={{ mt: 4 }}>
        <Stack direction="row" spacing={1}>
          <Button variant="text" color="inherit" onClick={onExit} disabled={executing}>
            Cancel
          </Button>
          <Button variant="outlined" onClick={onBack} disabled={executing}>
            Back
          </Button>
        </Stack>
        <Button
          variant="contained"
          onClick={onConfirm}
          disabled={confirmDisabled}
          startIcon={executing ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          {executing ? 'Working…' : confirmLabel}
        </Button>
      </Stack>
    </Box>
  );
};

export default WizardReviewStep;
