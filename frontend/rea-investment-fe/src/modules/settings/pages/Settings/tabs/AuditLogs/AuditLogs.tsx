import React, { useRef, useCallback } from 'react';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import Box from '@mui/material/Box';
import { GridApi } from 'ag-grid-community';
import { useQueryClient } from '@tanstack/react-query';

import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import { ApiClient } from '../../../../../../api';
import { auditLogQueryKeys } from '../../../../../../api/audit-log';
import type { AuditLogs as AuditLogsResponse } from '../../../../../../api/audit-log';

dayjs.extend(utc);

const STALE_TIME = 30_000;

const columns = [
  {
    headerName: 'User Name',
    field: 'user_name',
    filter: false,
    sortable: false,
    flex: 1
  },
  {
    headerName: 'Email',
    field: 'user_email',
    filter: false,
    sortable: false,
    flex: 1
  },
  {
    headerName: 'Source',
    field: 'source',
    filter: false,
    sortable: false,
    flex: 1
  },
  {
    headerName: 'Action',
    field: 'action',
    filter: false,
    sortable: false,
    flex: 1
  },
  {
    headerName: 'Success',
    field: 'is_success',
    filter: false,
    sortable: false,
    flex: 1,
    cellRenderer: (params: any) => {
      return (
        <Box display="flex" alignItems="center">
          <Box sx={{ textTransform: 'capitalize' }}>{params.data.is_success.toString()}</Box>
        </Box>
      );
    }
  },
  {
    headerName: 'Details',
    field: 'details',
    filter: false,
    sortable: false,
    flex: 1
  },
  {
    headerName: 'Time',
    field: 'created_at',
    filter: false,
    sortable: false,
    flex: 1,
    cellRenderer: (params: any) => {
      const date = dayjs.utc(params.data.created_at).local().format('MM/DD/YY hh:mm:ss A');
      return (
        <Box display="flex" alignItems="center">
          <Box>{date}</Box>
        </Box>
      );
    }
  }
];

const AuditLogs = () => {
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const queryClient = useQueryClient();

  const deliverData = useCallback((data: AuditLogsResponse, params: any) => {
    const api = basicTableRef.current?.getApi();
    if (!data.items.length) {
      api?.showNoRowsOverlay();
    } else {
      api?.hideOverlay();
    }
    params.success({
      rowData: data.items,
      rowCount: data.total
    });
  }, []);

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: any) => {
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const queryKey = auditLogQueryKeys.page(skip, limit);

        const cached = queryClient.getQueryData<AuditLogsResponse>(queryKey);
        if (cached) {
          deliverData(cached, params);

          queryClient.prefetchQuery({
            queryKey,
            queryFn: () => ApiClient.auditLog.getAuditLogs({ skip, limit }),
            staleTime: STALE_TIME
          });
          return;
        }

        queryClient
          .fetchQuery({
            queryKey,
            queryFn: () => ApiClient.auditLog.getAuditLogs({ skip, limit }),
            staleTime: STALE_TIME
          })
          .then(data => {
            deliverData(data, params);
          })
          .catch(() => {
            params?.fail();
          });
      }
    }),
    [queryClient, deliverData]
  );

  return (
    <BaseTable
      ref={basicTableRef}
      rowModelType="serverSide"
      disableRowHover={true}
      columnDefs={columns}
      serverSideDatasource={serverSideDatasource}
    />
  );
};

export default AuditLogs;
