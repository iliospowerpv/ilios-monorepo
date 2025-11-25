import React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import FileUploadIcon from '@mui/icons-material/FileUpload';
import { styled } from '@mui/material/styles';

export const VisuallyHiddenInput = styled('input')({
  clip: 'rect(0 0 0 0)',
  clipPath: 'inset(50%)',
  height: 1,
  overflow: 'hidden',
  position: 'absolute',
  bottom: 0,
  left: 0,
  whiteSpace: 'nowrap',
  width: 1
});

interface UploadButtonProps {
  isUploading: boolean;
  allowedFileTypes: string;
  handleFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
}

const UploadButton: React.FC<UploadButtonProps> = props => {
  const { isUploading, allowedFileTypes, handleFileChange } = props;

  return (
    <Box display="flex" flexDirection="row" flexGrow={1} mb={2}>
      <Button
        disabled={isUploading}
        component="label"
        role={undefined}
        variant="contained"
        tabIndex={-1}
        startIcon={isUploading ? <CircularProgress color="inherit" size={20} /> : <FileUploadIcon />}
      >
        {isUploading ? 'Uploading' : 'Upload File'}
        <VisuallyHiddenInput type="file" accept={allowedFileTypes} multiple={false} onChange={handleFileChange} />
      </Button>
    </Box>
  );
};

export default UploadButton;
