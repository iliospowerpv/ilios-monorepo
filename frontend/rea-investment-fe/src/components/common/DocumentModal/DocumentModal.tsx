import React from 'react';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import DocViewer, { DocViewerRenderers } from '@cyntler/react-doc-viewer';
import Box from '@mui/material/Box';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import Typography from '@mui/material/Typography';
import Modal from '@mui/material/Modal';
import Fade from '@mui/material/Fade';
import { styled } from '@mui/material/styles';

import { FileItem } from '../../../api';
import { DocImageRenderer } from '../DocImageRenderer/DocImageRenderer';

dayjs.extend(utc);

export const DocunentPreviewModal = styled(Modal)(() => ({
  '& .MuiDialogContent-root': {
    padding: 0
  }
}));

export const DocunentPreviewModalViewbox = styled(Box)(() => ({
  display: 'flex',
  height: '100%',
  outline: '0px',
  justifyContent: 'center',
  alignItems: 'center',
  minWidth: '600px'
}));

export const DocunentPreviewModalContent = styled(Box)(({ theme }) => ({
  [theme.breakpoints.between('xs', 'md')]: {
    width: 'calc(100% - 32px)'
  },
  [theme.breakpoints.between('md', 'lg')]: {
    width: 'calc(100% - 64px)'
  },
  [theme.breakpoints.between('lg', 'xl')]: {
    width: '90%'
  },
  [theme.breakpoints.up('xl')]: {
    width: '85%'
  },
  height: 'calc(100% - 32px)',
  minWidth: '600px',
  maxWidth: '2000px',
  margin: 'auto'
}));

export const DocumentPreviewContainer = styled(Box)(({ theme }) => ({
  height: '100%',
  width: '100%',
  margin: '0 auto',
  '#proxy-renderer': {
    overflow: 'hidden'
  },
  '#pdf-controls': {
    position: 'absolute',
    width: '100%',
    height: '56px',
    justifyContent: 'flex-start',
    alignItems: 'center',
    boxShadow: 'none',
    padding: '8px 20px',
    borderBottom: '1px solid #E0E0E0',
    background: theme.palette.common.white,
    '& > *': {
      color: theme.palette.text.secondary,
      boxShadow: 'none',
      margin: '0px 8px'
    },
    path: {
      fill: theme.palette.text.secondary
    },
    polygon: {
      fill: theme.palette.text.secondary
    }
  },
  '#pdf-pagination': {
    order: 1,
    margin: 0,
    '& > *': {
      color: theme.palette.text.secondary,
      boxShadow: 'none'
    }
  },
  '#pdf-download': {
    display: 'none'
  },
  '#msdoc-renderer': {
    marginTop: '-1px',
    marginLeft: '-1px'
  }
}));

interface DocumentModal {
  open: boolean;
  fileUrl: string;
  file: FileItem | null;
  onClose: () => void;
}

const DocumentModal: React.FC<DocumentModal> = props => {
  const { open, file, fileUrl, onClose } = props;

  if (!file || !fileUrl) return null;

  return (
    <DocunentPreviewModal
      className="DocumentPreviewModal-root"
      onClose={onClose}
      aria-labelledby="customized-dialog-title"
      open={open}
      disableEnforceFocus
      disableAutoFocus
      disableRestoreFocus
    >
      <Fade in={open}>
        <DocunentPreviewModalViewbox className="DocumentPreviewModal-viewbox">
          <DocunentPreviewModalContent className="DocumentPreviewModal-content">
            <DialogTitle
              sx={{
                bgcolor: 'primary.main',
                color: 'secondary.main',
                position: 'relative',
                height: '90px',
                maxWidth: '100%',
                minWidth: '600px'
              }}
              id="customized-dialog-title"
            >
              {file.filename}
              <Typography variant="body2" sx={{ marginTop: '5px' }}>
                Uploaded by {file.author}, {dayjs.utc(file.created_at).local().format('lll')}
              </Typography>
              <IconButton
                aria-label="close"
                onClick={onClose}
                sx={{
                  position: 'absolute',
                  right: 8,
                  top: 8,
                  color: theme => theme.palette.secondary.main
                }}
              >
                <CloseIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent
              dividers
              sx={{
                backgroundColor: theme => theme.palette.background.default,
                position: 'relative',
                height: 'calc(100% - 90px)',
                flex: 0,
                overflow: 'unset',
                width: '100%',
                minWidth: '600px'
              }}
            >
              <Box
                height="100%"
                maxWidth="2000px"
                marginX="auto"
                position="relative"
                padding={
                  file.filename.endsWith('.pdf') ||
                  file.filename.endsWith('.jpg') ||
                  file.filename.endsWith('.jpeg') ||
                  file.filename.endsWith('.png')
                    ? '70px 16px 16px!important'
                    : '16px'
                }
              >
                {document && (
                  <DocumentPreviewContainer>
                    <DocViewer
                      pluginRenderers={[DocImageRenderer, ...DocViewerRenderers]}
                      documents={[{ uri: fileUrl }]}
                      style={{ width: '100%', height: '100%' }}
                      config={{
                        header: {
                          disableHeader: true,
                          disableFileName: true
                        },
                        pdfZoom: {
                          defaultZoom: 0.7,
                          zoomJump: 0.1
                        },
                        pdfVerticalScrollByDefault: true
                      }}
                    />
                  </DocumentPreviewContainer>
                )}
              </Box>
            </DialogContent>
          </DocunentPreviewModalContent>
        </DocunentPreviewModalViewbox>
      </Fade>
    </DocunentPreviewModal>
  );
};

export default DocumentModal;
