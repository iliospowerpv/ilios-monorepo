import React, { useState, useCallback, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Stepper,
  Step,
  StepLabel,
  Box,
  Typography,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Select,
  MenuItem,
  FormControl,
  Chip,
  LinearProgress,
  IconButton,
  Stack,
  Divider,
  Checkbox,
  FormControlLabel
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import CloseIcon from '@mui/icons-material/Close';
import DownloadIcon from '@mui/icons-material/Download';
import { ApiClient } from '../../../api';
import type {
  ColumnMapping,
  ParsedFileResponse,
  ValidateResponse,
  ImportResultResponse
} from '../../../api/project-import';
import { TARGET_FIELDS } from '../../../api/project-import';

const STEPS = ['Upload File', 'Map Fields', 'Validate', 'Import'];

interface ProjectImportWizardProps {
  open: boolean;
  onClose: () => void;
  companyId: number;
  companyName: string;
  onImportComplete?: () => void;
}

const ProjectImportWizard: React.FC<ProjectImportWizardProps> = ({
  open,
  onClose,
  companyId,
  companyName,
  onImportComplete
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [parseResult, setParseResult] = useState<ParsedFileResponse | null>(null);
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [validateResult, setValidateResult] = useState<ValidateResponse | null>(null);
  const [importResult, setImportResult] = useState<ImportResultResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetState = useCallback(() => {
    setActiveStep(0);
    setFile(null);
    setParseResult(null);
    setMappings({});
    setValidateResult(null);
    setImportResult(null);
    setLoading(false);
    setError(null);
    setSkipDuplicates(true);
    setDragOver(false);
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onClose();
  }, [onClose, resetState]);

  const handleFileDrop = useCallback(
    async (droppedFile: File) => {
      const ext = droppedFile.name.split('.').pop()?.toLowerCase();
      if (!ext || !['csv', 'xlsx', 'xls'].includes(ext)) {
        setError('Please upload a .csv or .xlsx file');
        return;
      }
      setFile(droppedFile);
      setError(null);
      setLoading(true);

      try {
        const result = await ApiClient.projectImport.parseFile(companyId, droppedFile);
        setParseResult(result);
        setMappings(result.suggested_mappings);
        setActiveStep(1);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to parse file');
      } finally {
        setLoading(false);
      }
    },
    [companyId]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) handleFileDrop(droppedFile);
    },
    [handleFileDrop]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) handleFileDrop(selectedFile);
    },
    [handleFileDrop]
  );

  const handleMappingChange = useCallback((header: string, targetField: string) => {
    setMappings(prev => {
      const updated = { ...prev };
      if (targetField === '') {
        delete updated[header];
      } else {
        updated[header] = targetField;
      }
      return updated;
    });
  }, []);

  const handleValidate = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);

    const columnMappings: ColumnMapping[] = Object.entries(mappings).map(([source, target]) => ({
      source_column: source,
      target_field: target
    }));

    try {
      const result = await ApiClient.projectImport.validateImport(companyId, file, columnMappings);
      setValidateResult(result);
      setActiveStep(2);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Validation failed');
    } finally {
      setLoading(false);
    }
  }, [file, mappings, companyId]);

  const handleImport = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);

    const columnMappings: ColumnMapping[] = Object.entries(mappings).map(([source, target]) => ({
      source_column: source,
      target_field: target
    }));

    try {
      const result = await ApiClient.projectImport.executeImport(companyId, file, columnMappings, skipDuplicates);
      setImportResult(result);
      setActiveStep(3);
      if (result.imported > 0 && onImportComplete) {
        onImportComplete();
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Import failed');
    } finally {
      setLoading(false);
    }
  }, [file, mappings, companyId, skipDuplicates, onImportComplete]);

  const handleDownloadErrors = useCallback(() => {
    if (!importResult) return;
    const errorRows = importResult.results.filter(r => r.status === 'failed' || r.status === 'skipped');
    if (!errorRows.length) return;

    let csv = 'Row,Status,Project Name,Field,Error\n';
    errorRows.forEach(row => {
      if (row.errors.length) {
        row.errors.forEach(err => {
          csv += `${row.row},"${row.status}","${row.project_name || ''}","${err.field}","${err.message}"\n`;
        });
      } else {
        csv += `${row.row},"${row.status}","${row.project_name || ''}","",""\n`;
      }
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `import-errors-${importResult.batch_id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [importResult]);

  const usedTargets = new Set(Object.values(mappings));
  const requiredFields = ['project_name', 'address', 'city', 'state', 'zip_code'];
  const mappedRequired = requiredFields.filter(f => usedTargets.has(f));
  const canValidate = mappedRequired.length === requiredFields.length;

  const renderUploadStep = () => (
    <Box sx={{ textAlign: 'center', py: 4 }}>
      <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
        Importing projects under <strong>{companyName}</strong>
      </Typography>
      <Box
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        sx={{
          border: '2px dashed',
          borderColor: dragOver ? 'primary.main' : 'divider',
          borderRadius: 2,
          p: 6,
          cursor: 'pointer',
          bgcolor: dragOver ? 'action.hover' : 'background.default',
          transition: 'all 0.2s',
          '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' }
        }}
      >
        <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          Drag & drop your file here
        </Typography>
        <Typography variant="body2" color="text.secondary">
          or click to browse — supports .csv and .xlsx
        </Typography>
      </Box>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx"
        onChange={handleFileInput}
        style={{ display: 'none' }}
      />
      {file && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Selected: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)
        </Alert>
      )}
    </Box>
  );

  const renderMappingStep = () => {
    if (!parseResult) return null;

    return (
      <Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {parseResult.total_rows} rows detected in <strong>{file?.name}</strong>. Map your spreadsheet columns to
          project fields below.
        </Typography>

        {!canValidate && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            Required fields not yet mapped:{' '}
            {requiredFields
              .filter(f => !usedTargets.has(f))
              .map(f => TARGET_FIELDS.find(t => t.value === f)?.label || f)
              .join(', ')}
          </Alert>
        )}

        <TableContainer component={Paper} variant="outlined" sx={{ mb: 3, maxHeight: 300 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Spreadsheet Column</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Sample Value</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Map To</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {parseResult.headers.map(header => {
                const sampleVal = parseResult.sample_rows[0]?.[header] || '';
                const currentMapping = mappings[header] || '';
                return (
                  <TableRow key={header}>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {header}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                      >
                        {sampleVal}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <FormControl size="small" fullWidth>
                        <Select
                          value={currentMapping}
                          onChange={e => handleMappingChange(header, e.target.value)}
                          displayEmpty
                        >
                          <MenuItem value="">
                            <em>Skip this column</em>
                          </MenuItem>
                          {TARGET_FIELDS.map(tf => (
                            <MenuItem
                              key={tf.value}
                              value={tf.value}
                              disabled={usedTargets.has(tf.value) && currentMapping !== tf.value}
                            >
                              {tf.label}
                              {requiredFields.includes(tf.value) ? ' *' : ''}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        {parseResult.sample_rows.length > 0 && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Preview (first {Math.min(parseResult.sample_rows.length, 3)} rows)
            </Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 200 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    {parseResult.headers.map(h => (
                      <TableCell key={h} sx={{ fontWeight: 600, fontSize: '0.75rem' }}>
                        {h}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {parseResult.sample_rows.slice(0, 3).map((row, idx) => (
                    <TableRow key={idx}>
                      {parseResult.headers.map(h => (
                        <TableCell key={h} sx={{ fontSize: '0.75rem' }}>
                          {row[h] || ''}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </Box>
    );
  };

  const renderValidateStep = () => {
    if (!validateResult) return null;

    const { total_rows, valid_rows, invalid_rows, duplicate_rows, row_results } = validateResult;
    const errorRows = row_results.filter(r => r.status !== 'valid');

    return (
      <Box>
        <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
          <Paper variant="outlined" sx={{ p: 2, flex: 1, textAlign: 'center' }}>
            <Typography variant="h4">{total_rows}</Typography>
            <Typography variant="body2" color="text.secondary">
              Total Rows
            </Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2, flex: 1, textAlign: 'center' }}>
            <Typography variant="h4" color="success.main">
              {valid_rows}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Valid
            </Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2, flex: 1, textAlign: 'center' }}>
            <Typography variant="h4" color="error.main">
              {invalid_rows}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Invalid
            </Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2, flex: 1, textAlign: 'center' }}>
            <Typography variant="h4" color="warning.main">
              {duplicate_rows}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Duplicates
            </Typography>
          </Paper>
        </Stack>

        {duplicate_rows > 0 && (
          <FormControlLabel
            control={<Checkbox checked={skipDuplicates} onChange={e => setSkipDuplicates(e.target.checked)} />}
            label="Skip duplicate projects during import"
            sx={{ mb: 2 }}
          />
        )}

        {errorRows.length > 0 && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Issues Found
            </Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 250 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Row</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Project</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Issues</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {errorRows.map((row, idx) => (
                    <TableRow key={idx}>
                      <TableCell>{row.row}</TableCell>
                      <TableCell>{row.project_name || '—'}</TableCell>
                      <TableCell>
                        <Chip label={row.status} size="small" color={row.status === 'invalid' ? 'error' : 'warning'} />
                      </TableCell>
                      <TableCell>
                        {row.errors.map((e, i) => (
                          <Typography key={i} variant="body2" color="error.main">
                            {e.message}
                          </Typography>
                        ))}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}

        {valid_rows === 0 && (
          <Alert severity="error" sx={{ mt: 2 }}>
            No valid rows to import. Please go back and fix your field mappings or spreadsheet data.
          </Alert>
        )}
      </Box>
    );
  };

  const renderResultStep = () => {
    if (!importResult) return null;

    const hasErrors = importResult.failed > 0 || importResult.skipped > 0;

    return (
      <Box sx={{ textAlign: 'center', py: 2 }}>
        {importResult.imported > 0 ? (
          <CheckCircleIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
        ) : (
          <ErrorIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
        )}

        <Typography variant="h5" gutterBottom>
          Import Complete
        </Typography>

        <Stack direction="row" spacing={2} justifyContent="center" sx={{ mb: 3 }}>
          <Paper variant="outlined" sx={{ p: 2, minWidth: 100 }}>
            <Typography variant="h4" color="success.main">
              {importResult.imported}
            </Typography>
            <Typography variant="body2">Imported</Typography>
          </Paper>
          {importResult.skipped > 0 && (
            <Paper variant="outlined" sx={{ p: 2, minWidth: 100 }}>
              <Typography variant="h4" color="warning.main">
                {importResult.skipped}
              </Typography>
              <Typography variant="body2">Skipped</Typography>
            </Paper>
          )}
          {importResult.failed > 0 && (
            <Paper variant="outlined" sx={{ p: 2, minWidth: 100 }}>
              <Typography variant="h4" color="error.main">
                {importResult.failed}
              </Typography>
              <Typography variant="body2">Failed</Typography>
            </Paper>
          )}
        </Stack>

        {hasErrors && (
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleDownloadErrors} sx={{ mb: 2 }}>
            Download Error Report
          </Button>
        )}

        <Typography variant="body2" color="text.secondary">
          Batch ID: {importResult.batch_id}
        </Typography>
      </Box>
    );
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return renderUploadStep();
      case 1:
        return renderMappingStep();
      case 2:
        return renderValidateStep();
      case 3:
        return renderResultStep();
      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth PaperProps={{ sx: { minHeight: 500 } }}>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6">Import Projects</Typography>
        <IconButton onClick={handleClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <Divider />

      <Box sx={{ px: 3, pt: 2 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {STEPS.map(label => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Box>

      <DialogContent sx={{ pt: 2 }}>
        {loading && <LinearProgress sx={{ mb: 2 }} />}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        {renderStepContent()}
      </DialogContent>

      <Divider />

      <DialogActions sx={{ px: 3, py: 2 }}>
        {activeStep === 3 ? (
          <Button variant="contained" onClick={handleClose}>
            Done
          </Button>
        ) : (
          <>
            <Button onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            {activeStep === 1 && (
              <>
                <Button onClick={() => setActiveStep(0)} disabled={loading}>
                  Back
                </Button>
                <Button variant="contained" onClick={handleValidate} disabled={!canValidate || loading}>
                  Validate
                </Button>
              </>
            )}
            {activeStep === 2 && (
              <>
                <Button onClick={() => setActiveStep(1)} disabled={loading}>
                  Back
                </Button>
                <Button
                  variant="contained"
                  onClick={handleImport}
                  disabled={loading || (validateResult?.valid_rows ?? 0) === 0}
                  color="primary"
                >
                  Start Import ({validateResult?.valid_rows ?? 0} projects)
                </Button>
              </>
            )}
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ProjectImportWizard;
