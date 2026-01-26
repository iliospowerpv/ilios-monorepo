import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import DeleteIcon from '@mui/icons-material/Delete';
import ArchiveIcon from '@mui/icons-material/Archive';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';

import Assignee from '../Assignee/Assignee';
import { ApiClient, DiligenceDocument } from '../../../../../../../../api';
import { useNotify } from '../../../../../../../../contexts/notifications/notifications';

interface DocumentItemProps {
  document: DiligenceDocument;
  onRefresh?: () => void;
}

const DocumentItem: React.FC<DocumentItemProps> = ({ document, onRefresh }) => {
  const navigate = useNavigate();
  const { siteId, companyId } = useParams();
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [actionType, setActionType] = useState<'delete' | 'archive'>('delete');

  const hasFiles = document.files_count > 0;

  const deleteMutation = useMutation({
    mutationFn: () => ApiClient.dueDiligence.deleteDocument(Number(siteId), document.id),
    onSuccess: () => {
      notify('Document deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['site', 'diligence', { siteId: Number(siteId) }] });
      onRefresh?.();
    },
    onError: (error: any) => {
      notify(error?.response?.data?.detail || 'Failed to delete document');
    }
  });

  const archiveMutation = useMutation({
    mutationFn: () => ApiClient.dueDiligence.archiveDocument(Number(siteId), document.id),
    onSuccess: () => {
      notify('Document archived successfully');
      queryClient.invalidateQueries({ queryKey: ['site', 'diligence', { siteId: Number(siteId) }] });
      onRefresh?.();
    },
    onError: (error: any) => {
      notify(error?.response?.data?.detail || 'Failed to archive document');
    }
  });

  const handleActionClick = (e: React.MouseEvent, action: 'delete' | 'archive') => {
    e.stopPropagation();
    setActionType(action);
    setConfirmDialogOpen(true);
  };

  const handleConfirmAction = () => {
    setConfirmDialogOpen(false);
    if (actionType === 'delete') {
      deleteMutation.mutate();
    } else {
      archiveMutation.mutate();
    }
  };

  const filesCount = (item: number) => {
    switch (item) {
      case 0:
        return 'No Files Yet';
      case 1:
        return '1 File';
      default:
        return `${item} Files`;
    }
  };

  return (
    <>
      <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)}>
        <DialogTitle>{actionType === 'delete' ? 'Delete Document' : 'Archive Document'}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {actionType === 'delete'
              ? 'Are you sure you want to delete this document? This action cannot be undone.'
              : 'Are you sure you want to archive this document? Archived documents will be hidden from the list.'}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmAction} color={actionType === 'delete' ? 'error' : 'primary'} autoFocus>
            {actionType === 'delete' ? 'Delete' : 'Archive'}
          </Button>
        </DialogActions>
      </Dialog>
      <Box
        data-testid="document-item__component"
        role="button"
        tabIndex={0}
        onClick={() => navigate(`/due-diligence/companies/${companyId}/sites/${siteId}/due-diligence/${document.id}`)}
        onKeyDown={e => {
          if (e.key === 'Enter' || e.key === ' ') {
            navigate(`/due-diligence/companies/${companyId}/sites/${siteId}/due-diligence/${document.id}`);
          }
        }}
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '8px',
          minHeight: '80px',
          width: '100%',
          borderRight: 0,
          borderTop: 0,
          borderLeft: 0,
          borderBottom: '1px solid #E0E0E0',
          background: 'rgb(255, 255, 255)',
          textAlign: 'left',
          fontSize: '16px',
          lineHeight: '24px',
          cursor: 'pointer',
          fontFamily: 'Lato, sans-serif',
          transition:
            'background-color 250ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 250ms cubic-bezier(0.4, 0, 0.2, 1), border-color 250ms cubic-bezier(0.4, 0, 0.2, 1), color 250ms cubic-bezier(0.4, 0, 0.2, 1);',
          '&:last-child': {
            borderBottom: 0
          },
          '&:hover': {
            background: 'rgb(240, 240, 240)'
          }
        }}
      >
        <Box width="40%" ml="auto" display="inline" gap="12px">
          <Box component="span" marginInlineEnd="12px">
            {document.display_name || document.name}
          </Box>
          {document.ai_supported && (
            <Tooltip
              title="Supports AI parsing"
              componentsProps={{
                tooltip: { sx: { bgcolor: '#121212', borderRadius: '4px' } },
                popper: {
                  modifiers: [
                    {
                      name: 'offset',
                      options: {
                        offset: [72, -8]
                      }
                    }
                  ]
                }
              }}
            >
              <Chip
                label="AI"
                size="small"
                sx={{
                  cursor: 'default',
                  height: '22px',
                  fontWeight: 500,
                  fontSize: '13px',
                  lineHeight: '16px',
                  color: '#FFFFFF',
                  background: 'linear-gradient(245.75deg, #456CF3 7.17%, #8D4BE9 89.9%)'
                }}
              />
            </Tooltip>
          )}
        </Box>
        <Box width="15%">{filesCount(document.files_count)}</Box>
        <Box width="40%" minWidth="265px" height="100%" mr="auto">
          <Grid container spacing={2} justifyContent="flex-start" alignItems="center" wrap="nowrap">
            <Grid item xs={4} ml="auto">
              {document.status && (
                <Chip
                  label={document.status}
                  size="small"
                  sx={theme => ({
                    color: theme.palette.primary.main,
                    background: '#F4E998',
                    minWidth: '75px'
                  })}
                />
              )}
            </Grid>
            <Grid item mr="auto">
              <Assignee user={document.assignee} />
            </Grid>
            <Grid item ml="auto">
              <Button
                variant="outlined"
                sx={{ width: '120px', height: '32px', padding: '0', fontWeight: '500' }}
                onClick={e => {
                  e.stopPropagation();
                  navigate(`/due-diligence/companies/${companyId}/sites/${siteId}/due-diligence/${document.id}`);
                }}
              >
                Open
              </Button>
            </Grid>
            <Grid item>
              {hasFiles ? (
                <Tooltip title="Archive document">
                  <IconButton
                    size="small"
                    onClick={e => handleActionClick(e, 'archive')}
                    disabled={archiveMutation.isPending}
                  >
                    <ArchiveIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              ) : (
                <Tooltip title="Delete document">
                  <IconButton
                    size="small"
                    onClick={e => handleActionClick(e, 'delete')}
                    disabled={deleteMutation.isPending}
                    color="error"
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
            </Grid>
          </Grid>
        </Box>
      </Box>
    </>
  );
};

export default DocumentItem;
