import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';

import DocumentModal from '../../../../../../../components/common/DocumentModal/DocumentModal';
import { ApiClient, FileItem, UrlUpload, FileDataResponse, Category } from '../../../../../../../api';
import { useNotify } from '../../../../../../../contexts/notifications/notifications';
import { ConfirmationModal } from '../../../../../../../components/modals/ConfirmationModal/ConfirmationModal';
import UploadButton from '../../../../../../../components/common/UploadButton/UploadButton';
import Document from '../../../../../../../components/common/Document/Document';
import { MAX_FILE_SIZE } from '../../../../../../../constants';

interface DocumentListProps {
  siteId: number;
  deviceId: number;
  documents: any;
}

export const DocumentList: React.FC<DocumentListProps> = ({ siteId, deviceId, documents }) => {
  const notify = useNotify();
  const queryClient = useQueryClient();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const [isUploadingWarranty, setIsUploadingWarranty] = useState<boolean>(false);
  const [isUploadingSpecifications, setIsUploadingSpecifications] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [openModal, setOpenModal] = useState(false);
  const [confirmationModalOpen, setConfirmationModalOpen] = useState(false);
  const [fileUrl, setFileUrl] = useState('');

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
      ApiClient.assetManagement
        .downloadFile(siteId, deviceId, selectedFile.id)
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
    if (file && ['png', 'jpeg', 'jpg', 'pdf'].includes(file.extension)) {
      ApiClient.assetManagement
        .previewFile(siteId, deviceId, file.id)
        .then(response => {
          setFileUrl(response.preview_url);
        })
        .catch(e => {
          notify(e?.response?.data?.message || 'Cannot show file');
        });
    } else if (file) {
      ApiClient.assetManagement
        .downloadFile(siteId, deviceId, file.id)
        .then(response => {
          setFileUrl(response.download_url);
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
      ApiClient.assetManagement
        .deleteFile(siteId, deviceId, selectedFile.id)
        .then((response: FileDataResponse) => {
          queryClient.invalidateQueries({ queryKey: ['device', 'details', { siteId, deviceId }] });
          notify(response.message || 'File successfully deleted');
          setConfirmationModalOpen(false);
        })
        .catch(e => {
          setConfirmationModalOpen(false);
          notify(e?.response?.data?.message || 'Cannot delete file');
        });
    }
  };

  const executeRequests = async (file: File, category: Category) => {
    try {
      const uploadUrlResponse: UrlUpload = await ApiClient.assetManagement.uploadUrl(file.name, siteId, deviceId);

      await ApiClient.assetManagement.uploadFile(file, uploadUrlResponse.upload_url);

      const uploadConfirmResponse: any = await ApiClient.assetManagement.uploadConfirm(
        uploadUrlResponse.filepath,
        file.name,
        category,
        siteId,
        deviceId
      );

      queryClient.invalidateQueries({ queryKey: ['device', 'details', { siteId, deviceId }] });
      notify(uploadConfirmResponse.message || 'File has been successfully uploaded');
    } catch (e: any) {
      notify(
        e instanceof AxiosError
          ? e.response?.data?.message || e.message
          : e.message || 'File upload failed. Please try again'
      );
    } finally {
      if (category === 'Warranty') {
        setIsUploadingWarranty(false);
      } else {
        setIsUploadingSpecifications(false);
      }
    }
  };

  const uploadFileToServer = async (file: File, category: Category) => {
    if (category === 'Warranty') {
      setIsUploadingWarranty(true);
    } else {
      setIsUploadingSpecifications(true);
    }

    executeRequests(file, category);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>, category: Category) => {
    const file = event.target.files?.[0];

    if (file) {
      if (file.size > MAX_FILE_SIZE) {
        notify('File size should be under 100MB');
      } else {
        uploadFileToServer(file, category);
      }
    }
  };

  if (!documents) return null;

  return (
    <>
      <Box>
        {documents?.map((item: any) => (
          <Box key={item.category} sx={{ mb: 2, '&:last-child': { mb: 0 } }}>
            <Typography variant="h6" fontSize="16px" mb="12px" fontWeight="600">
              {item.category}
            </Typography>
            <UploadButton
              isUploading={item.category === 'Warranty' ? isUploadingWarranty : isUploadingSpecifications}
              allowedFileTypes=".pdf, .docx, .jpg, .jpeg, .png"
              handleFileChange={(event: React.ChangeEvent<HTMLInputElement>) => handleFileChange(event, item.category)}
            />
            {item.items?.map((file: any) => (
              <Box key={file.id} sx={{ mb: 1, '&:last-child': { mb: 0 } }}>
                <Document open={open} file={file} handleModalOpen={handleModalOpen} handleMenuClick={handleMenuClick} />
              </Box>
            ))}
          </Box>
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

export default DocumentList;
