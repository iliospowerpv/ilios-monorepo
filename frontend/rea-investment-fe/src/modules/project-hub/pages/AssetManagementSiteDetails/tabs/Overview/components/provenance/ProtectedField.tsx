import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Link from '@mui/material/Link';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined';
import FactCheckOutlinedIcon from '@mui/icons-material/FactCheckOutlined';

import type { ReconciliationRow, ReconciliationValue } from '../../../../../../../../api';
import { TextBox } from '../InformationCardBase/InformationCardBase.styles';
import { ProvenanceNote, ProvenanceVariant } from './BaselineProvenance';
import StatusChip from '../../../Reconciliation/components/StatusChip';
import { blockingMeta, missingDependencyLabel, ACTIONS_IN_DATA_ROOM } from '../../../Reconciliation/utils';
import { useReconciliationProvenance } from './ReconciliationProvenanceContext';
import { resolveProtectedValue } from './reconciliationFieldMap';

/**
 * Phase 3 — LIVE reconciliation status note for a protected Overview field.
 *
 * Reuses the Reconciliation tab's `StatusChip`, `blockingMeta` and
 * `missingDependencyLabel` so the language and severity colours stay identical
 * across surfaces. Renders the status ladder chip, a single most-severe blocking
 * chip, the backend-supplied "Next: <required_action>" caption, any
 * missing-dependency chips, and read-only deep links. The Data Room link is only
 * shown when the field's next step actually happens in the Data Room
 * (acceptance / promotion); baseline-activation statuses show the action text
 * without a dead link. The Reconciliation link is always available (the provider
 * only renders this note for users who can view reconciliation). Read-only — no
 * mutations, no writes.
 */
const LiveStatusNote: React.FC<{ row: ReconciliationRow; siteId: number | null }> = ({ row, siteId }) => {
  const blocking = row.blocking_level ? blockingMeta(row.blocking_level) : null;
  const deps = Array.isArray(row.missing_dependencies) ? row.missing_dependencies : [];
  const showDataRoomLink = Boolean(row.required_action) && siteId !== null && ACTIONS_IN_DATA_ROOM.has(row.status);

  return (
    <Box sx={{ mt: '4px', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', alignItems: 'center', gap: '4px' }}>
        <StatusChip status={row.status} label={row.status_label} description={row.status_explanation} />
        {blocking && (
          <Chip
            label={blocking.label}
            color={blocking.color}
            size="small"
            variant="filled"
            sx={{ height: 18, fontSize: '0.625rem', '& .MuiChip-label': { px: '6px' } }}
          />
        )}
      </Box>

      {row.required_action && (
        <Typography variant="caption" sx={{ color: 'text.secondary', textAlign: 'right', lineHeight: 1.3 }}>
          <Box component="span" sx={{ fontWeight: 600 }}>
            Next:
          </Box>{' '}
          {row.required_action}
        </Typography>
      )}

      {deps.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: '2px' }}>
          {deps.map(dep => (
            <Chip
              key={dep}
              label={missingDependencyLabel(dep)}
              size="small"
              variant="outlined"
              sx={{ height: 16, fontSize: '0.5625rem', '& .MuiChip-label': { px: '5px' } }}
            />
          ))}
        </Box>
      )}

      {siteId !== null && (
        <Stack direction="row" spacing={1.5} flexWrap="wrap" justifyContent="flex-end">
          {showDataRoomLink && (
            <Link
              component={RouterLink}
              to={`/project-hub/projects/${siteId}/data-room`}
              variant="caption"
              underline="hover"
              sx={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}
            >
              <FolderOutlinedIcon sx={{ fontSize: '0.8125rem' }} />
              Open Data Room
            </Link>
          )}
          <Link
            component={RouterLink}
            to={`/project-hub/projects/${siteId}/reconciliation`}
            variant="caption"
            underline="hover"
            sx={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}
          >
            <FactCheckOutlinedIcon sx={{ fontSize: '0.8125rem' }} />
            View Reconciliation
          </Link>
        </Stack>
      )}
    </Box>
  );
};

interface ProtectedFieldProps {
  /** Overview field key (see OVERVIEW_FIELD_TO_RECON). */
  field: string;
  /** Static-fallback provenance note variant when no live row is available. */
  variant: ProvenanceVariant;
  /** The card's own current value, used as the display fallback (zero regression). */
  fallback: ReconciliationValue | undefined;
  /**
   * Formats the resolved value for display. Receives the value chosen by the
   * precedence resolver (which is the card fallback when no live truth exists),
   * so passing the card's existing formatter reproduces today's rendering
   * exactly. Defaults to a plain string render.
   */
  format?: (value: ReconciliationValue) => React.ReactNode;
}

/**
 * Renders a protected (read-only) Overview field value bound to LIVE
 * reconciliation truth-state when the user can view reconciliation and a backing
 * row exists; otherwise it degrades to the existing static provenance label and
 * the card's own value. It NEVER makes the field editable and performs no writes.
 */
export const ProtectedField: React.FC<ProtectedFieldProps> = ({ field, variant, fallback, format }) => {
  const { canView, getRow, siteId } = useReconciliationProvenance();
  const row = getRow(field);
  const { value, qualifier } = resolveProtectedValue(row, fallback, canView);

  const display = format ? format(value ?? null) : value === null || value === undefined ? '' : String(value);
  const showLive = canView && Boolean(row);

  return (
    <>
      <TextBox>{display}</TextBox>
      {qualifier && (
        <Box sx={{ mt: '2px', color: 'text.secondary', fontSize: '0.6875rem', fontStyle: 'italic', lineHeight: 1.3 }}>
          {qualifier}
        </Box>
      )}
      {showLive && row ? <LiveStatusNote row={row} siteId={siteId} /> : <ProvenanceNote variant={variant} />}
    </>
  );
};

export default ProtectedField;
