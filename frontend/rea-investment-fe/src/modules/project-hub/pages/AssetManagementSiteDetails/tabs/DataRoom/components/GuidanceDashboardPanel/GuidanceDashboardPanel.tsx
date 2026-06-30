import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';
import Collapse from '@mui/material/Collapse';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import InsightsIcon from '@mui/icons-material/Insights';

import { ApiClient, ExpectedDocument, GuidancePromotionStatus, GuidanceStage } from '../../../../../../../../api';

interface GuidanceDashboardPanelProps {
  siteId: number;
  onAddMissingDocument?: (doc: ExpectedDocument, stage: GuidanceStage) => void;
}

const PROMOTION_LABELS: Record<
  GuidancePromotionStatus,
  { label: string; color: 'default' | 'info' | 'warning' | 'success' }
> = {
  none: { label: 'No files', color: 'default' },
  not_started: { label: 'Not promoted', color: 'warning' },
  in_progress: { label: 'In progress', color: 'info' },
  complete: { label: 'Complete', color: 'success' }
};

export const GuidanceDashboardPanel: React.FC<GuidanceDashboardPanelProps> = ({ siteId, onAddMissingDocument }) => {
  const [expanded, setExpanded] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['site', 'data-room-guidance', { siteId }],
    queryFn: () => ApiClient.dueDiligence.getDataRoomGuidance(siteId),
    enabled: !!siteId && Number.isSafeInteger(siteId)
  });

  const stages = data?.items ?? [];
  const totals = stages.reduce(
    (acc, stage) => {
      acc.expected += stage.expected;
      acc.present += stage.present;
      acc.missing += stage.missing;
      return acc;
    },
    { expected: 0, present: 0, missing: 0 }
  );

  return (
    <Paper elevation={0} sx={{ p: 2, mb: 3, border: '1px solid #E0E0E0' }}>
      <Box
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        sx={{ cursor: 'pointer' }}
        onClick={() => setExpanded(prev => !prev)}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <InsightsIcon color="primary" />
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Data Room Guidance
          </Typography>
          {!isLoading && !error && stages.length > 0 && (
            <Typography variant="body2" color="text.secondary">
              {totals.present}/{totals.expected} expected present · {totals.missing} missing
            </Typography>
          )}
        </Box>
        <IconButton size="small" aria-label={expanded ? 'Collapse data room guidance' : 'Expand data room guidance'}>
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>

      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <Box mt={2}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            A read-only, per-stage view of completeness derived from your existing documents, versions and promotions.
            It is advisory only and changes nothing.
          </Typography>

          {isLoading ? (
            <Box display="flex" alignItems="center" justifyContent="center" py={3}>
              <CircularProgress size={28} />
            </Box>
          ) : error ? (
            <Alert severity="error">Failed to load the guidance dashboard. Please try again.</Alert>
          ) : stages.length === 0 ? (
            <Alert severity="info">No stages with expected documents are defined for this project.</Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Stage</TableCell>
                    <Tooltip title="Documents expected by the catalog for this stage">
                      <TableCell align="right">Expected</TableCell>
                    </Tooltip>
                    <Tooltip title="Expected documents that have at least one uploaded version">
                      <TableCell align="right">Present</TableCell>
                    </Tooltip>
                    <Tooltip title="Expected documents with no uploaded version yet">
                      <TableCell align="right">Missing</TableCell>
                    </Tooltip>
                    <Tooltip title="Promoted documents that received a newer version since promotion">
                      <TableCell align="right">Needs Update</TableCell>
                    </Tooltip>
                    <Tooltip title="Expected documents flagged optional">
                      <TableCell align="right">Optional</TableCell>
                    </Tooltip>
                    <Tooltip title="Archived documents in this stage">
                      <TableCell align="right">Archived</TableCell>
                    </Tooltip>
                    <Tooltip title="Total uploaded file versions across live documents">
                      <TableCell align="right">Versions</TableCell>
                    </Tooltip>
                    <TableCell>Promotion</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {stages.map(stage => {
                    const promotion = PROMOTION_LABELS[stage.promotion_status] ?? PROMOTION_LABELS.none;
                    return (
                      <TableRow key={stage.section_key} hover>
                        <TableCell sx={{ fontWeight: 500 }}>{stage.section_name}</TableCell>
                        <TableCell align="right">{stage.expected}</TableCell>
                        <TableCell align="right">{stage.present}</TableCell>
                        <TableCell align="right">
                          {stage.missing > 0 ? (
                            <Box>
                              <Box component="span" sx={{ color: 'warning.main', fontWeight: 600 }}>
                                {stage.missing}
                              </Box>
                              {onAddMissingDocument && stage.missing_documents.length > 0 && (
                                <Stack spacing={0.25} sx={{ mt: 0.5, alignItems: 'flex-end' }}>
                                  {stage.missing_documents.map(doc => (
                                    <Tooltip
                                      key={`${stage.section_key}-${doc.kind}`}
                                      title={`Add "${doc.name}" to ${stage.section_name}`}
                                    >
                                      <Link
                                        component="button"
                                        type="button"
                                        variant="caption"
                                        underline="hover"
                                        onClick={() => onAddMissingDocument(doc, stage)}
                                        data-testid={`guidance-add-missing-${stage.section_key}-${doc.kind}`}
                                        sx={{ textAlign: 'right', lineHeight: 1.3 }}
                                      >
                                        + {doc.name}
                                      </Link>
                                    </Tooltip>
                                  ))}
                                </Stack>
                              )}
                            </Box>
                          ) : (
                            stage.missing
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {stage.needs_update > 0 ? (
                            <Box component="span" sx={{ color: 'info.main', fontWeight: 600 }}>
                              {stage.needs_update}
                            </Box>
                          ) : (
                            stage.needs_update
                          )}
                        </TableCell>
                        <TableCell align="right">{stage.optional}</TableCell>
                        <TableCell align="right">{stage.archived}</TableCell>
                        <TableCell align="right">{stage.version_count}</TableCell>
                        <TableCell>
                          <Chip size="small" label={promotion.label} color={promotion.color} variant="outlined" />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default GuidanceDashboardPanel;
