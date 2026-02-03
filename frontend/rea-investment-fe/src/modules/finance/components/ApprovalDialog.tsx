import React, { useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import Alert from '@mui/material/Alert';
import { FinanceObligation, FinanceApprovalDecision } from '../types';

interface ApprovalDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { decision: string; notes?: string; override_reason?: string }) => Promise<unknown>;
  obligation: FinanceObligation | null;
  action: 'approve' | 'reject' | null;
}

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

export const ApprovalDialog: React.FC<ApprovalDialogProps> = ({ open, onClose, onSubmit, obligation, action }) => {
  const [notes, setNotes] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [useOverride, setUseOverride] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      let decision: string;
      if (action === 'reject') {
        decision = FinanceApprovalDecision.Rejected;
      } else if (useOverride) {
        decision = FinanceApprovalDecision.Override;
      } else {
        decision = FinanceApprovalDecision.Approved;
      }
      await onSubmit({
        decision,
        notes: notes || undefined,
        override_reason: useOverride ? overrideReason : undefined
      });
      setNotes('');
      setOverrideReason('');
      setUseOverride(false);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  if (!obligation) return null;

  const hasPrerequisiteIssues =
    obligation.prerequisite_snapshot &&
    (obligation.prerequisite_snapshot as any).missing_prerequisites?.length > 0;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{action === 'approve' ? 'Approve Obligation' : 'Reject Obligation'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <Typography variant="body2">
            <strong>Amount:</strong> {formatCurrency(obligation.amount_requested)}
          </Typography>
          <Typography variant="body2">
            <strong>Type:</strong> {obligation.obligation_type}
          </Typography>
          {obligation.vendor_name && (
            <Typography variant="body2">
              <strong>Vendor:</strong> {obligation.vendor_name}
            </Typography>
          )}
          {obligation.description && (
            <Typography variant="body2">
              <strong>Description:</strong> {obligation.description}
            </Typography>
          )}
          {obligation.reference_number && (
            <Typography variant="body2">
              <strong>Reference:</strong> {obligation.reference_number}
            </Typography>
          )}

          {hasPrerequisiteIssues && (
            <Alert severity="warning">
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                Missing Prerequisites:
              </Typography>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {((obligation.prerequisite_snapshot as any).missing_prerequisites || []).map(
                  (prereq: string, idx: number) => (
                    <li key={idx}>{prereq}</li>
                  )
                )}
              </ul>
            </Alert>
          )}

          {action === 'approve' && hasPrerequisiteIssues && (
            <FormControlLabel
              control={<Checkbox checked={useOverride} onChange={e => setUseOverride(e.target.checked)} />}
              label="Approve with override (requires reason)"
            />
          )}

          {useOverride && (
            <TextField
              label="Override Reason"
              value={overrideReason}
              onChange={e => setOverrideReason(e.target.value)}
              multiline
              rows={2}
              required
              fullWidth
              placeholder="Explain why you are approving despite missing prerequisites"
            />
          )}

          <TextField
            label="Notes"
            value={notes}
            onChange={e => setNotes(e.target.value)}
            multiline
            rows={2}
            fullWidth
            placeholder={action === 'reject' ? 'Reason for rejection (optional)' : 'Additional notes (optional)'}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          color={action === 'reject' ? 'error' : 'primary'}
          disabled={loading || (useOverride && !overrideReason)}
        >
          {action === 'approve' ? (useOverride ? 'Approve with Override' : 'Approve') : 'Reject'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ApprovalDialog;
