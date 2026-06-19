import React, { useRef, useState, useCallback } from 'react';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import { styled, alpha } from '@mui/material/styles';

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

const isFileAccepted = (file: File, acceptAttr: string): boolean => {
  const normalized = (acceptAttr || '').trim();
  // An empty or wildcard accept means "all file types" (mirrors formatAcceptLabel).
  if (normalized === '' || normalized === '*' || normalized === '*/*') return true;
  const tokens = normalized.split(',').map(t => t.trim().toLowerCase());
  const ext = ('.' + (file.name.split('.').pop() || '')).toLowerCase();
  const mime = file.type.toLowerCase();
  return tokens.some(token => {
    if (token === '*' || token === '*/*') return true;
    if (token.startsWith('.')) return ext === token;
    if (token.endsWith('/*')) return mime.startsWith(token.replace('/*', '/'));
    return mime === token;
  });
};

const formatAcceptLabel = (acceptAttr: string): string => {
  if (!acceptAttr || acceptAttr.trim() === '*') return 'All file types';
  return acceptAttr
    .split(',')
    .map(t => t.trim().replace('.', '').toUpperCase())
    .filter(Boolean)
    .join(', ');
};

const UploadButton: React.FC<UploadButtonProps> = props => {
  const { isUploading, allowedFileTypes, handleFileChange } = props;
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  const processFile = useCallback(
    (file: File) => {
      const input = fileInputRef.current;
      if (!input) return;
      // Route dropped files through the same parent handler the native picker
      // uses, but invoke it directly instead of re-dispatching a DOM "change"
      // event. A synthesized change is unreliable in React 18 and can deliver a
      // multipart part with an empty filename, which the backend rejects (400).
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      handleFileChange({
        target: input,
        currentTarget: input
      } as unknown as React.ChangeEvent<HTMLInputElement>);
      input.value = '';
    },
    [handleFileChange]
  );

  const handleDragEnter = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounterRef.current += 1;
      if (!isUploading && e.dataTransfer.items.length > 0) {
        setIsDragOver(true);
      }
    },
    [isUploading]
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current === 0) {
      setIsDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      dragCounterRef.current = 0;
      if (isUploading) return;
      const files = e.dataTransfer.files;
      if (files.length === 0) return;
      const file = files[0];
      if (!isFileAccepted(file, allowedFileTypes)) return;
      processFile(file);
    },
    [isUploading, allowedFileTypes, processFile]
  );

  const handleBrowseClick = useCallback(() => {
    if (!isUploading) {
      fileInputRef.current?.click();
    }
  }, [isUploading]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleFileChange(e);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [handleFileChange]
  );

  return (
    <Box mb={2}>
      <Box
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleBrowseClick}
        role="button"
        tabIndex={0}
        onKeyDown={e => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleBrowseClick();
          }
        }}
        aria-label="Upload file"
        sx={theme => ({
          border: `2px dashed ${isDragOver ? theme.palette.primary.main : theme.palette.divider}`,
          borderRadius: '8px',
          padding: '24px 16px',
          textAlign: 'center',
          cursor: isUploading ? 'default' : 'pointer',
          backgroundColor: isDragOver
            ? alpha(theme.palette.primary.main, 0.06)
            : isUploading
              ? alpha(theme.palette.action.disabled, 0.04)
              : 'transparent',
          transition: 'all 0.2s ease',
          '&:hover': isUploading
            ? {}
            : {
                borderColor: theme.palette.primary.light,
                backgroundColor: alpha(theme.palette.primary.main, 0.03)
              },
          '&:focus-visible': {
            outline: `2px solid ${theme.palette.primary.main}`,
            outlineOffset: '2px'
          }
        })}
      >
        {isUploading ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
            <CircularProgress size={32} />
            <Typography variant="body2" color="text.secondary">
              Uploading file...
            </Typography>
          </Box>
        ) : isDragOver ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
            <InsertDriveFileIcon sx={{ fontSize: 36, color: 'primary.main' }} />
            <Typography variant="body2" color="primary.main" fontWeight={600}>
              Drop file here
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
            <CloudUploadIcon sx={{ fontSize: 36, color: 'text.secondary' }} />
            <Typography variant="body2" color="text.primary">
              Drag and drop a file here, or{' '}
              <Typography component="span" variant="body2" color="primary.main" fontWeight={600}>
                browse
              </Typography>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatAcceptLabel(allowedFileTypes)} &bull; Max 100 MB
            </Typography>
          </Box>
        )}
      </Box>
      <input
        ref={fileInputRef}
        type="file"
        accept={allowedFileTypes}
        multiple={false}
        onChange={handleInputChange}
        style={{ display: 'none' }}
      />
    </Box>
  );
};

export default UploadButton;
