import React, { useMemo, useRef } from 'react';
import { GridApi } from 'ag-grid-community';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

import { ApiClient } from '../../../../../../api';
import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import { Button, useTheme } from '@mui/material';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import Box from '@mui/material/Box';
import { useMutation } from '@tanstack/react-query';
import ConfirmationModal from '../../../../../../components/modals/ConfirmationModal/ConfirmationModal';
import { useNotify } from '../../../../../../contexts/notifications/notifications';

dayjs.extend(utc);

const AlertsTab: React.FC<any> = ({ deviceDetails }) => {
  const { alertSeverity } = useTheme();
  const deviceSeverity: any = {
    critical: <BoltRoundedIcon />,
    warning: <WarningRoundedIcon sx={{ color: alertSeverity.warning }} />,
    high: <WarningRoundedIcon sx={{ color: alertSeverity.high }} />
  };
  const columns = [
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
      headerName: 'Actions',
      sortable: false,
      cellRenderer: (params: any) => (
        <Button
          variant="contained"
          color="primary"
          sx={{ height: '32px', marginBottom: '6px', padding: '0', fontWeight: '500' }}
          onClick={() => {
            handleClickResolve(params.data.id);
          }}
          disabled={params.data.is_resolved}
        >
          Resolve
        </Button>
      )
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
    }
  ];

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
      notify(response.message || `Alert was successfully resolve.`);
      setConfirmationModalOpen(false);
      setAlertID(0);
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
          .deviceAlerts(deviceDetails.id, {
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
  }, [alertID, deviceDetails.id]);
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
    </>
  );
};

export default AlertsTab;
