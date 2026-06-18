import React from 'react';

import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import { useNotify } from '../../contexts/notifications/notifications';
import { PromotionDiffTable } from './PromotionDiffTable';
import { usePromotionDiff } from './usePromotionDiff';
import { usePromoteVersion } from './usePromoteVersion';
import { promotionErrorMessage } from './promotionErrorMessage';
import type { PromoteVersionContext } from './types';

interface PromoteVersionDialogProps {
  open: boolean;
  siteId: number;
  /** What is being promoted: ids + optional display-only document-version metadata. */
  context: PromoteVersionContext;
  onClose: () => void;
  /**
   * Called after a successful promotion (before the dialog closes) so the launching
   * surface can invalidate its own caches (e.g. the Data Room document terms).
   */
  onPromoted?: () => void;
}

const formatContextDate = (value: string): string => {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
};

/**
 * Generic, launcher-agnostic promote dialog. It always promotes a whole file
 * version (all-or-nothing) and is reused verbatim by the Reconciliation table and
 * the Data Room document modal. The optional `context` metadata drives the
 * version-context block; `launchedFieldLabel` (Reconciliation only) personalises
 * the scope warning and highlights the launched field in the diff.
 */
export const PromoteVersionDialog: React.FC<PromoteVersionDialogProps> = ({
  open,
  siteId,
  context,
  onClose,
  onPromoted
}) => {
  const notify = useNotify();

  const { documentId, fileId } = context;
  const launchedFieldLabel = context.launchedFieldLabel ?? null;
  const canQuery = open && Number.isInteger(fileId);

  const [notes, setNotes] = React.useState('');
  const [reconfirmNeeded, setReconfirmNeeded] = React.useState(false);
  // Snapshot (stringified) of the diff the user has actually reviewed; used to
  // force a re-confirm if the live diff changes between open and confirm.
  const reviewedKeyRef = React.useRef<string | null>(null);

  const {
    data: diff,
    isLoading: isDiffLoading,
    isError: isDiffError,
    refetch
  } = usePromotionDiff(siteId, fileId, canQuery);

  React.useEffect(() => {
    if (open) {
      setNotes('');
      setReconfirmNeeded(false);
      reviewedKeyRef.current = null;
    }
  }, [open, fileId]);

  React.useEffect(() => {
    if (diff && reviewedKeyRef.current === null) {
      reviewedKeyRef.current = JSON.stringify(diff);
    }
  }, [diff]);

  const promote = usePromoteVersion(siteId, {
    onSuccess: result => {
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
    if (!Number.isInteger(fileId) || !Number.isInteger(documentId)) return;
    // Re-fetch the authoritative diff at confirm time. If the blast radius moved
    // since the user last reviewed it, hold and require a fresh confirmation.
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
    promote.mutate({ document_id: documentId, file_id: fileId, notes: notes.trim() ? notes.trim() : null });
  };

  const hasChanges = Boolean(diff?.has_changes);
  const confirmDisabled = isDiffLoading || isDiffError || !hasChanges || promote.isPending;

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" data-testid="promote-dialog">
      <DialogTitle sx={{ fontWeight: 600 }}>Promote to current assumptions</DialogTitle>
      <DialogContent dividers>
        <Box
          data-testid="promote-version-context"
          sx={{ mb: 2, p: 1.5, borderRadius: 1, backgroundColor: 'action.hover' }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Document version
          </Typography>
          {(context.documentName || context.documentTypeLabel || context.isActual) && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, alignItems: 'center', mb: 0.5 }}>
              {context.documentName && (
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {context.documentName}
                </Typography>
              )}
              {context.documentTypeLabel && <Chip size="small" variant="outlined" label={context.documentTypeLabel} />}
              {context.isActual && <Chip size="small" color="success" variant="outlined" label="Actual" />}
            </Box>
          )}
          {context.fileName && (
            <Typography variant="body2" color="text.secondary">
              File: {context.fileName}
            </Typography>
          )}
          {context.versionLabel && (
            <Typography variant="body2" color="text.secondary">
              Version: {context.versionLabel}
            </Typography>
          )}
          {context.uploadedAt && (
            <Typography variant="body2" color="text.secondary">
              Uploaded: {formatContextDate(context.uploadedAt)}
            </Typography>
          )}
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
            Document #{documentId} · Version #{fileId}
          </Typography>
        </Box>

        <Alert severity="warning" sx={{ mb: 2 }} data-testid="promote-scope-warning">
          <AlertTitle>This promotes the whole document version</AlertTitle>
          {launchedFieldLabel ? (
            <>
              Promoting this version will update <strong>every accepted value on it</strong> — not just{' '}
              <strong>{launchedFieldLabel}</strong>.
            </>
          ) : (
            <>
              Promoting this version will update <strong>every accepted value on it</strong>.
            </>
          )}{' '}
          Review the complete set of changes below before confirming. Acceptance and overrides are unchanged; this only
          moves accepted values into the project&apos;s active assumptions and does <strong>not</strong> build or
          activate a baseline.
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
                The change preview was updated since you opened this dialog. Review the current changes below, then
                confirm again to proceed.
              </Alert>
            )}

            <PromotionDiffTable diff={diff} launchedFieldLabel={launchedFieldLabel} />

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
