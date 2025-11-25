import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';

import DocumentModal from '../DocumentModal/DocumentModal';
import { ApiClient, FileItem, FileDataResponse, UrlUpload } from '../../../api';
import { useNotify } from '../../../contexts/notifications/notifications';
import { ConfirmationModal } from '../../modals/ConfirmationModal/ConfirmationModal';
import UploadButton from '../UploadButton/UploadButton';
import Document from '../Document/Document';
import { MAX_FILE_SIZE } from '../../../constants';

interface SiteConditionsProps {
  boardId: number;
  taskId: number;
}

export const SiteConditions: React.FC<SiteConditionsProps> = ({ boardId, taskId }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [openModal, setOpenModal] = useState(false);
  const [confirmationModalOpen, setConfirmationModalOpen] = useState(false);
  const [fileUrl, setFileUrl] = useState('');

  const { data: fileData, isLoading: isLoadingFileData } = useQuery({
    queryFn: async () => {
      return ApiClient.taskManagement.getSiteConditions(boardId, taskId);
    },
    queryKey: ['site conditions', { boardId, taskId }]
  });

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
      ApiClient.taskManagement
        .downloadSiteConditions(boardId, taskId, selectedFile.id)
        .then(response => {
          downloadFile(response.download_url, selectedFile.filename);
          notify('Download started');
        })
        .catch(e => {
          notify(e?.response?.data?.message || 'Cannot download file');
        });
    }
  };

  const handleModalOpen = (file: FileItem) => {
    if (file && ['png', 'jpeg', 'jpg'].includes(file.extension)) {
      ApiClient.taskManagement
        .previewSiteConditions(boardId, taskId, file.id)
        .then(response => {
          setFileUrl(response.preview_url);
        })
        .catch(e => {
          notify(e?.response?.data?.message || 'Cannot show file');
        });
    }

    setSelectedFile(file);
    setOpenModal(true);
  };

  const handleModalClose = () => {
    setOpenModal(false);
  };

  const handleConfirmModalClose = (): void => {
    setConfirmationModalOpen(false);
  };

  const handleModalConfirm = async (): Promise<void> => {
    if (selectedFile) {
      ApiClient.taskManagement
        .deleteSiteConditions(boardId, taskId, selectedFile.id)
        .then((response: FileDataResponse) => {
          queryClient.invalidateQueries({ queryKey: ['site conditions'] });
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
      const uploadUrlResponse: UrlUpload = await ApiClient.taskManagement.uploadSiteConditions(
        file.name,
        boardId,
        taskId
      );

      await ApiClient.taskManagement.uploadFile(file, uploadUrlResponse.upload_url);

      const uploadConfirmResponse: any = await ApiClient.taskManagement.uploadSiteConditionsConfirm(
        uploadUrlResponse.filepath,
        file.name,
        boardId,
        taskId
      );

      queryClient.invalidateQueries({ queryKey: ['site conditions'] });
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

  if (isLoadingFileData || !fileData) return null;

  return (
    <>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
          Site Conditions
        </Typography>
        <Box>
          <UploadButton
            isUploading={isUploading}
            allowedFileTypes=".jpeg, .jpg, .png"
            handleFileChange={handleFileChange}
          />
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
              </Menu>
            </Grid>
          </Box>
        </Box>
      </Box>
      <DocumentModal open={openModal} file={selectedFile} fileUrl={fileUrl} onClose={handleModalClose} />
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

export default SiteConditions;
