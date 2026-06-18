import React from 'react';

import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import Typography from '@mui/material/Typography';

import type { PromotionDiff, PromotionDiffChange } from '../../api';

const PLACEHOLDER = '—';

const CHANGE_GROUPS: { type: string; title: string; informational?: boolean }[] = [
  { type: 'changed', title: 'Changed — replaces the current active value' },
  { type: 'added', title: 'Added — becomes a new active value' },
  {
    type: 'removed',
    title: 'No longer carried by this version',
    informational: true
  }
];

const valueOrPlaceholder = (value: string | null): string =>
  value === null || value === undefined || value === '' ? PLACEHOLDER : value;

const ChangeRows: React.FC<{ changes: PromotionDiffChange[]; launchedField: string }> = ({
  changes,
  launchedField
}) => (
  <>
    {changes.map(change => {
      const highlighted = launchedField !== '' && change.field_name === launchedField;
      return (
        <TableRow
          key={`${change.type}-${change.field_id}-${change.field_name}`}
          data-testid="promote-change-row"
          selected={highlighted}
        >
          <TableCell sx={{ fontWeight: highlighted ? 600 : 400 }}>{change.field_name}</TableCell>
          <TableCell sx={{ whiteSpace: 'nowrap' }}>{valueOrPlaceholder(change.current_value)}</TableCell>
          <TableCell sx={{ whiteSpace: 'nowrap' }}>{valueOrPlaceholder(change.new_value)}</TableCell>
        </TableRow>
      );
    })}
  </>
);

/**
 * Presentational, read-only diff preview: summary chips plus a grouped
 * changed / added / removed table. `removed` rows are informational only —
 * promotion never retires them. Shared verbatim by every promote launcher.
 */
export const PromotionDiffTable: React.FC<{ diff: PromotionDiff; launchedFieldLabel?: string | null }> = ({
  diff,
  launchedFieldLabel
}) => {
  const hasChanges = Boolean(diff.has_changes);
  const launchedField = launchedFieldLabel ?? '';

  return (
    <>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }} data-testid="promote-summary">
        <Chip size="small" color="primary" variant="outlined" label={`Changed: ${diff.summary.changed}`} />
        <Chip size="small" color="success" variant="outlined" label={`Added: ${diff.summary.added}`} />
        <Chip size="small" variant="outlined" label={`No longer carried: ${diff.summary.removed}`} />
      </Box>

      {!hasChanges ? (
        <Alert severity="info" data-testid="promote-no-changes">
          This version&apos;s accepted values already match the current assumptions. There is nothing to promote.
        </Alert>
      ) : (
        <TableContainer>
          <Table size="small" data-testid="promote-diff-table">
            {CHANGE_GROUPS.map(group => {
              const groupChanges = diff.changes.filter(change => change.type === group.type);
              if (groupChanges.length === 0) return null;
              return (
                <React.Fragment key={group.type}>
                  <TableHead>
                    <TableRow>
                      <TableCell colSpan={3} sx={{ backgroundColor: 'action.hover', fontWeight: 600 }}>
                        {group.title}
                        {group.informational && (
                          <Typography
                            component="div"
                            variant="caption"
                            color="text.secondary"
                            data-testid="promote-removed-note"
                          >
                            Informational only — this version no longer carries these fields. Promotion does{' '}
                            <strong>not</strong> delete or retire them.
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>Field</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Current</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{group.informational ? 'Dropped' : 'New'}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <ChangeRows changes={groupChanges} launchedField={launchedField} />
                  </TableBody>
                </React.Fragment>
              );
            })}
          </Table>
        </TableContainer>
      )}
    </>
  );
};

export default PromotionDiffTable;
