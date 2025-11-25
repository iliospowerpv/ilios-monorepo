import React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';

interface AIAssistantActionConfirmationDialogProps {
  open: boolean;
  onClose: () => void;
  title?: string | null;
  text?: string | null;
  onConfirm: () => void;
}

export const AIAssistantActionConfirmationDialog: React.FC<AIAssistantActionConfirmationDialogProps> = ({
  open,
  onClose,
  title,
  text,
  onConfirm
}) => (
  <Dialog open={open} onClose={onClose}>
    <DialogTitle sx={{ backgroundColor: '#121212', color: '#FFFFFF' }}>{title}</DialogTitle>
    <IconButton
      aria-label="close"
      onClick={onClose}
      sx={{
        position: 'absolute',
        right: 8,
        top: 12,
        color: 'rgba(255, 255, 255, 0.56)'
      }}
    >
      <CloseIcon />
    </IconButton>
    <DialogContent sx={{ padding: '8px 24px 8px 24px !important' }}>
      <DialogContentText>{text}</DialogContentText>
    </DialogContent>
    <DialogActions>
      <Button variant="outlined" onClick={onClose}>
        Cancel
      </Button>
      <Button variant="contained" onClick={onConfirm}>
        Confirm
      </Button>
    </DialogActions>
  </Dialog>
);

export default AIAssistantActionConfirmationDialog;
