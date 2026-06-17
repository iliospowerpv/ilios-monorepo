import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import Box from '@mui/material/Box';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Table from '@mui/material/Table';
import TableHead from '@mui/material/TableHead';
import TableBody from '@mui/material/TableBody';
import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import { ApiClient } from '../../../../../../../api';
import type { PromotionDiff, PromotionDiffChange, ReconciliationRow } from '../../../../../../../api';
import { useNotify } from '../../../../../../../contexts/notifications/notifications';
import { PLACEHOLDER, promotionErrorMessage } from '../utils';

interface PromoteVersionDialogProps {
  open: boolean;
  siteId: number;
  /** The accepted-not-promoted row the user launched from. */
  row: ReconciliationRow;
  onClose: () => void;
  /** Called after a successful promotion (before the dialog closes). */
  onPromoted?: () => void;
}

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
      const highlighted = change.field_name === launchedField;
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

export const PromoteVersionDialog: React.FC<PromoteVersionDialogProps> = ({
  open,
  siteId,
  row,
  onClose,
  onPromoted
}) => {
  const notify = useNotify();
  const queryClient = useQueryClient();

  const fileId = row.document_version_id;
  const documentId = row.document_id;
  const canQuery = open && typeof fileId === 'number';

  const [notes, setNotes] = React.useState('');
  const [reconfirmNeeded, setReconfirmNeeded] = React.useState(false);
  // Tracks the diff the user has actually looked at, so a confirm-time refetch
  // that returns a different blast radius forces a re-review (R2 in the spec).
  const reviewedKeyRef = React.useRef<string | null>(null);

  const {
    data: diff,
    isLoading: isDiffLoading,
    isError: isDiffError,
    refetch
  } = useQuery({
    queryKey: ['site', 'assumptions', 'promotion-diff', { siteId, fileId }],
    queryFn: () => ApiClient.assumptions.getPromotionDiff(siteId, fileId as number),
    enabled: canQuery,
    // Always reflect the live blast radius — never a cached diff.
    staleTime: 0,
    gcTime: 0,
    retry: false as const,
    refetchOnWindowFocus: false
  });

  // Reset transient state whenever the dialog opens for a (possibly new) row.
  React.useEffect(() => {
    if (open) {
      setNotes('');
      setReconfirmNeeded(false);
      reviewedKeyRef.current = null;
    }
  }, [open, fileId]);

  // Record the first diff the user sees as "reviewed".
  React.useEffect(() => {
    if (diff && reviewedKeyRef.current === null) {
      reviewedKeyRef.current = JSON.stringify(diff);
    }
  }, [diff]);

  const promote = useMutation({
    mutationFn: () =>
      ApiClient.assumptions.promoteVersion(siteId, {
        document_id: documentId as number,
        file_id: fileId as number,
        notes: notes.trim() ? notes.trim() : null
      }),
    onSuccess: result => {
      queryClient.invalidateQueries({ queryKey: ['site', 'reconciliation', { siteId }] });
      queryClient.invalidateQueries({ queryKey: ['site', 'assumptions', 'facts', { siteId }] });
      queryClient.invalidateQueries({ queryKey: ['site', 'assumptions', 'promotions', { siteId }] });
      notify(
        `Promoted ${result.facts_promoted} value${result.facts_promoted === 1 ? '' : 's'} to current assumptions. ` +
          'The active baseline was NOT updated — building or activating a baseline is a separate step.'
      );
      onPromoted?.();
      onClose();
    },
    onError: error => {
      notify(promotionErrorMessage(error));
    }
  });

  const handleConfirm = async () => {
    if (typeof fileId !== 'number' || typeof documentId !== 'number') return;
    // Re-fetch the diff at confirm time and require a re-review if it changed.
    const result = await refetch();
    const fresh = result.data;
    if (!fresh) {
      notify('Could not verify the latest changes; please try again.');
      return;
    }
    const freshKey = JSON.stringify(fresh);
    if (reviewedKeyRef.current !== freshKey) {
      reviewedKeyRef.current = freshKey;
      setReconfirmNeeded(true);
      return;
    }
    setReconfirmNeeded(false);
    promote.mutate();
  };

  const hasChanges = Boolean(diff?.has_changes);
  const confirmDisabled = isDiffLoading || isDiffError || !hasChanges || promote.isPending;

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" data-testid="promote-dialog">
      <DialogTitle sx={{ fontWeight: 600 }}>Promote to current assumptions</DialogTitle>
      <DialogContent dividers>
        <Alert severity="warning" sx={{ mb: 2 }} data-testid="promote-scope-warning">
          <AlertTitle>This promotes the whole document version</AlertTitle>
          Promoting this version will update <strong>every accepted value on it</strong> — not just{' '}
          <strong>{row.display_label}</strong>. Review the complete set of changes below before confirming. Acceptance and
          overrides are unchanged; this only moves accepted values into the project&apos;s active assumptions and does{' '}
          <strong>not</strong> build or activate a baseline.
        </Alert>

        {isDiffLoading && (
          <Box display="flex" alignItems="center" justifyContent="center" py={4} data-testid="promote-diff-loading">
            <CircularProgress size={32} />
          </Box>
        )}

        {isDiffError && (
          <Alert severity="error" data-testid="promote-diff-error">
            <AlertTitle>Couldn&apos;t load the change preview</AlertTitle>
            We couldn&apos;t load what this promotion would change. Please close this dialog and try again.
          </Alert>
        )}

        {!isDiffLoading && !isDiffError && diff && (
          <>
            {reconfirmNeeded && (
              <Alert severity="info" sx={{ mb: 2 }} data-testid="promote-reconfirm-warning">
                The change preview was updated since you opened this dialog. Review the current changes below, then confirm
                again to proceed.
              </Alert>
            )}

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
                          <ChangeRows changes={groupChanges} launchedField={row.display_label} />
                        </TableBody>
                      </React.Fragment>
                    );
                  })}
                </Table>
              </TableContainer>
            )}

            <TextField
              label="Promotion notes (optional)"
              value={notes}
              onChange={event => setNotes(event.target.value)}
              fullWidth
              multiline
              minRows={2}
              maxRows={5}
              inputProps={{ maxLength: 2000, 'data-testid': 'promote-notes' }}
              sx={{ mt: 2 }}
              disabled={!hasChanges || promote.isPending}
              helperText="Saved to the promotion audit trail."
            />
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" onClick={onClose} disabled={promote.isPending} data-testid="promote-cancel-btn">
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={confirmDisabled}
          data-testid="promote-confirm-btn"
        >
          {promote.isPending ? 'Promoting…' : 'Promote this version'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PromoteVersionDialog;
