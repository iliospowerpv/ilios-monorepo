import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Tooltip from '@mui/material/Tooltip';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined';

import { ApiClient } from '../../../../../../../api';
import type {
  DiagnosticBlockingLevel,
  InventoryClassCount,
  InventoryMismatch,
  InventoryNextAction,
  InventoryReconciliationResponse,
  InventoryReconciliationStatus
} from '../../../../../../../types/telemetryV2';
import { formatDateTime, PLACEHOLDER } from '../utils';

type ChipColor = 'default' | 'info' | 'success' | 'warning' | 'error';

interface StatusMeta {
  label: string;
  color: ChipColor;
  severity: 'neutral' | 'info' | 'good' | 'attention' | 'blocking';
}

/**
 * Display metadata for the G1->G8 reconciliation headline. The backend remains
 * the source of truth for `status_label` / `status_explanation`; this map only
 * picks an honest chip colour and a fallback label for unknown future statuses.
 */
const STATUS_META: Record<string, StatusMeta> = {
  telemetry_not_connected: { label: 'Telemetry not connected', color: 'default', severity: 'neutral' },
  documented_inventory_incomplete: {
    label: 'Documented inventory incomplete',
    color: 'warning',
    severity: 'attention'
  },
  telemetry_connected_no_devices: {
    label: 'Connected — no devices discovered',
    color: 'warning',
    severity: 'attention'
  },
  telemetry_inventory_incomplete_or_stale: {
    label: 'Telemetry inventory incomplete / stale',
    color: 'warning',
    severity: 'attention'
  },
  needs_reconciliation: { label: 'Needs reconciliation', color: 'error', severity: 'blocking' },
  mapping_complete_with_acknowledged_exceptions: {
    label: 'Mapping complete (acknowledged exceptions)',
    color: 'info',
    severity: 'info'
  },
  partially_matched: { label: 'Partially matched', color: 'warning', severity: 'attention' },
  matched: { label: 'Matched', color: 'success', severity: 'good' }
};

const statusMeta = (status: InventoryReconciliationStatus): StatusMeta =>
  STATUS_META[status] || {
    label: String(status).replace(/_/g, ' '),
    color: 'default',
    severity: 'neutral'
  };

interface BlockingMeta {
  label: string;
  color: ChipColor;
}

/** Mirrors the backend `DiagnosticBlockingLevel` (most -> least severe). */
const BLOCKING_META: Record<string, BlockingMeta> = {
  blocks_calculation: { label: 'Blocks calculation', color: 'error' },
  lowers_confidence: { label: 'Lowers confidence', color: 'warning' },
  informational: { label: 'Informational', color: 'default' }
};

const blockingMeta = (level: DiagnosticBlockingLevel): BlockingMeta =>
  BLOCKING_META[level] || { label: String(level).replace(/_/g, ' '), color: 'default' };

const EQUIPMENT_CLASS_LABELS: Record<string, string> = {
  inverter: 'Inverters',
  module: 'Modules',
  production_meter: 'Production meters',
  weather_sensor: 'Weather sensors',
  gateway: 'Gateways / loggers',
  comms: 'Comms / modems',
  virtual: 'Virtual aggregates',
  other: 'Other'
};

const equipmentClassLabel = (value: string | null): string => {
  if (!value) return 'All equipment';
  return EQUIPMENT_CLASS_LABELS[value] || value.replace(/_/g, ' ');
};

const CATEGORY_LABELS: Record<string, string> = {
  quantity_mismatch: 'Quantity mismatch',
  missing_telemetry_counterpart: 'Missing telemetry counterpart',
  undocumented_telemetry_device: 'Undocumented telemetry device',
  model_capacity_mismatch: 'Model / capacity mismatch',
  cardinality_exception: 'Cardinality exception',
  device_role_mismatch: 'Device role mismatch',
  weather_expected_dependency: 'Weather expected dependency',
  telemetry_freshness: 'Telemetry freshness',
  design_as_built_version: 'Design / as-built version'
};

const categoryLabel = (value: string): string => CATEGORY_LABELS[value] || value.replace(/_/g, ' ');

const formatCount = (value: number | null | undefined): string =>
  value === null || value === undefined ? PLACEHOLDER : String(value);

const inventoryReconciliationQuery = (siteId: number, enabled: boolean) => ({
  queryKey: ['site', 'inventory-reconciliation', { siteId }],
  queryFn: () => ApiClient.telemetryV2.getSiteInventoryReconciliation(siteId),
  enabled,
  retry: false as const
});

interface InventoryReconciliationPanelProps {
  siteId: number;
}

const ClassCountTable: React.FC<{ rows: InventoryClassCount[] }> = ({ rows }) => (
  <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
    <Table size="small" aria-label="inventory class counts">
      <TableHead>
        <TableRow>
          <TableCell>Equipment class</TableCell>
          <TableCell align="right">Documented</TableCell>
          <TableCell align="right">iliOS rows</TableCell>
          <TableCell align="right">Discovered</TableCell>
          <TableCell align="right">Mapped</TableCell>
          <TableCell>Basis</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map(row => (
          <TableRow key={row.equipment_class}>
            <TableCell>
              {equipmentClassLabel(row.equipment_class)}
              {row.note ? (
                <Tooltip title={row.note} arrow>
                  <Typography
                    component="span"
                    variant="caption"
                    color="text.secondary"
                    sx={{ ml: 0.5, cursor: 'help' }}
                  >
                    (?)
                  </Typography>
                </Tooltip>
              ) : null}
            </TableCell>
            <TableCell align="right">{formatCount(row.documented_count)}</TableCell>
            <TableCell align="right">{formatCount(row.ilios_row_count)}</TableCell>
            <TableCell align="right">{formatCount(row.discovered_count)}</TableCell>
            <TableCell align="right">{formatCount(row.mapped_count)}</TableCell>
            <TableCell>
              <Typography variant="caption" color="text.secondary">
                {row.reconciliation_basis}
              </Typography>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </TableContainer>
);

const MismatchTable: React.FC<{ rows: InventoryMismatch[] }> = ({ rows }) => (
  <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
    <Table size="small" aria-label="inventory mismatches">
      <TableHead>
        <TableRow>
          <TableCell>Finding</TableCell>
          <TableCell>Category</TableCell>
          <TableCell>Class</TableCell>
          <TableCell>Impact</TableCell>
          <TableCell>Documented</TableCell>
          <TableCell>Observed</TableCell>
          <TableCell>Provenance</TableCell>
          <TableCell>Next step</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map(m => {
          const impact = blockingMeta(m.blocking_level);
          const provenance = m.recorded_provenance;
          const provenanceText = provenance
            ? [
                provenance.has_telemetry_mapping ? 'mapped' : 'unmapped',
                provenance.source_provider,
                provenance.external_device_type
              ]
                .filter(Boolean)
                .join(' · ')
            : PLACEHOLDER;
          return (
            <TableRow key={m.mismatch_signature}>
              <TableCell>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {m.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {m.detail}
                </Typography>
                {m.device_name ? (
                  <Typography variant="caption" color="text.secondary" display="block">
                    Device: {m.device_name}
                  </Typography>
                ) : null}
              </TableCell>
              <TableCell>{categoryLabel(m.category)}</TableCell>
              <TableCell>{equipmentClassLabel(m.equipment_class)}</TableCell>
              <TableCell>
                <Chip size="small" color={impact.color} label={impact.label} variant="outlined" />
              </TableCell>
              <TableCell>{m.documented_value ?? PLACEHOLDER}</TableCell>
              <TableCell>{m.observed_value ?? PLACEHOLDER}</TableCell>
              <TableCell>
                <Typography variant="caption" color="text.secondary">
                  {provenanceText}
                </Typography>
                {m.reconciliation_inference ? (
                  <Tooltip
                    title="Inferred origin — a non-definitive assessment, never authoritative documentation."
                    arrow
                  >
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ cursor: 'help' }}>
                      inferred: {String(m.reconciliation_inference).replace(/_/g, ' ')}
                    </Typography>
                  </Tooltip>
                ) : null}
              </TableCell>
              <TableCell>
                <Typography variant="caption" color="text.secondary">
                  {m.recommended_action ?? PLACEHOLDER}
                </Typography>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  </TableContainer>
);

const NextActionsList: React.FC<{ actions: InventoryNextAction[] }> = ({ actions }) => (
  <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
    <Typography variant="subtitle2" sx={{ mb: 1 }}>
      Recommended next steps
    </Typography>
    <Box component="ul" sx={{ pl: 3, m: 0 }}>
      {actions.map((action, idx) => {
        const impact = blockingMeta(action.blocking_level);
        return (
          <li key={`${action.title}-${idx}`}>
            <Typography variant="body2" component="span" sx={{ fontWeight: 600 }}>
              {action.title}
            </Typography>{' '}
            <Chip size="small" color={impact.color} label={impact.label} variant="outlined" sx={{ ml: 0.5 }} />
            <Typography variant="caption" color="text.secondary" display="block">
              {action.detail}
            </Typography>
          </li>
        );
      })}
    </Box>
  </Paper>
);

const Header: React.FC<{ generatedAt?: string }> = ({ generatedAt }) => (
  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
    <Inventory2OutlinedIcon color="primary" />
    <Typography variant="h6" sx={{ fontWeight: 600 }}>
      Device Inventory Reconciliation
    </Typography>
    <Chip label="Read-only" size="small" variant="outlined" sx={{ ml: 1 }} />
    {generatedAt ? (
      <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
        Generated {formatDateTime(generatedAt)}
      </Typography>
    ) : null}
  </Box>
);

export const InventoryReconciliationPanel: React.FC<InventoryReconciliationPanelProps> = ({ siteId }) => {
  const isValidId = Number.isSafeInteger(siteId) && siteId > 0;
  const { data, isLoading, error } = useQuery<InventoryReconciliationResponse>(
    inventoryReconciliationQuery(isValidId ? siteId : -1, isValidId)
  );

  if (isLoading) {
    return (
      <Box sx={{ mt: 4 }} data-testid="inventory-reconciliation-panel">
        <Header />
        <Box display="flex" alignItems="center" justifyContent="center" py={4}>
          <CircularProgress size={32} />
        </Box>
      </Box>
    );
  }

  if (error) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    return (
      <Box sx={{ mt: 4 }} data-testid="inventory-reconciliation-panel">
        <Header />
        <Alert
          severity={status === 401 || status === 403 ? 'warning' : 'error'}
          data-testid="inventory-reconciliation-error"
        >
          <AlertTitle>
            {status === 401 || status === 403 ? 'Access restricted' : "Couldn't load inventory reconciliation"}
          </AlertTitle>
          {status === 401 || status === 403
            ? 'You don\u2019t have permission to view the device inventory reconciliation for this project.'
            : 'Something went wrong while loading the device inventory reconciliation. Please try again later.'}
        </Alert>
      </Box>
    );
  }

  if (!data) {
    return null;
  }

  const meta = statusMeta(data.status);
  const hasMismatches = data.mismatches.length > 0;
  const hasActions = data.next_actions.length > 0;
  const hasClassCounts = data.class_counts.length > 0;

  return (
    <Box sx={{ mt: 4 }} data-testid="inventory-reconciliation-panel">
      <Header generatedAt={data.generated_at} />

      <Alert severity="info" sx={{ mb: 2 }} data-testid="inventory-reconciliation-disclaimer">
        Compares the approved documented inventory (active project facts) against the telemetry-discovered devices and
        their reviewer-confirmed mappings. This view is strictly informational — it never maps, creates, acknowledges,
        converts, or promotes anything. Modules are counted but never compared to per-device telemetry counts.
      </Alert>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }} data-testid="inventory-reconciliation-headline">
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Chip
            color={meta.color}
            label={data.status_label || meta.label}
            data-testid="inventory-reconciliation-status-chip"
          />
          {data.has_blocking_mismatch ? (
            <Chip size="small" color="error" variant="outlined" label="Blocking mismatch" />
          ) : null}
          {data.weather_dependency_unsatisfied ? (
            <Chip size="small" color="error" variant="outlined" label="Weather dependency unsatisfied" />
          ) : null}
          {data.discovery_stale ? (
            <Chip size="small" color="warning" variant="outlined" label="Discovery stale" />
          ) : null}
          {data.documented_inventory_incomplete ? (
            <Chip size="small" color="warning" variant="outlined" label="Documented inventory incomplete" />
          ) : null}
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {data.status_explanation}
        </Typography>
        <Box sx={{ display: 'flex', gap: 3, mt: 1.5, flexWrap: 'wrap' }}>
          <Typography variant="caption" color="text.secondary">
            iliOS devices: <strong>{data.total_ilios_devices}</strong>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Discovered devices: <strong>{data.total_discovered_devices}</strong>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Open actionable mismatches: <strong>{data.open_actionable_mismatch_count}</strong>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Informational: <strong>{data.informational_mismatch_count}</strong>
          </Typography>
          {data.discovery_last_synced_at ? (
            <Typography variant="caption" color="text.secondary">
              Last discovery sync: <strong>{formatDateTime(data.discovery_last_synced_at)}</strong>
            </Typography>
          ) : null}
        </Box>
      </Paper>

      {hasClassCounts ? (
        <>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Equipment class counts
          </Typography>
          <ClassCountTable rows={data.class_counts} />
        </>
      ) : null}

      {hasMismatches ? (
        <>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Findings ({data.mismatches.length})
          </Typography>
          <MismatchTable rows={data.mismatches} />
        </>
      ) : (
        <Alert severity="success" sx={{ mb: 2 }} data-testid="inventory-reconciliation-no-mismatches">
          No inventory mismatches detected for this project.
        </Alert>
      )}

      {hasActions ? <NextActionsList actions={data.next_actions} /> : null}

      {data.notes.length > 0 ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Notes
          </Typography>
          <Box component="ul" sx={{ pl: 3, m: 0 }}>
            {data.notes.map((note, idx) => (
              <li key={idx}>
                <Typography variant="caption" color="text.secondary">
                  {note}
                </Typography>
              </li>
            ))}
          </Box>
        </Paper>
      ) : null}
    </Box>
  );
};

export default InventoryReconciliationPanel;
