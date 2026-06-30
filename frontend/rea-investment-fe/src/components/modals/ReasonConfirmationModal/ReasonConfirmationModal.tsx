import React, { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';

interface ReasonConfirmationModalProps {
  open: boolean;
  title: string;
  message: string;
  reasonLabel?: string;
  confirmLabel?: string;
  confirmColor?: 'error' | 'warning' | 'primary';
  isLoading?: boolean;
  errorMessage?: string | null;
  onConfirm: (reason: string) => void;
  onClose: () => void;
}

export const ReasonConfirmationModal: React.FC<ReasonConfirmationModalProps> = ({
  open,
  title,
  message,
  reasonLabel = 'Reason',
  confirmLabel = 'Confirm',
  confirmColor = 'error',
  isLoading = false,
  errorMessage = null,
  onConfirm,
  onClose
}) => {
  const [reason, setReason] = useState('');

  useEffect(() => {
    if (!open) {
      setReason('');
    }
  }, [open]);

  const trimmedReason = reason.trim();
  const confirmDisabled = isLoading || trimmedReason.length === 0;

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
        {errorMessage && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {errorMessage}
          </Alert>
        )}
        <TextField
          autoFocus
          required
          fullWidth
          multiline
          minRows={2}
          margin="dense"
          label={reasonLabel}
          placeholder="Enter a reason for this action"
          value={reason}
          onChange={e => setReason(e.target.value)}
          disabled={isLoading}
          inputProps={{ 'aria-label': reasonLabel }}
          sx={{ mt: 2 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isLoading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color={confirmColor}
          onClick={() => onConfirm(trimmedReason)}
          disabled={confirmDisabled}
          startIcon={isLoading ? <CircularProgress size={16} /> : undefined}
        >
          {confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ReasonConfirmationModal;
