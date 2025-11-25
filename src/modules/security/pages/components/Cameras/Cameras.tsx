import React from 'react';

import { GridApi, ColDef, RowClickedEvent } from 'ag-grid-community';
import { ApiClient } from '../../../../../api';
import { SiteDetailsTabProps } from '../../../../operations-and-maintenance/pages/SiteDetails/tabs/types';
import Box from '@mui/material/Box';
import { useTheme } from '@mui/material';
import { useMutation, useQuery } from '@tanstack/react-query';
import IframeComponent from '../Iframe/Iframe';
import BaseTable from '../../../../../components/common/tables/BaseTable/BaseTable';

export const CamerasTab: React.FC<SiteDetailsTabProps> = ({ siteDetails }) => {
  const { id: siteId } = siteDetails;
  const basicTableRef = React.useRef<{ getApi: () => GridApi | undefined }>(null);
  const [open, setOpen] = React.useState(false);
  const [url, setUrl] = React.useState('');
  const [name, setName] = React.useState('');
  const [isCameraDisconnected, setIsCameraDisconnected] = React.useState(false);

  const { efficiencyColors, alertSeverity } = useTheme();
  const deviceSeverity: any = {
    GREEN: <Box bgcolor={efficiencyColors.good} borderRadius="50%" width="12px" height="12px" mt="14px" />,
    YELLOW: <Box bgcolor={efficiencyColors.mediocre} borderRadius="50%" width="12px" height="12px" mt="14px" />,
    RED: <Box bgcolor={alertSeverity.high} borderRadius="50%" width="12px" height="12px" mt="14px" />
  };

  const columns: ColDef[] = [
    {
      headerName: 'Camera Name',
      field: 'name',
      flex: 1,
      editable: false,
      filter: false,
      sortable: false
    },
    {
      headerName: 'Location',
      field: 'location',
      flex: 1,
      editable: false,
      filter: false,
      sortable: false
    },
    {
      headerName: 'Status',
      field: 'status',
      flex: 1,
      editable: false,
      filter: false,
      sortable: false,
      cellRenderer: (params: any) => (
        <Box display="flex" alignItems="center">
          {deviceSeverity[params.data.status]}
        </Box>
      )
    }
  ];

  const { data: rowData } = useQuery({
    queryFn: async () => {
      return ApiClient.operationsAndMaintenance.getCamerasById(siteId);
    },
    queryKey: ['cameras', { siteId }],
    staleTime: 1000 * 60 * 5
  });

  const { mutateAsync: resolveUrl } = useMutation({
    mutationFn: (url: number) => ApiClient.operationsAndMaintenance.getCamerasUrlById(siteId, url)
  });

  const handleModalConfirm = async (url: number): Promise<any> => {
    return await resolveUrl(url);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const onRowClicked = React.useCallback(
    async (e: RowClickedEvent) => {
      try {
        const res = await handleModalConfirm(e.data.uuid);
        if (res && res.live_stream_url) {
          setName(e.data.name);
          setUrl(res.live_stream_url);
          setOpen(true);
          setIsCameraDisconnected(e.data.status === 'RED');
        }
      } catch (error) {
        console.error('Error handling row click:', error);
      }
    },
    [handleModalConfirm]
  );

  return (
    <>
      <BaseTable
        ref={basicTableRef}
        rowIdKey="uuid"
        rowData={rowData?.items}
        columnDefs={columns}
        onRowClicked={onRowClicked}
      />
      <IframeComponent
        openModal={open}
        url={url}
        handleClose={handleClose}
        name={name}
        isDisconnected={isCameraDisconnected}
      />
    </>
  );
};

export default CamerasTab;
