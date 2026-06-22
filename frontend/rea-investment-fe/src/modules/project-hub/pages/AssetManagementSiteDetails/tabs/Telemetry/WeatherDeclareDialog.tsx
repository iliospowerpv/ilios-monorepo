import React, { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import CircularProgress from '@mui/material/CircularProgress';

import { ApiClient } from '../../../../../../api';
import type {
  WeatherDeclareRequest,
  WeatherDeclarationBasis,
  WeatherIrradiancePlane,
  WeatherTemperatureType,
  WeatherCalibrationStatus,
  WeatherDeviceMapping
} from '../../../../../../types/weather';

interface Option<T extends string> {
  value: T;
  label: string;
}

const BASIS_OPTIONS: Option<WeatherDeclarationBasis>[] = [
  { value: 'provider_confirmed', label: 'Provider confirmed' },
  { value: 'source_document', label: 'Source document' },
  { value: 'reviewer_source_note', label: 'Reviewer source note' },
  { value: 'reviewer_assumption', label: 'Reviewer assumption' }
];

const PLANE_OPTIONS: Option<WeatherIrradiancePlane>[] = [
  { value: 'unknown', label: 'Unknown (not declared)' },
  { value: 'poa', label: 'POA — plane of array' },
  { value: 'ghi', label: 'GHI — global horizontal' },
  { value: 'dni', label: 'DNI — direct normal' },
  { value: 'dhi', label: 'DHI — diffuse horizontal' }
];

const TEMP_OPTIONS: Option<WeatherTemperatureType>[] = [
  { value: 'unknown', label: 'Unknown (not declared)' },
  { value: 'cell', label: 'Cell' },
  { value: 'module', label: 'Module back' },
  { value: 'ambient', label: 'Ambient' },
  { value: 'modeled_cell', label: 'Modeled cell' }
];

const CALIBRATION_OPTIONS: Option<WeatherCalibrationStatus>[] = [
  { value: 'unknown', label: 'Unknown (not declared)' },
  { value: 'calibrated', label: 'Calibrated' },
  { value: 'uncalibrated', label: 'Uncalibrated' }
];

interface WeatherDeclareDialogProps {
  open: boolean;
  onClose: () => void;
  siteId: number;
  deviceId: number;
  deviceName?: string | null;
  defaultMetric?: string | null;
  /** Optional supersession target (the current active mapping for this device). */
  supersedesMappingId?: number | null;
}

const STEPS = ['Declare semantics', 'Review & activate'];

/**
 * Two-step governed weather-semantics declaration dialog.
 *
 * Step 1 captures the declared measurement semantics, governing basis, and
 * evidence. Step 2 reviews exactly what will be written and lets the reviewer
 * either save it as a draft or declare-and-activate atomically. Semantics are
 * NEVER inferred: every field defaults to `unknown` and only an explicit choice
 * sets POA / cell / calibrated. The `reviewer_assumption` basis requires an
 * explicit confirmation before anything can be saved.
 */
export const WeatherDeclareDialog: React.FC<WeatherDeclareDialogProps> = ({
  open,
  onClose,
  siteId,
  deviceId,
  deviceName,
  defaultMetric,
  supersedesMappingId
}) => {
  const queryClient = useQueryClient();
  const [activeStep, setActiveStep] = useState(0);

  const [metric, setMetric] = useState(defaultMetric ?? '');
  const [basis, setBasis] = useState<WeatherDeclarationBasis>('provider_confirmed');
  const [plane, setPlane] = useState<WeatherIrradiancePlane>('unknown');
  const [temperature, setTemperature] = useState<WeatherTemperatureType>('unknown');
  const [calibration, setCalibration] = useState<WeatherCalibrationStatus>('unknown');
  const [weatherSourceId, setWeatherSourceId] = useState('');
  const [sourceDocumentId, setSourceDocumentId] = useState('');
  const [sourceFileId, setSourceFileId] = useState('');
  const [reviewerNote, setReviewerNote] = useState('');
  const [assumptionConfirmed, setAssumptionConfirmed] = useState(false);

  const isAssumption = basis === 'reviewer_assumption';

  const reset = () => {
    setActiveStep(0);
    setMetric(defaultMetric ?? '');
    setBasis('provider_confirmed');
    setPlane('unknown');
    setTemperature('unknown');
    setCalibration('unknown');
    setWeatherSourceId('');
    setSourceDocumentId('');
    setSourceFileId('');
    setReviewerNote('');
    setAssumptionConfirmed(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const buildPayload = (activate: boolean): WeatherDeclareRequest => {
    const parseId = (raw: string): number | undefined => {
      const trimmed = raw.trim();
      if (!trimmed) return undefined;
      const n = Number(trimmed);
      return Number.isFinite(n) ? n : undefined;
    };
    return {
      device_id: deviceId,
      metric: metric.trim(),
      declaration_basis: basis,
      irradiance_plane: plane,
      temperature_type: temperature,
      calibration_status: calibration,
      weather_source_id: parseId(weatherSourceId) ?? null,
      source_document_id: parseId(sourceDocumentId) ?? null,
      source_file_id: parseId(sourceFileId) ?? null,
      reviewer_note: reviewerNote.trim() || null,
      supersedes_mapping_id: supersedesMappingId ?? null,
      assumption_confirmed: isAssumption ? assumptionConfirmed : false,
      activate
    };
  };

  const mutation = useMutation<WeatherDeviceMapping, unknown, boolean>({
    mutationFn: (activate: boolean) => ApiClient.weather.declareDeviceMapping(siteId, buildPayload(activate)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['weather-semantics-reconciliation', siteId] });
      queryClient.invalidateQueries({ queryKey: ['weather-device-mappings', siteId] });
      queryClient.invalidateQueries({ queryKey: ['weather-device-history', siteId, deviceId] });
      queryClient.invalidateQueries({ queryKey: ['weather-upstream-changes', siteId] });
      handleClose();
    }
  });

  const errorMessage = useMemo(() => {
    if (!mutation.isError) return null;
    const err = mutation.error as { response?: { data?: { detail?: unknown } }; message?: string };
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object') return JSON.stringify(detail);
    return err?.message || 'Failed to save the declaration.';
  }, [mutation.isError, mutation.error]);

  const metricValid = metric.trim().length > 0 && metric.trim().length <= 64;
  const canContinue = metricValid;
  const assumptionBlocks = isAssumption && !assumptionConfirmed;
  const canSubmit = canContinue && !assumptionBlocks && !mutation.isPending;

  const semanticsSummary = (
    <Box sx={{ display: 'grid', gridTemplateColumns: 'auto 1fr', columnGap: 2, rowGap: 0.5 }}>
      <Typography variant="body2" color="text.secondary">
        Device
      </Typography>
      <Typography variant="body2">{deviceName ?? `Device ${deviceId}`}</Typography>
      <Typography variant="body2" color="text.secondary">
        Metric
      </Typography>
      <Typography variant="body2">{metric || '—'}</Typography>
      <Typography variant="body2" color="text.secondary">
        Basis
      </Typography>
      <Typography variant="body2">{BASIS_OPTIONS.find(o => o.value === basis)?.label}</Typography>
      <Typography variant="body2" color="text.secondary">
        Irradiance plane
      </Typography>
      <Typography variant="body2">{PLANE_OPTIONS.find(o => o.value === plane)?.label}</Typography>
      <Typography variant="body2" color="text.secondary">
        Temperature type
      </Typography>
      <Typography variant="body2">{TEMP_OPTIONS.find(o => o.value === temperature)?.label}</Typography>
      <Typography variant="body2" color="text.secondary">
        Calibration
      </Typography>
      <Typography variant="body2">{CALIBRATION_OPTIONS.find(o => o.value === calibration)?.label}</Typography>
    </Box>
  );

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Declare weather semantics</DialogTitle>
      <DialogContent dividers>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {STEPS.map(label => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {activeStep === 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Alert severity="info" sx={{ py: 0 }}>
              Semantics are never guessed. Anything left as &quot;Unknown&quot; stays undeclared — declaring GHI does not
              transpose it to POA, and declaring ambient does not promote it to cell.
            </Alert>
            <Typography variant="body2" color="text.secondary">
              Device: <strong>{deviceName ?? `Device ${deviceId}`}</strong>
            </Typography>
            <TextField
              label="Metric"
              value={metric}
              onChange={e => setMetric(e.target.value)}
              required
              size="small"
              error={metric.length > 0 && !metricValid}
              helperText={metric.length > 0 && !metricValid ? 'Metric must be 1–64 characters.' : 'e.g. irradiance, module_temp'}
            />
            <TextField
              label="Declaration basis"
              select
              value={basis}
              onChange={e => setBasis(e.target.value as WeatherDeclarationBasis)}
              size="small"
            >
              {BASIS_OPTIONS.map(o => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Irradiance plane"
              select
              value={plane}
              onChange={e => setPlane(e.target.value as WeatherIrradiancePlane)}
              size="small"
            >
              {PLANE_OPTIONS.map(o => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Temperature type"
              select
              value={temperature}
              onChange={e => setTemperature(e.target.value as WeatherTemperatureType)}
              size="small"
            >
              {TEMP_OPTIONS.map(o => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Calibration status"
              select
              value={calibration}
              onChange={e => setCalibration(e.target.value as WeatherCalibrationStatus)}
              size="small"
            >
              {CALIBRATION_OPTIONS.map(o => (
                <MenuItem key={o.value} value={o.value}>
                  {o.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Weather source ID (optional)"
              value={weatherSourceId}
              onChange={e => setWeatherSourceId(e.target.value)}
              size="small"
              type="number"
            />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="Source document ID"
                value={sourceDocumentId}
                onChange={e => setSourceDocumentId(e.target.value)}
                size="small"
                type="number"
                fullWidth
              />
              <TextField
                label="Source file ID"
                value={sourceFileId}
                onChange={e => setSourceFileId(e.target.value)}
                size="small"
                type="number"
                fullWidth
              />
            </Box>
            <TextField
              label="Reviewer note (evidence)"
              value={reviewerNote}
              onChange={e => setReviewerNote(e.target.value)}
              size="small"
              multiline
              minRows={2}
            />
          </Box>
        )}

        {activeStep === 1 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="subtitle2">Review declaration</Typography>
            {semanticsSummary}
            {(sourceDocumentId || sourceFileId || reviewerNote) && (
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Evidence
                </Typography>
                <Typography variant="body2">
                  {[
                    sourceDocumentId ? `doc #${sourceDocumentId}` : null,
                    sourceFileId ? `file #${sourceFileId}` : null,
                    reviewerNote ? 'note attached' : null
                  ]
                    .filter(Boolean)
                    .join(' · ') || '—'}
                </Typography>
              </Box>
            )}
            {supersedesMappingId != null && (
              <Alert severity="warning" sx={{ py: 0 }}>
                Activating will supersede the current active declaration (#{supersedesMappingId}) for this device.
              </Alert>
            )}
            {isAssumption && (
              <FormControlLabel
                control={
                  <Checkbox checked={assumptionConfirmed} onChange={e => setAssumptionConfirmed(e.target.checked)} />
                }
                label="I confirm this is a reviewer assumption with no provider/source confirmation."
              />
            )}
            {assumptionBlocks && (
              <Alert severity="warning" sx={{ py: 0 }}>
                A reviewer-assumption declaration must be explicitly confirmed before it can be saved.
              </Alert>
            )}
            {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={mutation.isPending}>
          Cancel
        </Button>
        {activeStep === 0 ? (
          <Button variant="contained" onClick={() => setActiveStep(1)} disabled={!canContinue}>
            Next
          </Button>
        ) : (
          <>
            <Button onClick={() => setActiveStep(0)} disabled={mutation.isPending}>
              Back
            </Button>
            <Button onClick={() => mutation.mutate(false)} disabled={!canSubmit}>
              Save as draft
            </Button>
            <Button
              variant="contained"
              onClick={() => mutation.mutate(true)}
              disabled={!canSubmit}
              startIcon={mutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
            >
              Declare &amp; activate
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default WeatherDeclareDialog;
