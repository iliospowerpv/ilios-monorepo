import React from 'react';
import { Button } from '@mui/material';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Typography from '@mui/material/Typography';

interface ConfirmationModalProps {
  open: boolean;
  confirmationTitle?: string;
  confirmationMessage: string;
  confirmationDisabled: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  open,
  confirmationTitle,
  confirmationMessage,
  confirmationDisabled,
  onConfirm,
  onClose
}) => {
  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        aria-labelledby="cofirmation-dialog-title"
        aria-describedby="confirmation-dialog-description"
        fullWidth={true}
      >
        <DialogTitle id="confirmation-dialog-title" sx={{ bgcolor: 'primary.main', color: 'secondary.main' }}>
          {confirmationTitle || 'Confirm Your Action'}
        </DialogTitle>
        <DialogContent sx={{ padding: '18px !important' }}>
          <Typography>{confirmationMessage}</Typography>
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="contained" onClick={onConfirm} disabled={confirmationDisabled} autoFocus>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ConfirmationModal;
