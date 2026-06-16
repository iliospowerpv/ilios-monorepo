import React, { useMemo, useRef } from 'react';
import { GridApi } from 'ag-grid-community';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import { useTheme } from '@mui/material/styles';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import { useMutation } from '@tanstack/react-query';

import { ApiClient } from '../../../../../../api';
import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import ConfirmationModal from '../../../../../../components/modals/ConfirmationModal/ConfirmationModal';
import { useNotify } from '../../../../../../contexts/notifications/notifications';
import type { DeviceDetailsTabProps } from '../types';

dayjs.extend(utc);

/**
 * Project Hub Device Details "Alerts" tab.
 *
 * Reuses the Postgres-backed O&M alert APIs (`deviceAlerts` reads, paginated,
 * from the `alerts` table via SQLAlchemy; `companyAlertResolve` flips
 * `is_resolved`). This is API reuse only — the orphaned O&M alerts *route* is
 * NOT relinked; this tab lives entirely inside the Project Hub device surface
 * and is scoped by the `deviceId` route param (never a BigQuery/Firestore
 * source). Server-side pagination is preserved via AG Grid's serverSide model.
 */
const AlertsTab: React.FC<DeviceDetailsTabProps> = ({ deviceId }) => {
  const { alertSeverity } = useTheme();
  const notify = useNotify();
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [confirmationModalOpen, setConfirmationModalOpen] = React.useState(false);
  const [alertID, setAlertID] = React.useState(0);

  const severityIcon: Record<string, React.ReactElement> = {
    critical: <BoltRoundedIcon sx={{ color: alertSeverity.severe }} />,
    severe: <BoltRoundedIcon sx={{ color: alertSeverity.severe }} />,
    warning: <WarningRoundedIcon sx={{ color: alertSeverity.warning }} />,
    high: <WarningRoundedIcon sx={{ color: alertSeverity.high }} />
  };

  const handleClickResolve = (id: number): void => {
    setAlertID(id);
    setConfirmationModalOpen(true);
  };

  const columns = [
    { headerName: 'Alert Type', field: 'type', flex: 1 },
    {
      headerName: 'Severity',
      field: 'severity',
      flex: 1,
      cellRenderer: (params: any) => (
        <Box display="flex" alignItems="center">
          {severityIcon[params.data.severity]}
          <Box sx={{ paddingLeft: '10px' }}>
            {params.data.severity ? params.data.severity.charAt(0).toUpperCase() + params.data.severity.slice(1) : ''}
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
          onClick={() => handleClickResolve(params.data.id)}
          disabled={params.data.is_resolved}
        >
          Resolve
        </Button>
      )
    },
    { headerName: 'Error Message', field: 'error_message', flex: 1, sortable: false },
    {
      headerName: 'Alert Start',
      field: 'alert_start',
      flex: 1,
      cellRenderer: (params: any) => {
        const start = dayjs.utc(params.data.alert_start);
        return (
          <Box display="flex" alignItems="center">
            <Box>{start.isValid() ? start.local().format('MM/DD/YY hh:mm:ss A') : 'Unavailable'}</Box>
          </Box>
        );
      }
    },
    {
      headerName: 'Duration',
      field: 'alert_start',
      flex: 1,
      sortable: false,
      cellRenderer: (params: any) => {
        const start = dayjs.utc(params.data.alert_start);
        if (!start.isValid()) {
          return (
            <Box display="flex" alignItems="center">
              <Box>Unavailable</Box>
            </Box>
          );
        }
        const durationInMinutes = dayjs().diff(start.local(), 'minutes');
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

  const { mutateAsync: resolveAlert, isPending: isResolvePending } = useMutation({
    mutationFn: () => ApiClient.operationsAndMaintenance.companyAlertResolve(alertID)
  });

  const handleModalClose = (): void => {
    setAlertID(0);
    setConfirmationModalOpen(false);
  };

  const handleModalConfirm = async (): Promise<void> => {
    try {
      const response = await resolveAlert();
      notify(response.message || 'Alert was successfully resolved.');
      setConfirmationModalOpen(false);
      setAlertID(0);
      basicTableRef.current?.getApi()?.refreshServerSide({ purge: true });
    } catch (e: any) {
      notify(e?.response?.data?.message || 'Alert resolve failed');
    }
  };

  const serverSideDatasource = useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;
        ApiClient.operationsAndMaintenance
          .deviceAlerts(deviceId, {
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
            params.success({ rowData: data.items, rowCount: data.total });
          })
          .catch(() => {
            params?.fail();
          });
      }
    }),
    [deviceId]
  );

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
