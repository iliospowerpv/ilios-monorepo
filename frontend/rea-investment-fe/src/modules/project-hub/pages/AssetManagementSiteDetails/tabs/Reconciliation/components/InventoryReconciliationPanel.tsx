import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Tooltip from '@mui/material/Tooltip';
import Button from '@mui/material/Button';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined';
import TaskAltOutlinedIcon from '@mui/icons-material/TaskAltOutlined';

import { ApiClient } from '../../../../../../../api';
import { useAuth } from '../../../../../../../contexts/auth/auth';
import type {
  DiagnosticBlockingLevel,
  InventoryAckListResponse,
  InventoryAckPolicy,
  InventoryAckResponse,
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

const MIN_REASON_LEN = 10;
const MAX_REASON_LEN = 1000;

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

/** A mismatch is acknowledgeable only when its policy is one of the two ack-able. */
const isAcknowledgeablePolicy = (policy: InventoryAckPolicy): boolean =>
  policy === 'acknowledgeable_with_required_followup' || policy === 'acknowledgeable_non_blocking';

/**
 * Best-effort extraction of a human message from an axios-style error. The
 * backend returns FastAPI `detail` (string) for most cases and a structured
 * object for stale-version conflicts; fall back to a generic message.
 */
const extractErrorMessage = (err: unknown, fallback: string): string => {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (detail && typeof detail === 'object') {
    const msg = (detail as { message?: unknown }).message;
    if (typeof msg === 'string' && msg.trim()) return msg;
  }
  return fallback;
};

const inventoryReconciliationQuery = (siteId: number, enabled: boolean) => ({
  queryKey: ['site', 'inventory-reconciliation', { siteId }],
  queryFn: () => ApiClient.telemetryV2.getSiteInventoryReconciliation(siteId),
  enabled,
  retry: false as const
});

const inventoryAcknowledgementsQuery = (siteId: number, enabled: boolean) => ({
  queryKey: ['site', 'inventory-reconciliation-acks', { siteId }],
  queryFn: () => ApiClient.telemetryV2.listInventoryAcknowledgements(siteId),
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

interface MismatchTableProps {
  rows: InventoryMismatch[];
  canAcknowledge: boolean;
  ackBySignature: Map<string, InventoryAckResponse>;
  pendingSignature: string | null;
  onAcknowledge: (mismatch: InventoryMismatch) => void;
  onRevoke: (mismatch: InventoryMismatch, ack: InventoryAckResponse) => void;
}

const MismatchAckCell: React.FC<{
  mismatch: InventoryMismatch;
  canAcknowledge: boolean;
  ack?: InventoryAckResponse;
  pending: boolean;
  onAcknowledge: (mismatch: InventoryMismatch) => void;
  onRevoke: (mismatch: InventoryMismatch, ack: InventoryAckResponse) => void;
}> = ({ mismatch, canAcknowledge, ack, pending, onAcknowledge, onRevoke }) => {
  // Already acknowledged for the current engine version.
  if (mismatch.is_acknowledged) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, alignItems: 'flex-start' }}>
        <Tooltip
          title={
            ack
              ? `Acknowledged ${formatDateTime(ack.acknowledged_at)}${
                  ack.acknowledgement_reason ? ` — ${ack.acknowledgement_reason}` : ''
                }`
              : 'Acknowledged'
          }
          arrow
        >
          <Chip size="small" color="success" icon={<TaskAltOutlinedIcon />} label="Acknowledged" variant="outlined" />
        </Tooltip>
        {canAcknowledge && ack ? (
          <Button
            size="small"
            color="inherit"
            disabled={pending}
            onClick={() => onRevoke(mismatch, ack)}
            data-testid={`inventory-ack-revoke-${mismatch.mismatch_signature}`}
          >
            Revoke
          </Button>
        ) : null}
      </Box>
    );
  }

  // Blocking mismatches can never be acknowledged.
  if (mismatch.acknowledgement_policy === 'not_acknowledgeable_blocking') {
    return (
      <Tooltip
        title="This mismatch blocks expected-performance math and can never be signed off — it must be resolved."
        arrow
      >
        <Chip size="small" color="error" variant="outlined" label="Cannot acknowledge" />
      </Tooltip>
    );
  }

  // Informational findings are not actionable, so there is nothing to sign off.
  if (!isAcknowledgeablePolicy(mismatch.acknowledgement_policy)) {
    return (
      <Typography variant="caption" color="text.secondary">
        {PLACEHOLDER}
      </Typography>
    );
  }

  if (!canAcknowledge) {
    return (
      <Typography variant="caption" color="text.secondary">
        Asset edit required
      </Typography>
    );
  }

  return (
    <Button
      size="small"
      variant="outlined"
      disabled={pending}
      onClick={() => onAcknowledge(mismatch)}
      data-testid={`inventory-ack-${mismatch.mismatch_signature}`}
    >
      Acknowledge
    </Button>
  );
};

const MismatchTable: React.FC<MismatchTableProps> = ({
  rows,
  canAcknowledge,
  ackBySignature,
  pendingSignature,
  onAcknowledge,
  onRevoke
}) => (
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
          <TableCell>Sign-off</TableCell>
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
              <TableCell>
                <MismatchAckCell
                  mismatch={m}
                  canAcknowledge={canAcknowledge}
                  ack={ackBySignature.get(m.mismatch_signature)}
                  pending={pendingSignature === m.mismatch_signature}
                  onAcknowledge={onAcknowledge}
                  onRevoke={onRevoke}
                />
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
  const queryClient = useQueryClient();
  const { user } = useAuth();
  // Acknowledging an inventory mismatch is an Asset.edit reviewer action. The
  // backend still enforces the real Asset.edit dependency, so a non-reviewer
  // sees read-only chips instead of action buttons.
  const canAcknowledge = Boolean(user?.is_system_user) || Boolean(user?.role?.permissions?.['Asset Management']?.edit);

  const { data, isLoading, error } = useQuery<InventoryReconciliationResponse>(
    inventoryReconciliationQuery(isValidId ? siteId : -1, isValidId)
  );
  const { data: ackList } = useQuery<InventoryAckListResponse>(
    inventoryAcknowledgementsQuery(isValidId ? siteId : -1, isValidId)
  );

  // Map active acknowledgements by signature so a row can offer Revoke and show
  // who/when. Only `is_active` acks are surfaced (a stale-version ack reads as
  // expired and the matching mismatch is no longer `is_acknowledged`).
  const ackBySignature = React.useMemo(() => {
    const map = new Map<string, InventoryAckResponse>();
    (ackList?.acknowledgements ?? []).forEach(ack => {
      if (ack.is_active && !map.has(ack.mismatch_signature)) {
        map.set(ack.mismatch_signature, ack);
      }
    });
    return map;
  }, [ackList]);

  const [ackTarget, setAckTarget] = React.useState<InventoryMismatch | null>(null);
  const [revokeTarget, setRevokeTarget] = React.useState<{
    mismatch: InventoryMismatch;
    ack: InventoryAckResponse;
  } | null>(null);
  const [reason, setReason] = React.useState('');
  const [actionError, setActionError] = React.useState<string | null>(null);

  const invalidate = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['site', 'inventory-reconciliation', { siteId }] });
    queryClient.invalidateQueries({ queryKey: ['site', 'inventory-reconciliation-acks', { siteId }] });
  }, [queryClient, siteId]);

  const createMutation = useMutation({
    mutationFn: (vars: { mismatch: InventoryMismatch; reason: string }) =>
      ApiClient.telemetryV2.createInventoryAcknowledgement(siteId, {
        mismatch_signature: vars.mismatch.mismatch_signature,
        reconciliation_version: data?.reconciliation_version ?? '',
        acknowledgement_reason: vars.reason
      }),
    onSuccess: () => {
      invalidate();
      setAckTarget(null);
      setReason('');
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError(extractErrorMessage(err, "Couldn't acknowledge this mismatch. Please try again."));
    }
  });

  const revokeMutation = useMutation({
    mutationFn: (vars: { ackId: number; reason: string }) =>
      ApiClient.telemetryV2.revokeInventoryAcknowledgement(siteId, vars.ackId, { revocation_reason: vars.reason }),
    onSuccess: () => {
      invalidate();
      setRevokeTarget(null);
      setReason('');
      setActionError(null);
    },
    onError: (err: unknown) => {
      setActionError(extractErrorMessage(err, "Couldn't revoke this acknowledgement. Please try again."));
    }
  });

  const openAcknowledge = (mismatch: InventoryMismatch) => {
    setReason('');
    setActionError(null);
    setAckTarget(mismatch);
  };

  const openRevoke = (mismatch: InventoryMismatch, ack: InventoryAckResponse) => {
    setReason('');
    setActionError(null);
    setRevokeTarget({ mismatch, ack });
  };

  const closeDialogs = () => {
    if (createMutation.isPending || revokeMutation.isPending) return;
    setAckTarget(null);
    setRevokeTarget(null);
    setReason('');
    setActionError(null);
  };

  const trimmedReason = reason.trim();
  const reasonValid = trimmedReason.length >= MIN_REASON_LEN && trimmedReason.length <= MAX_REASON_LEN;
  const reasonError =
    reason.length > 0 && !reasonValid
      ? trimmedReason.length < MIN_REASON_LEN
        ? `Please enter at least ${MIN_REASON_LEN} characters.`
        : `Please keep this under ${MAX_REASON_LEN} characters.`
      : undefined;

  const pendingSignature = createMutation.isPending
    ? (ackTarget?.mismatch_signature ?? null)
    : revokeMutation.isPending
      ? (revokeTarget?.mismatch.mismatch_signature ?? null)
      : null;

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
        their reviewer-confirmed mappings. This view is strictly informational — it never maps, creates, converts, or
        promotes anything. Reviewers with Asset edit rights may sign off on actionable mismatches as accepted
        exceptions; sign-off records a rationale only and changes no devices, mappings, facts, telemetry, or baselines.
        Modules are counted but never compared to per-device telemetry counts.
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
            Acknowledged exceptions: <strong>{data.acknowledged_exception_count}</strong>
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
          <MismatchTable
            rows={data.mismatches}
            canAcknowledge={canAcknowledge}
            ackBySignature={ackBySignature}
            pendingSignature={pendingSignature}
            onAcknowledge={openAcknowledge}
            onRevoke={openRevoke}
          />
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

      <Dialog
        open={Boolean(ackTarget)}
        onClose={closeDialogs}
        fullWidth
        maxWidth="sm"
        data-testid="inventory-ack-dialog"
      >
        <DialogTitle>Acknowledge mismatch</DialogTitle>
        <DialogContent>
          <DialogContentText component="div" sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {ackTarget?.title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {ackTarget?.detail}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              Signing off records this as a reviewed, accepted exception. It changes no devices, mappings, facts,
              telemetry, or baselines, and it can be revoked later.
            </Typography>
          </DialogContentText>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={3}
            label="Reason for acknowledgement"
            placeholder="Explain why this mismatch is an acceptable exception"
            value={reason}
            onChange={e => setReason(e.target.value)}
            error={Boolean(reasonError)}
            helperText={reasonError ?? `${trimmedReason.length}/${MAX_REASON_LEN}`}
            inputProps={{ 'data-testid': 'inventory-ack-reason' }}
          />
          {actionError ? (
            <Alert severity="error" sx={{ mt: 2 }} data-testid="inventory-ack-dialog-error">
              {actionError}
            </Alert>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialogs} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="contained"
            disabled={!reasonValid || createMutation.isPending || !ackTarget}
            onClick={() => ackTarget && createMutation.mutate({ mismatch: ackTarget, reason: trimmedReason })}
            data-testid="inventory-ack-confirm"
          >
            {createMutation.isPending ? 'Acknowledging…' : 'Acknowledge'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(revokeTarget)}
        onClose={closeDialogs}
        fullWidth
        maxWidth="sm"
        data-testid="inventory-revoke-dialog"
      >
        <DialogTitle>Revoke acknowledgement</DialogTitle>
        <DialogContent>
          <DialogContentText component="div" sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {revokeTarget?.mismatch.title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Revoking returns this mismatch to open/actionable. The original acknowledgement is kept as immutable
              history.
            </Typography>
          </DialogContentText>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={3}
            label="Reason for revocation"
            placeholder="Explain why this acknowledgement no longer applies"
            value={reason}
            onChange={e => setReason(e.target.value)}
            error={Boolean(reasonError)}
            helperText={reasonError ?? `${trimmedReason.length}/${MAX_REASON_LEN}`}
            inputProps={{ 'data-testid': 'inventory-revoke-reason' }}
          />
          {actionError ? (
            <Alert severity="error" sx={{ mt: 2 }} data-testid="inventory-revoke-dialog-error">
              {actionError}
            </Alert>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialogs} disabled={revokeMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="warning"
            disabled={!reasonValid || revokeMutation.isPending || !revokeTarget}
            onClick={() => revokeTarget && revokeMutation.mutate({ ackId: revokeTarget.ack.id, reason: trimmedReason })}
            data-testid="inventory-revoke-confirm"
          >
            {revokeMutation.isPending ? 'Revoking…' : 'Revoke'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default InventoryReconciliationPanel;
