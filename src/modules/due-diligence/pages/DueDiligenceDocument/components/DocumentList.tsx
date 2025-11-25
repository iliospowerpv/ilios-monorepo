import React, { useCallback, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import Collapse from '@mui/material/Collapse';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import BookmarkAddedIcon from '@mui/icons-material/BookmarkAdded';
import BookmarkRemoveIcon from '@mui/icons-material/BookmarkRemove';
import { AxiosError } from 'axios';
import { useSearchParams } from 'react-router-dom';

import DocumentModal from './DocumentModal';
import UniversalDocumentModal from '../../../../../components/common/DocumentModal/DocumentModal';
import { ApiClient, FileItem, FileDataResponse, UrlUpload } from '../../../../../api';
import { useNotify } from '../../../../../contexts/notifications/notifications';
import { ConfirmationModal } from '../../../../../components/modals/ConfirmationModal/ConfirmationModal';
import UploadButton from '../../../../../components/common/UploadButton/UploadButton';
import Document from '../../../../../components/common/Document/Document';
import { MAX_FILE_SIZE } from '../../../../../constants';

interface DocumentListProps {
  siteId: number;
  documentId: number;
  documentKind: boolean;
  boardId: number;
  taskId: number;
}

export const DocumentList: React.FC<DocumentListProps> = ({ siteId, documentId, documentKind, boardId, taskId }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [openModal, setOpenModal] = useState(false);
  const [confirmationModalOpen, setConfirmationModalOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const [isActualFiles, setIsActualFiles] = useState(true);

  const { data: fileData, isLoading: isLoadingFileData } = useQuery({
    queryFn: async () => {
      return ApiClient.dueDiligence.getFiles(siteId, documentId);
    },
    queryKey: ['files', { siteId, documentId }]
  });

  const { data: fileUrl, error: errorRetrievingFileUrl } = useQuery({
    queryFn:
      selectedFile && openModal
        ? ['png', 'jpeg', 'jpg', 'pdf'].includes(selectedFile.extension)
          ? () => ApiClient.dueDiligence.previewFile(siteId, documentId, selectedFile.id).then(res => res.preview_url)
          : () => ApiClient.dueDiligence.downloadFile(siteId, documentId, selectedFile.id).then(res => res.download_url)
        : () => null,
    enabled: openModal && !!selectedFile,
    queryKey: ['file-preview-url', { siteId, documentId, fileId: selectedFile?.id ?? null }],
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
    refetchOnMount: false
  });

  useEffect(() => {
    if (errorRetrievingFileUrl) {
      notify(
        (errorRetrievingFileUrl instanceof AxiosError && errorRetrievingFileUrl?.response?.data?.message) ||
          'Cannot show file'
      );
    }
  }, [errorRetrievingFileUrl, notify]);

  const toggleFileIsActual = (isActual: boolean) => {
    if (selectedFile) {
      ApiClient.dueDiligence
        .updateIsActualFile({ siteId, documentId, fileId: selectedFile.id, attributes: { is_actual: isActual } })
        .then(response => {
          queryClient.invalidateQueries({ queryKey: ['files', { siteId, documentId }] });
          notify(response?.message || 'File is actual status has been updated successfully');
        })
        .catch(e => {
          notify(e?.response?.data?.message || 'Cannot mark file as actual');
        });
    }
  };

  const findActualFiles = () => {
    return fileData ? fileData?.items.filter((file: FileItem) => file.is_actual) : null;
  };

  const downloadFile = (url: string, filename: string) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, file: FileItem) => {
    event.stopPropagation();
    setSelectedFile(file);
    setAnchorEl(event.currentTarget);
  };
  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleDelete = () => {
    setConfirmationModalOpen(true);
    handleMenuClose();
  };

  const handleDownload = () => {
    handleMenuClose();

    if (selectedFile) {
      ApiClient.dueDiligence
        .downloadFile(siteId, documentId, selectedFile.id)
        .then(response => {
          downloadFile(response.download_url, selectedFile.filename);
          notify('Download started');
        })
        .catch(e => {
          notify(e?.response?.data?.message || 'Cannot download file');
        });
    }
  };

  const handleMarkAsActual = () => {
    toggleFileIsActual(true);
    handleMenuClose();
  };

  const handleRemoveFromActual = () => {
    toggleFileIsActual(false);
    handleMenuClose();
  };

  const handleModalOpen = useCallback(
    (file: FileItem) => {
      queryClient.removeQueries({ queryKey: ['file-preview-url'] });
      setSelectedFile(file);
      setOpenModal(true);
    },
    [queryClient]
  );

  const handleModalClose = () => {
    setOpenModal(false);
    setSelectedFile(null);
  };

  const handleConfirmModalClose = (): void => {
    setConfirmationModalOpen(false);
  };

  const handleModalConfirm = async (): Promise<void> => {
    if (selectedFile) {
      ApiClient.dueDiligence
        .deleteFile(siteId, documentId, selectedFile.id)
        .then((response: FileDataResponse) => {
          queryClient.invalidateQueries({ queryKey: ['files'] });
          queryClient.removeQueries({ queryKey: ['file-preview-url'] });
          notify(response.message || 'File successfully deleted');
          setConfirmationModalOpen(false);
        })
        .catch(e => {
          setConfirmationModalOpen(false);
          notify(e?.response?.data?.message || 'Cannot delete file');
        });
    }
  };

  const executeRequests = async (file: File) => {
    try {
      const uploadUrlResponse: UrlUpload = await ApiClient.dueDiligence.uploadUrl(file.name, siteId, documentId);

      await ApiClient.dueDiligence.uploadFile(file, uploadUrlResponse.upload_url);

      const uploadConfirmResponse: any = await ApiClient.dueDiligence.uploadConfirm(
        uploadUrlResponse.filepath,
        file.name,
        siteId,
        documentId
      );

      queryClient.invalidateQueries({ queryKey: ['files'] });
      notify(uploadConfirmResponse.message || 'File has been successfully uploaded');
    } catch (e: any) {
      notify(
        e instanceof AxiosError
          ? e.response?.data?.message || e.message
          : e.message || 'File upload failed. Please try again'
      );
    } finally {
      setIsUploading(false);
    }
  };

  const uploadFileToServer = async (file: File) => {
    setIsUploading(true);

    executeRequests(file);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];

    if (file) {
      if (file.size > MAX_FILE_SIZE) {
        notify('File size should be under 100MB');
      } else {
        uploadFileToServer(file);
      }
    }
  };

  useEffect(() => {
    if (searchParams.has('fileId')) {
      const token = searchParams.get('fileId');
      if (token && fileData) {
        const fileId = Number.parseInt(token);
        const filteredItem = fileData?.items?.filter(item => item.id === fileId);
        if (filteredItem && filteredItem.length > 0) {
          handleModalOpen(filteredItem[0]);
        }
        searchParams.delete('fileId');
        setSearchParams(searchParams, { replace: true });
      }
    }
  }, [searchParams, setSearchParams, fileData, handleModalOpen]);

  useEffect(() => {
    const result = findActualFiles();

    if (result) {
      setIsActualFiles(!!result.length);
    }
  }, [fileData]);

  if (isLoadingFileData || !fileData) return null;

  return (
    <>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
          Documents
        </Typography>
        <Box>
          <UploadButton
            isUploading={isUploading}
            allowedFileTypes=".pdf, .docx, .jpeg, .jpg, .png"
            handleFileChange={handleFileChange}
          />
          <Collapse in={!isActualFiles} sx={{ mb: 2 }}>
            <Alert severity="info" sx={{ borderRadius: '4px' }}>
              Please mark actual files to ensure accurate AI assistant responses. If none are marked, response accuracy
              may be affected.
            </Alert>
          </Collapse>
          <Box display="flex" flexDirection="row" flexGrow={1} sx={{ width: '100%' }}>
            <Grid container rowSpacing={1} columnSpacing={1}>
              {fileData?.items.map(file => (
                <Grid key={file.id} item xs={6}>
                  <Document
                    open={open}
                    file={file}
                    handleModalOpen={handleModalOpen}
                    handleMenuClick={handleMenuClick}
                  />
                </Grid>
              ))}
              <Menu
                id={`basic-menu`}
                anchorEl={anchorEl}
                open={open}
                onClose={handleMenuClose}
                MenuListProps={{
                  'aria-labelledby': `basic-button`
                }}
                transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
              >
                <MenuItem onClick={handleDownload}>
                  <ListItemIcon>
                    <DownloadIcon fontSize="small" />
                  </ListItemIcon>
                  Download
                </MenuItem>
                <MenuItem onClick={handleDelete}>
                  <ListItemIcon>
                    <DeleteIcon fontSize="small" />
                  </ListItemIcon>
                  Delete
                </MenuItem>
                {!selectedFile?.is_actual && (
                  <MenuItem onClick={handleMarkAsActual}>
                    <ListItemIcon>
                      <BookmarkAddedIcon fontSize="small" />
                    </ListItemIcon>
                    Mark as Actual
                  </MenuItem>
                )}
                {selectedFile?.is_actual && (
                  <MenuItem onClick={handleRemoveFromActual}>
                    <ListItemIcon>
                      <BookmarkRemoveIcon fontSize="small" />
                    </ListItemIcon>
                    Remove from Actual
                  </MenuItem>
                )}
              </Menu>
            </Grid>
          </Box>
        </Box>
      </Box>
      {!documentKind || ['jpeg', 'png', 'jpg'].includes(selectedFile?.extension || '') ? (
        <UniversalDocumentModal
          open={openModal}
          fileUrl={fileUrl ?? ''}
          file={selectedFile}
          onClose={handleModalClose}
        />
      ) : (
        <DocumentModal
          open={openModal}
          fileUrl={fileUrl ?? ''}
          file={selectedFile}
          siteId={siteId}
          documentId={documentId}
          boardId={boardId}
          taskId={taskId}
          onClose={handleModalClose}
        />
      )}
      <ConfirmationModal
        open={confirmationModalOpen}
        confirmationMessage="Are you sure you want to delete this file?"
        confirmationDisabled={false}
        onClose={handleConfirmModalClose}
        onConfirm={handleModalConfirm}
      />
    </>
  );
};

export default DocumentList;
