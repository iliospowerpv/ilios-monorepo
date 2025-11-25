import * as React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import Box from '@mui/material/Box';

interface IframeComponentProps {
  url: string;
  openModal: boolean;
  isDisconnected?: boolean;
  handleClose: () => void;
  name: string;
}

function IframeComponent({ url, openModal, name, isDisconnected, handleClose }: IframeComponentProps) {
  return (
    <Dialog
      open={openModal}
      onClose={handleClose}
      aria-labelledby="alert-dialog-title"
      aria-describedby="alert-dialog-description"
      maxWidth={`xl`}
      sx={{
        '& .MuiDialog-paper': {
          width: '80vw',
          maxWidth: 'none',
          height: '80vh'
        }
      }}
    >
      <DialogTitle
        sx={{ m: 0, p: 2, height: '64px', bgcolor: 'primary.main', color: 'secondary.main' }}
        id="customized-dialog-title"
      >
        {name}
      </DialogTitle>
      <IconButton
        aria-label="close"
        onClick={handleClose}
        sx={theme => ({
          position: 'absolute',
          right: 8,
          top: 12,
          color: theme.palette.grey[500]
        })}
      >
        <CloseIcon />
      </IconButton>
      <DialogContent sx={{ m: 0, p: 0, display: 'flex' }}>
        {isDisconnected ? (
          <Box
            sx={{
              backgroundColor: '#000000',
              width: '100%',
              height: '100%',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            Camera Disconnected
          </Box>
        ) : (
          <iframe src={url} title="Embedded Content" width="100%" height="100%" style={{ border: 'none' }} />
        )}
      </DialogContent>
    </Dialog>
  );
}

export default IframeComponent;
