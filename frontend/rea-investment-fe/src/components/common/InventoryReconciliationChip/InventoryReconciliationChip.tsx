import React from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import type { InventoryReconciliationStatus, InventoryReconciliationSummary } from '../../../types/telemetryV2';

export type InventoryChipColor = 'default' | 'info' | 'success' | 'warning' | 'error';

export interface InventoryStatusMeta {
  label: string;
  color: InventoryChipColor;
  severity: 'neutral' | 'info' | 'good' | 'attention' | 'blocking';
}

/**
 * Display metadata for the G1->G8 reconciliation headline. The backend remains
 * the source of truth for `status_label` / `status_explanation`; this map only
 * picks an honest chip colour and a fallback label for unknown future statuses.
 *
 * Shared by the per-site Reconciliation panel and the list/card status chip so
 * the two surfaces can never disagree on colour or fallback label.
 */
export const INVENTORY_STATUS_META: Record<string, InventoryStatusMeta> = {
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

export const inventoryStatusMeta = (status: InventoryReconciliationStatus): InventoryStatusMeta =>
  INVENTORY_STATUS_META[status] || {
    label: String(status).replace(/_/g, ' '),
    color: 'default',
    severity: 'neutral'
  };

/** Neutral chip shown while loading or when a summary is unavailable. */
const UNAVAILABLE_LABEL = 'Status unavailable';
const LOADING_LABEL = 'Checking…';

interface InventoryReconciliationChipProps {
  /**
   * The site's compact reconciliation summary. `undefined`/`null` means the
   * summary is not available for this site (auth-omitted, missing, or errored) —
   * the chip renders a neutral "Status unavailable" and NEVER fabricates a match.
   */
  summary?: InventoryReconciliationSummary | null;
  /** While the batch summary request is in flight. Renders a neutral loading chip. */
  loading?: boolean;
  /** The batch summary request failed. Renders a neutral "Status unavailable" chip. */
  error?: boolean;
  size?: 'small' | 'medium';
}

/**
 * Read-only inventory reconciliation status chip for list/card surfaces.
 *
 * Strictly informational: it displays the backend-provided `status_label` and a
 * blocking indicator, with a tooltip carrying the backend `status_explanation`.
 * It performs no fetching itself (consumers pass the already-fetched summary) and
 * never mutates anything. Loading and unavailable states are neutral and honest —
 * an absent summary is shown as "Status unavailable", not "Matched".
 */
export const InventoryReconciliationChip: React.FC<InventoryReconciliationChipProps> = ({
  summary,
  loading = false,
  error = false,
  size = 'small'
}) => {
  if (loading) {
    return (
      <Tooltip title="Checking reconciliation status…">
        <Chip
          size={size}
          color="default"
          variant="outlined"
          label={LOADING_LABEL}
          data-testid="inventory-reconciliation-chip"
          data-state="loading"
        />
      </Tooltip>
    );
  }

  if (error || !summary) {
    return (
      <Tooltip title="Reconciliation status unavailable.">
        <Chip
          size={size}
          color="default"
          variant="outlined"
          label={UNAVAILABLE_LABEL}
          data-testid="inventory-reconciliation-chip"
          data-state="unavailable"
        />
      </Tooltip>
    );
  }

  const meta = inventoryStatusMeta(summary.status);
  const label = summary.status_label || meta.label;

  const tooltip = (
    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
        {label}
      </Typography>
      {summary.status_explanation ? (
        <Typography variant="body2" sx={{ mt: 0.5 }}>
          {summary.status_explanation}
        </Typography>
      ) : null}
      {summary.has_blocking_mismatch ? (
        <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
          Blocking issues present.
        </Typography>
      ) : null}
      {summary.weather_dependency_unsatisfied ? (
        <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
          Weather dependency unresolved.
        </Typography>
      ) : null}
      {summary.open_actionable_mismatch_count > 0 ? (
        <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
          Open actionable mismatches: {summary.open_actionable_mismatch_count}
        </Typography>
      ) : null}
    </Box>
  );

  return (
    <Tooltip title={tooltip}>
      <Box
        sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}
        data-testid="inventory-reconciliation-chip"
        data-state="ready"
        data-status={summary.status}
      >
        <Chip size={size} color={meta.color} label={label} />
        {summary.has_blocking_mismatch ? (
          <Box
            component="span"
            data-testid="inventory-reconciliation-blocking-indicator"
            sx={theme => ({
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: theme.palette.error.main,
              flexShrink: 0
            })}
          />
        ) : null}
      </Box>
    </Tooltip>
  );
};

export default InventoryReconciliationChip;
