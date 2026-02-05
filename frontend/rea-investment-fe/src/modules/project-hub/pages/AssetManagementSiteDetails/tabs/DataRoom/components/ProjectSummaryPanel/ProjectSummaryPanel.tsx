import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';
import Collapse from '@mui/material/Collapse';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import Link from '@mui/material/Link';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AssessmentIcon from '@mui/icons-material/Assessment';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import HelpIcon from '@mui/icons-material/Help';

import { ApiClient } from '../../../../../../../../api';
import { useNotify } from '../../../../../../../../contexts/notifications/notifications';
import { useAuth } from '../../../../../../../../contexts/auth/auth';

interface AgreementTerm {
  name: string;
  value: string | null;
  updated_at: string | null;
}

interface DiligenceDocument {
  id: number;
  name: string;
  files_count: number;
  display_name?: string | null;
  custom_name?: string | null;
}

interface ProjectSummaryPanelProps {
  siteId: number;
  companyId: number;
}

const STORAGE_KEY_PREFIX = 'project-summary-expanded-';

const statusIconMapping: Readonly<Record<string, React.ReactNode | undefined>> = Object.freeze({
  Equal: <CheckCircleIcon sx={{ color: theme => theme.efficiencyColors?.good || '#4CAF50', fontSize: 18 }} />,
  'Not Equal': <WarningRoundedIcon sx={{ color: theme => theme.alertSeverity?.high || '#F44336', fontSize: 18 }} />,
  Ambiguous: <WarningRoundedIcon sx={{ color: theme => theme.alertSeverity?.warning || '#FF9800', fontSize: 18 }} />,
  'N/A': <HelpIcon sx={{ color: '#00000042', fontSize: 18 }} />
});

interface SummaryItem {
  status: string;
  count: number;
}

export const ProjectSummaryPanel: React.FC<ProjectSummaryPanelProps> = ({ siteId, companyId }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const hasDiligenceView = user?.diligence_overview_access || user?.is_system_user;
  const hasDiligenceEdit = user?.is_system_user;

  const userId = user?.id ?? 'anonymous';
  const storageKey = `${STORAGE_KEY_PREFIX}${userId}-${siteId}`;
  const [isExpanded, setIsExpanded] = useState(() => {
    try {
      const stored = typeof window !== 'undefined' ? localStorage.getItem(storageKey) : null;
      return stored !== null ? stored === 'true' : true;
    } catch {
      return true;
    }
  });

  const [isCoTerminusCheckRunning, setIsCoTerminusCheckRunning] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<DiligenceDocument | null>(null);

  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem(storageKey, String(isExpanded));
      }
    } catch {
      // Ignore localStorage errors in SSR or restricted contexts
    }
  }, [isExpanded, storageKey]);

  const toggleExpanded = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  const { data: checkResultsData, isLoading: isLoadingCheckResults } = useQuery({
    queryFn: () => ApiClient.dueDiligence.getCoterminusCheckResults({ siteId }),
    queryKey: ['co-terminus', 'check-results', { siteId }],
    refetchInterval: isCoTerminusCheckRunning ? 15000 : false,
    enabled: hasDiligenceView
  });

  const { data: executionStatusData, isLoading: isLoadingExecutionStatus } = useQuery({
    queryFn: () => ApiClient.dueDiligence.getCoTerminusExecutionStatus({ siteId }),
    queryKey: ['co-terminus', 'execution-status', { siteId }],
    refetchInterval: isCoTerminusCheckRunning ? 15000 : 60000,
    enabled: hasDiligenceView
  });

  const {
    data: documentsData,
    isLoading: isLoadingDocuments,
    isFetching: isFetchingDocuments
  } = useQuery({
    queryFn: () => ApiClient.dueDiligence.getDocuments(siteId),
    queryKey: ['site', 'diligence', { siteId }],
    enabled: hasDiligenceView
  });

  const documentsWithFiles = useMemo(() => {
    if (!documentsData?.items) return [];
    const extractDocs = (sections: typeof documentsData.items): DiligenceDocument[] => {
      const docs: DiligenceDocument[] = [];
      for (const section of sections) {
        docs.push(...section.documents.filter(doc => doc.files_count > 0));
        if (section.related_sections?.length) {
          docs.push(...extractDocs(section.related_sections));
        }
      }
      return docs;
    };
    return extractDocs(documentsData.items);
  }, [documentsData?.items]);

  const { data: termData, isLoading: isLoadingTermData } = useQuery({
    queryFn: async () => {
      if (selectedDocument?.id) {
        return ApiClient.dueDiligence.getAgreementTerms(siteId, selectedDocument.id);
      }
      return { items: [] };
    },
    queryKey: ['agreement-term', { siteId, documentId: selectedDocument?.id }],
    enabled: !!selectedDocument?.id && hasDiligenceView
  });

  useEffect(() => {
    if (documentsWithFiles.length > 0 && !selectedDocument) {
      setSelectedDocument(documentsWithFiles[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentsWithFiles.length]);

  useEffect(() => {
    const { status } = executionStatusData ?? { status: null };
    switch (status) {
      case 'Processing':
        setIsCoTerminusCheckRunning(true);
        break;
      case 'Completed':
        setIsCoTerminusCheckRunning(false);
        queryClient.invalidateQueries({ queryKey: ['co-terminus', 'check-results', { siteId }] });
        break;
      case null:
      case 'Not Started':
        setIsCoTerminusCheckRunning(false);
        break;
      case 'Processing Failed':
      case 'Processing Start Failed':
      case 'Processing Timeout':
      case 'Unprocessable File':
        setIsCoTerminusCheckRunning(false);
        queryClient.invalidateQueries({ queryKey: ['co-terminus', 'check-results', { siteId }] });
        break;
    }
  }, [executionStatusData, queryClient, siteId]);

  const { mutateAsync: initCoTerminusCheck } = useMutation({
    mutationFn: () => ApiClient.dueDiligence.initCoTerminusCheck({ siteId }),
    onSuccess: () => {
      notify('Co-terminus check started');
      queryClient.invalidateQueries({ queryKey: ['co-terminus'] });
    },
    onError: (error: AxiosError<{ message?: string }>) => {
      notify(error.response?.data?.message || 'Failed to start check');
    }
  });

  const handleRunCheck = async () => {
    setIsCoTerminusCheckRunning(true);
    try {
      await initCoTerminusCheck();
    } catch {
      setIsCoTerminusCheckRunning(false);
    }
  };

  // Derived values (computed from query data, safe before conditional render)
  const summary: SummaryItem[] = useMemo(() => checkResultsData?.summary ?? [], [checkResultsData?.summary]);
  const hasResults = !!checkResultsData?.items?.length;
  const isProcessing = isCoTerminusCheckRunning || executionStatusData?.status === 'Processing';
  const hasError = [
    'Processing Failed',
    'Processing Start Failed',
    'Processing Timeout',
    'Unprocessable File'
  ].includes(executionStatusData?.status ?? '');

  const btnLabel = ['Processing', null, 'Not Started', undefined].includes(executionStatusData?.status)
    ? 'Run Check'
    : 'Rerun Check';

  // Project-level aggregation (collapsed summary - does NOT depend on selectedDocument)
  const projectLevelStats = useMemo(() => {
    const totalDocuments = documentsWithFiles.length;
    const notEqualCount = summary.find(s => s.status === 'Not Equal')?.count ?? 0;
    const ambiguousCount = summary.find(s => s.status === 'Ambiguous')?.count ?? 0;
    const equalCount = summary.find(s => s.status === 'Equal')?.count ?? 0;
    const naCount = summary.find(s => s.status === 'N/A')?.count ?? 0;
    const mismatchCount = notEqualCount + ambiguousCount;
    const totalTermsChecked = equalCount + notEqualCount + ambiguousCount + naCount;
    const termsPromoted = hasResults ? totalTermsChecked : 0;
    return { totalDocuments, termsPromoted, mismatchCount, equalCount, hasCoTerminusResults: hasResults };
  }, [documentsWithFiles.length, summary, hasResults]);

  // Tri-state health derivation
  const projectHealth = useMemo(() => {
    const { mismatchCount, termsPromoted, hasCoTerminusResults } = projectLevelStats;
    if (hasError || (hasCoTerminusResults && mismatchCount > 0)) {
      return { label: 'Attention Needed', color: 'error' as const };
    }
    if (hasCoTerminusResults && mismatchCount === 0 && termsPromoted > 0) {
      return { label: 'Healthy', color: 'success' as const };
    }
    return { label: 'In Progress', color: 'warning' as const };
  }, [projectLevelStats, hasError]);

  // Collapsed indicator labels (project-level)
  const documentsLabel = projectLevelStats.totalDocuments > 0 ? `${projectLevelStats.totalDocuments}` : '—';
  const termsCollapsedLabel =
    projectLevelStats.termsPromoted > 0 ? `${projectLevelStats.termsPromoted} promoted` : 'Not promoted';

  const coTerminusCollapsedLabel = (() => {
    if (isProcessing) return 'Running';
    if (!hasResults) return 'Not run';
    if (projectLevelStats.mismatchCount > 0) {
      return `${projectLevelStats.mismatchCount} mismatch${projectLevelStats.mismatchCount > 1 ? 'es' : ''}`;
    }
    return 'OK';
  })();

  const coTerminusCollapsedColor = (() => {
    if (isProcessing) return 'warning';
    if (!hasResults) return 'default';
    if (projectLevelStats.mismatchCount > 0) return 'error';
    return 'success';
  })();

  if (!hasDiligenceView) {
    return null;
  }

  return (
    <Paper
      elevation={0}
      sx={{
        border: '1px solid #E0E0E0',
        borderRadius: 1,
        mb: 3,
        overflow: 'hidden'
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          py: 1.5,
          bgcolor: '#FAFAFA',
          borderBottom: isExpanded ? '1px solid #E0E0E0' : 'none',
          cursor: 'pointer'
        }}
        onClick={toggleExpanded}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <AssessmentIcon color="primary" fontSize="small" />
          <Typography variant="subtitle1" fontWeight={600}>
            Project Summary
          </Typography>
          {!isExpanded && (
            <Stack direction="row" spacing={1.5} sx={{ ml: 2 }} alignItems="center">
              <Chip
                label={`Due Diligence: ${projectHealth.label}`}
                size="small"
                color={projectHealth.color}
                sx={{ height: 20, fontSize: '11px', fontWeight: 600, '& .MuiChip-label': { px: 1 } }}
              />
              <Typography variant="caption" color="text.secondary">
                Documents: {documentsLabel}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Terms: {termsCollapsedLabel}
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}
              >
                Co-terminus:{' '}
                <Chip
                  label={coTerminusCollapsedLabel}
                  size="small"
                  color={coTerminusCollapsedColor as 'default' | 'success' | 'warning' | 'error'}
                  sx={{ height: 18, fontSize: '10px', '& .MuiChip-label': { px: 0.75 } }}
                />
              </Typography>
            </Stack>
          )}
        </Stack>
        <IconButton
          size="small"
          onClick={e => {
            e.stopPropagation();
            toggleExpanded();
          }}
        >
          {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>

      <Collapse in={isExpanded}>
        <Box sx={{ p: 2 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={7}>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Terms & Values
              </Typography>

              {isLoadingDocuments ? (
                <Box display="flex" alignItems="center" py={2}>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    Loading documents...
                  </Typography>
                </Box>
              ) : documentsWithFiles.length > 0 ? (
                <>
                  <Box sx={{ mb: 2 }}>
                    <Autocomplete
                      value={selectedDocument}
                      options={documentsWithFiles}
                      size="small"
                      getOptionLabel={option => option.display_name || option.custom_name || option.name}
                      loading={isFetchingDocuments}
                      getOptionKey={option => option.id}
                      sx={{ maxWidth: 300 }}
                      renderInput={params => (
                        <TextField
                          {...params}
                          placeholder="Select document"
                          variant="outlined"
                          InputProps={{
                            ...params.InputProps,
                            endAdornment: (
                              <>
                                {isFetchingDocuments ? <CircularProgress size={16} /> : null}
                                {params.InputProps.endAdornment}
                              </>
                            )
                          }}
                        />
                      )}
                      onChange={(_, newValue) => setSelectedDocument(newValue)}
                    />
                  </Box>

                  {selectedDocument && (
                    <Box
                      sx={{ border: '1px solid #0000001F', borderRadius: 1, p: 2, maxHeight: 200, overflowY: 'auto' }}
                    >
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                        <Typography variant="body2" fontWeight={600}>
                          {selectedDocument.display_name || selectedDocument.custom_name || selectedDocument.name}
                        </Typography>
                        <Link
                          component="button"
                          variant="caption"
                          underline="hover"
                          onClick={() =>
                            window.open(
                              `/due-diligence/companies/${companyId}/sites/${siteId}/due-diligence/${selectedDocument.id}`,
                              '_blank'
                            )
                          }
                        >
                          View Details
                        </Link>
                      </Box>
                      {isLoadingTermData ? (
                        <Typography variant="body2" color="text.secondary">
                          Loading...
                        </Typography>
                      ) : termData?.items?.length ? (
                        <Stack spacing={1}>
                          {termData.items.slice(0, 5).map((term: AgreementTerm) => (
                            <Box key={term.name}>
                              <Typography variant="caption" fontWeight={600} color="text.secondary">
                                {term.name}
                              </Typography>
                              <Typography variant="body2">{term.value || 'N/A'}</Typography>
                            </Box>
                          ))}
                          {termData.items.length > 5 && (
                            <Typography variant="caption" color="text.secondary">
                              +{termData.items.length - 5} more fields
                            </Typography>
                          )}
                        </Stack>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          No extracted terms available. Parse the document to extract terms.
                        </Typography>
                      )}
                    </Box>
                  )}
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No documents with uploaded files.
                </Typography>
              )}
            </Grid>

            <Grid item xs={12} md={5}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="subtitle2" fontWeight={600}>
                  Cross-Document Checks
                </Typography>
                {hasDiligenceEdit && (
                  <Button
                    size="small"
                    variant="contained"
                    disabled={isLoadingExecutionStatus || isProcessing}
                    startIcon={isProcessing ? <CircularProgress size={14} color="inherit" /> : null}
                    onClick={e => {
                      e.stopPropagation();
                      handleRunCheck();
                    }}
                  >
                    {btnLabel}
                  </Button>
                )}
              </Stack>

              {hasError && (
                <Alert severity="error" sx={{ mb: 1, py: 0 }}>
                  Check failed. Please try again.
                </Alert>
              )}

              {isLoadingCheckResults && !hasResults ? (
                <Box display="flex" justifyContent="center" py={3}>
                  <CircularProgress size={24} />
                </Box>
              ) : hasResults ? (
                <Box sx={{ bgcolor: '#0000000A', borderRadius: 1, p: 1.5 }}>
                  {summary.map(item => (
                    <Stack
                      key={item.status}
                      direction="row"
                      alignItems="center"
                      justifyContent="space-between"
                      py={0.5}
                      sx={{ '&:not(:last-child)': { borderBottom: '1px solid #E0E0E0' } }}
                    >
                      <Stack direction="row" alignItems="center" spacing={1}>
                        {statusIconMapping[item.status]}
                        <Typography variant="body2">
                          {item.status === 'Equal'
                            ? 'Terms Match'
                            : item.status === 'Not Equal'
                              ? "Terms Don't Match"
                              : item.status === 'Ambiguous'
                                ? 'Uncertain'
                                : item.status === 'N/A'
                                  ? 'Data Incomplete'
                                  : item.status}
                        </Typography>
                      </Stack>
                      <Typography variant="body2" fontWeight={600}>
                        {item.count}
                      </Typography>
                    </Stack>
                  ))}
                </Box>
              ) : (
                <Box
                  sx={{
                    border: '1px solid #0000001F',
                    borderRadius: 1,
                    p: 2,
                    textAlign: 'center'
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    No checks run yet. Run a check to compare terms across documents.
                  </Typography>
                </Box>
              )}
            </Grid>
          </Grid>
        </Box>
      </Collapse>
    </Paper>
  );
};

export default ProjectSummaryPanel;
