import React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';

interface ArchiveConfirmationModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  entityType: 'company' | 'project';
  entityName: string;
  isLoading?: boolean;
}

export const ArchiveConfirmationModal: React.FC<ArchiveConfirmationModalProps> = ({
  open,
  onClose,
  onConfirm,
  entityType,
  entityName,
  isLoading = false
}) => {
  const isCompany = entityType === 'company';

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningAmberIcon color="warning" />
          Archive {isCompany ? 'Company' : 'Project'}
        </Box>
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          Are you sure you want to archive <strong>{entityName}</strong>?
        </DialogContentText>
        {isCompany && (
          <DialogContentText sx={{ mt: 2, color: 'warning.main' }}>
            This will also archive all child projects associated with this company. They will be hidden from all active
            views, dashboards, and search results.
          </DialogContentText>
        )}
        {!isCompany && (
          <DialogContentText sx={{ mt: 2 }}>
            This project will be hidden from all active views, dashboards, and search results.
          </DialogContentText>
        )}
        <DialogContentText sx={{ mt: 2 }}>Archived records can be restored later by an admin.</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isLoading}>
          Cancel
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color="warning"
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={16} /> : undefined}
        >
          {isLoading ? 'Archiving...' : 'Archive'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ArchiveConfirmationModal;
