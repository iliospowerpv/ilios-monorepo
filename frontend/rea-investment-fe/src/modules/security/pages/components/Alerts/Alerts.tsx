import React from 'react';
import { GridApi, ColDef, RowClickedEvent } from 'ag-grid-community';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import { useQuery, useMutation, queryOptions } from '@tanstack/react-query';

import { ApiClient } from '../../../../../api';
import BaseTable from '../../../../../components/common/tables/BaseTable/BaseTable';
import { SiteDetailsTabProps } from '../../../../operations-and-maintenance/pages/SiteDetails/tabs/types';
import IframeComponent from '../Iframe/Iframe';
import AddTaskForm from '../../../../../components/clusters/TasksCluster/internal/AddTaskForm/AddTaskForm';

dayjs.extend(utc);

export const boardQuery = (
  entityType: 'site' | 'company',
  entityId: number,
  enabled = true,
  throwOnError = false,
  module = 'O&M'
) =>
  queryOptions({
    queryKey: ['board', { entityType, entityId }],
    queryFn: () => ApiClient.taskManagement.getBoard({ entityType, entityId, module }),
    enabled: enabled,
    throwOnError: throwOnError ? true : undefined
  });

export const AlertsTab: React.FC<SiteDetailsTabProps> = ({ siteDetails, companyDetails }) => {
  const { id: siteId } = siteDetails;
  const { id: companyId } = companyDetails;
  const basicTableRef = React.useRef<{ getApi: () => GridApi | undefined }>(null);
  const [open, setOpen] = React.useState(false);
  const [url, setUrl] = React.useState('');
  const [name, setName] = React.useState('');
  const [isFormOpen, setIsFormOpen] = React.useState<boolean>(false);
  const [description, setDescription] = React.useState<string>('');
  const { data: boardInfo } = useQuery(boardQuery('site', siteId, true, true));
  const boardId = boardInfo ? Number.parseInt(boardInfo?.items[0].id as string) : -1;

  const { data: rowData } = useQuery({
    queryFn: async () => {
      return ApiClient.operationsAndMaintenance.alertsBySite(siteId);
    },
    queryKey: ['camera-alerts', { siteId }],
    staleTime: 1000 * 60 * 5
  });

  const { mutateAsync: resolveUrl } = useMutation({
    mutationFn: (alert_uuid: number) => ApiClient.operationsAndMaintenance.getCamerasUrlByAlertId(siteId, alert_uuid)
  });

  const handleModalConfirm = async (alert_uuid: number): Promise<any> => {
    return await resolveUrl(alert_uuid);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const onRowClicked = React.useCallback(
    async (e: RowClickedEvent) => {
      try {
        const res = await handleModalConfirm(e.data.alert_uuid);
        const date = dayjs.utc(e.data.timestamp).local().format('MM/DD/YY, hh:mm A');
        if (res && res.shared_clip_url) {
          setName(`${e.data.alert_type} - ${date}`);
          setUrl(res.shared_clip_url);
          setOpen(true);
        }
      } catch (error) {
        console.error('Error handling row click:', error);
      }
    },
    [handleModalConfirm]
  );

  const handleAddClick = async (data: any) => {
    try {
      await handleModalConfirm(data.alert_uuid).then(res => {
        const date = dayjs.utc(data.timestamp).local().format('MM/DD/YY, hh:mm A');
        if (res && res.shared_clip_url) {
          setDescription(
            `<p>ALERT</p><p>${data.alert_type} - ${date} <a target="_blank" rel="noopener noreferrer nofollow" href=${res.shared_clip_url}>link</a></p><p>${data.camera_name}</p>`
          );
          setIsFormOpen(true);
        }
      });
    } catch (error) {
      console.error('Error click:', error);
    }
  };

  const handleCloseForm = () => setIsFormOpen(false);

  const columns: ColDef[] = [
    {
      headerName: 'Alert Type',
      field: 'alert_type',
      flex: 1,
      editable: false,
      filter: false,
      sortable: false
    },
    {
      headerName: 'Camera Name',
      field: 'camera_name',
      flex: 1,
      editable: false,
      filter: false,
      sortable: false
    },
    {
      headerName: 'Timestamp',
      field: 'timestamp',
      flex: 1,
      editable: false,
      filter: false,
      sortable: false,
      cellRenderer: (params: any) => {
        const date = dayjs.utc(params.data.timestamp).local().format('MM/DD/YY hh:mm:ss A');
        return (
          <Box display="flex" alignItems="center">
            <Box>{date}</Box>
          </Box>
        );
      }
    },
    {
      headerName: 'Actions',
      sortable: false,
      cellRenderer: (params: any) => {
        return (
          <Button
            variant="contained"
            color="primary"
            sx={{ height: '32px', padding: '5px 16px', marginBottom: '5px', fontWeight: '500' }}
            ref={ref => {
              if (!ref) return;

              ref.onclick = e => {
                e.stopPropagation();
                handleAddClick(params.data);
              };
            }}
          >
            Create Task
          </Button>
        );
      }
    }
  ];

  return (
    <>
      <BaseTable
        ref={basicTableRef}
        rowIdKey="alert_uuid"
        rowData={rowData?.items}
        columnDefs={columns}
        onRowClicked={onRowClicked}
      />
      <IframeComponent openModal={open} url={url} handleClose={handleClose} name={name} />
      <AddTaskForm
        open={isFormOpen}
        onClose={handleCloseForm}
        boardId={boardId}
        scope={'site'}
        siteId={siteId}
        companyId={companyId}
        description={description}
      />
    </>
  );
};

export default AlertsTab;
