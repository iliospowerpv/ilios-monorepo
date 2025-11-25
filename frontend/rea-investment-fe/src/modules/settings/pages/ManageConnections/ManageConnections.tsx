import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import AddIcon from '@mui/icons-material/Add';

import LoadingComponent from '../../../../components/common/LoadingComponent/LoadingComponent';
import NoConnections from './components/NoConnections/NoConnections';
import ConnectionItem from './components/ConnectionItem/ConnectionItem';
import { ConnectionForm } from '../../../../components/forms/ConnectionForm/ConnectionForm';
import { ApiClient, Connection, ConnectionResponse } from '../../../../api';
import { ConfirmationModal } from '../../../../components/modals/ConfirmationModal/ConfirmationModal';
import { useNotify } from '../../../../contexts/notifications/notifications';

export const ManageConnectionsPage: React.FC = () => {
  const { companyId } = useParams();
  const isValidId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));

  const notify = useNotify();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [confirmationModalOpen, setConfirmationModalOpen] = useState(false);
  const [connections, setConnections] = useState<Connection[] | []>([]);
  const [selectedConnection, setSelectedConnection] = useState<Connection>();

  const {
    data: connectionData,
    isLoading: isLoadingConnectionData,
    isFetching
  } = useQuery({
    queryFn: async () => {
      const id = isValidId ? Number.parseInt(companyId) : -1;
      return ApiClient.connections.getConnections(id);
    },
    queryKey: ['connections', { companyId }],
    enabled: isValidId
  });

  const addConnection = () => {
    const newConnection = { id: +Date.now(), name: '', provider: '', token: '', isEditing: true, isNotSaved: true };

    setSelectedConnection(newConnection);
    setConnections([...connections, newConnection]);
  };

  const handleDelete = (connection: Connection, isCancel?: boolean) => {
    if (!isCancel) {
      setConfirmationModalOpen(true);
    }

    setSelectedConnection(connection);
  };

  const handleEdit = (connection: Connection) => {
    setSelectedConnection(connection);
    setConnections(prevConnections =>
      prevConnections?.map(item => (item.id === connection.id ? { ...item, isEditing: !item?.isEditing } : item))
    );
  };

  const handleCancel = (connection: Connection) => {
    if (connection.isNotSaved) {
      setConnections(connections?.filter(item => item.id !== connection?.id));
    } else {
      handleEdit(connection);
    }
  };

  const handleSave = (connection: Connection) => {
    setConnections(prevConnections =>
      prevConnections?.map(item => (item.id === connection.id ? { ...connection, isNotSaved: false } : item))
    );
    handleEdit(connection);
    queryClient.invalidateQueries({ queryKey: ['connections', { companyId }] });
  };

  const handleConfirmModalClose = () => {
    setConfirmationModalOpen(false);
  };

  const handleModalConfirm = () => {
    setConfirmationModalOpen(false);

    const id = isValidId ? Number.parseInt(companyId) : -1;
    if (selectedConnection) {
      ApiClient.connections
        .deleteConnection(id, selectedConnection?.id)
        .then((response: ConnectionResponse) => {
          queryClient.invalidateQueries({ queryKey: ['connections', { companyId }] });
          notify(response.message || 'Connection has been successfully deleted');
        })
        .catch(e => {
          notify(e?.response?.data?.message || 'Failed to delete connection. Please try again.');
        });
    }
  };

  useEffect(() => {
    if (connectionData) {
      setConnections([...connectionData.items]);
    }
  }, [connectionData]);

  return (
    <>
      <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
        <Typography my="64px" variant="h4" fontWeight={600} data-testid="manage-connection__form-title">
          Manage Connections
        </Typography>
        {!isValidId && (
          <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
            {`Provided companyId "${companyId}" is invalid.`}
          </Alert>
        )}
        {isValidId && (
          <Stack width="30%" minWidth="320px" spacing={2}>
            <>
              {isLoadingConnectionData || isFetching ? (
                <LoadingComponent />
              ) : !connections.length ? (
                <NoConnections />
              ) : (
                connections.map((connection: Connection) =>
                  connection.isEditing ? (
                    <ConnectionForm
                      key={connection.id}
                      companyId={+companyId}
                      connection={connection}
                      onCancel={() => handleCancel(connection)}
                      onSave={() => handleSave(connection)}
                    />
                  ) : (
                    <ConnectionItem
                      key={connection.id}
                      connection={connection}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                    />
                  )
                )
              )}
            </>
            <Box>
              <Button variant="text" startIcon={<AddIcon />} onClick={addConnection}>
                Add New Connection
              </Button>
            </Box>
            <Button fullWidth variant="outlined" onClick={() => navigate(-1)}>
              Back
            </Button>
          </Stack>
        )}
      </Stack>
      <ConfirmationModal
        open={confirmationModalOpen}
        confirmationTitle="Delete Connection?"
        confirmationMessage="This action cannot be undone, and the dashboard data may no longer be up to date."
        confirmationDisabled={false}
        onClose={handleConfirmModalClose}
        onConfirm={handleModalConfirm}
      />
    </>
  );
};

export default ManageConnectionsPage;
