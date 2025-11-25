import React, { useMemo, useRef } from 'react';
import { GridApi, ColDef } from 'ag-grid-community';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import { useTheme } from '@mui/material';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import Box from '@mui/material/Box';
import { useMutation, useQuery } from '@tanstack/react-query';
import NotificationsOffIcon from '@mui/icons-material/NotificationsOff';
import AddTaskIcon from '@mui/icons-material/AddTask';
import IconButton from '@mui/material/IconButton';

import { ApiClient } from '../../../../../../api';
import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import ConfirmationModal from '../../../../../../components/modals/ConfirmationModal/ConfirmationModal';
import { useNotify } from '../../../../../../contexts/notifications/notifications';
import AddTaskForm from '../../../../../../components/clusters/TasksCluster/internal/AddTaskForm/AddTaskForm';

dayjs.extend(utc);

interface CreateTaskFromAlertContext {
  boardId: number;
  alertId: number;
  description: string;
  alertSeverity: string;
}

const AlertsTab: React.FC<any> = ({ siteDetails, companyDetails }) => {
  const { alertSeverity } = useTheme();
  const siteId = siteDetails.id as number;
  const companyId = companyDetails.id as number;

  const [createTaskContext, setCreateTaskContext] = React.useState<CreateTaskFromAlertContext | null>(null);

  const { data: taskBoards, isLoading: isLoadingTaskBoards } = useQuery({
    queryKey: ['boards', { entityType: 'site', entityId: siteId, module: 'O&M' }],
    queryFn: () => ApiClient.taskManagement.getBoard({ entityType: 'site', entityId: siteId, module: 'O&M' }),
    throwOnError: true
  });

  const deviceSeverity: any = React.useMemo(
    () => ({
      Critical: <BoltRoundedIcon />,
      Informational: <WarningRoundedIcon sx={{ color: alertSeverity.warning }} />,
      Warning: <WarningRoundedIcon sx={{ color: alertSeverity.high }} />
    }),
    [alertSeverity]
  );

  const onCreateTaskClick = React.useCallback(
    (data: any) => {
      if (!taskBoards) throw new Error('The task board cannot be found.');

      const [board] = taskBoards.items;
      const boardId = board.id as unknown as number;
      const alertId = data.id;
      const alertCategory = data.type;
      const alertSeverity = data.severity;
      const alertErrorMessage = data.error_message;
      const alertStart = dayjs.utc(data.alert_start).local().format('MM/DD/YY hh:mm:ss A');

      const description = `<p>ALERT</p><p>Alert Category - ${alertCategory}</p><p>Severity - ${alertSeverity}</p><p>Error Message - ${alertErrorMessage}</p><p>Alert Start - ${alertStart}</p>`;

      setCreateTaskContext({
        boardId,
        alertId,
        description,
        alertSeverity
      });
    },
    [taskBoards]
  );

  const onCreateTaskModalClose = React.useCallback(() => setCreateTaskContext(null), []);

  const columns: ColDef[] = React.useMemo(
    () => [
      {
        headerName: 'Alert Type',
        field: 'type',
        flex: 1
      },
      {
        headerName: 'Severity',
        field: 'severity',
        flex: 1,
        cellRenderer: (params: any) => (
          <Box display="flex" alignItems="center">
            {deviceSeverity[params.data.severity]}
            <Box sx={{ paddingLeft: '10px' }}>
              {params.data.severity?.charAt(0)?.toUpperCase() + params.data.severity?.slice(1)}
            </Box>
          </Box>
        )
      },
      {
        headerName: 'Device Name',
        field: 'device_name',
        flex: 1
      },
      {
        headerName: 'Error Message',
        field: 'error_message',
        flex: 1,
        sortable: false
      },
      {
        headerName: 'Alert Start',
        field: 'alert_start',
        flex: 1,
        cellRenderer: (params: any) => {
          const date = dayjs.utc(params.data.alert_start).local().format('MM/DD/YY hh:mm:ss A');
          return (
            <Box display="flex" alignItems="center">
              <Box>{date}</Box>
            </Box>
          );
        }
      },
      {
        headerName: 'Duration',
        field: 'error_message',
        flex: 1,
        sortable: false,
        cellRenderer: (params: any) => {
          const date = dayjs.utc(params.data.alert_start).local();
          const durationInMinutes = dayjs().diff(date, 'minutes');
          const hours = Math.floor(durationInMinutes / 60);
          const minutes = durationInMinutes % 60;
          return (
            <Box display="flex" alignItems="center">
              <Box>{`${hours}h ${minutes}m`}</Box>
            </Box>
          );
        }
      },
      {
        headerName: 'Task ID',
        flex: 1,
        sortable: false,
        field: 'task.external_id'
      },
      {
        headerName: 'Task Status',
        flex: 1,
        sortable: false,
        field: 'task.status.name'
      },
      {
        headerName: 'Actions',
        sortable: false,
        cellRenderer: (params: any) => (
          <Box height="100%" width="100%" display="flex">
            <Box display="flex" alignItems="center">
              <IconButton
                sx={{ mr: '4px' }}
                size="small"
                title="Resolve"
                onClick={() => handleClickResolve(params.data.id)}
                disabled={params.data.is_resolved}
              >
                <NotificationsOffIcon />
              </IconButton>
              <IconButton
                title="Create a Task"
                size="small"
                disabled={!!params?.data?.task || isLoadingTaskBoards || !taskBoards}
                onClick={() => onCreateTaskClick(params.data)}
              >
                <AddTaskIcon />
              </IconButton>
            </Box>
          </Box>
        )
      }
    ],
    [deviceSeverity, isLoadingTaskBoards, taskBoards, onCreateTaskClick]
  );

  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [confirmationModalOpen, setConfirmationModalOpen] = React.useState(false);
  const [alertID, setAlertID] = React.useState(0);
  const notify = useNotify();

  const { mutateAsync: resolveAlert, isPending: isResolvePending } = useMutation({
    mutationFn: () => ApiClient.operationsAndMaintenance.companyAlertResolve(alertID)
  });
  const handleClickResolve = (id: number): void => {
    setAlertID(id);
    setConfirmationModalOpen(true);
  };

  const handleModalClose = (): void => {
    setAlertID(0);
    setConfirmationModalOpen(false);
  };

  const handleModalConfirm = async (): Promise<void> => {
    try {
      const response = await resolveAlert();
      notify(response.message || `Alert was successfully resolved.`);
      setConfirmationModalOpen(false);
      setAlertID(0);
      basicTableRef.current?.getApi()?.refreshServerSide({ purge: true });
    } catch (e: any) {
      notify(e?.response?.data?.message || 'Alert resolve failed');
    }
  };

  const serverSideDatasource = useMemo(() => {
    return {
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;
        ApiClient.operationsAndMaintenance
          .siteAlerts(siteDetails.id, {
            skip,
            limit,
            ...(orderBy && { order_by: orderBy }),
            ...(orderDirection && { order_direction: orderDirection }),
            is_resolved: false
          })
          .then(data => {
            if (!data.items.length) {
              api?.showNoRowsOverlay();
            } else {
              api?.hideOverlay();
            }

            params.success({
              rowData: data.items,
              rowCount: data.total
            });
          })
          .catch(() => {
            params?.fail();
          });
      }
    };
  }, [siteDetails.id]);
  return (
    <>
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        disableRowHover={true}
        columnDefs={columns}
        serverSideDatasource={serverSideDatasource}
      />
      <ConfirmationModal
        open={confirmationModalOpen}
        confirmationMessage="Are you sure you want to resolve this alert?"
        confirmationDisabled={isResolvePending}
        onClose={handleModalClose}
        onConfirm={handleModalConfirm}
      />
      <AddTaskForm
        open={!!createTaskContext}
        onClose={onCreateTaskModalClose}
        boardId={createTaskContext ? createTaskContext.boardId : -1}
        scope="site"
        siteId={siteId}
        companyId={companyId}
        module="O&M"
        description={createTaskContext ? createTaskContext.description : undefined}
        alertId={createTaskContext ? createTaskContext.alertId : null}
        alertSeverity={createTaskContext ? createTaskContext.alertSeverity : null}
      />
    </>
  );
};

export default AlertsTab;
