import React, { useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

import { GridApi, RowClickedEvent } from 'ag-grid-community';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import FlagIcon from '@mui/icons-material/Flag';
import { useTheme } from '@mui/material';
import Avatar from '@mui/material/Avatar';
import Typography from '@mui/material/Typography';

import BaseTable from '../../../../components/common/tables/BaseTable/BaseTable';
import { ApiClient } from '../../../../api';

export const HomeTasks: React.FC = () => {
  const navigate = useNavigate();
  const { efficiencyColors, color } = useTheme();
  const taskPriority: Record<string, React.ReactNode> = {
    High: <FlagIcon sx={{ color: efficiencyColors.low }} />,
    Low: <FlagIcon sx={{ color: efficiencyColors.good }} />,
    Medium: <FlagIcon sx={{ color: efficiencyColors.mediocre }} />
  };

  const avatarStyles = {
    width: 32,
    height: 32,
    marginRight: '4px !important',
    backgroundColor: color.blueGray,
    fontSize: '12px',
    fontWeight: '700'
  };

  const getColumns = () => [
    {
      headerName: 'Priority',
      field: 'priority',
      width: '80px',
      sortable: false,
      cellRenderer: (params: { data: { priority: string } }) => {
        return (
          <Box display="flex" alignItems="center" mt="6px">
            {taskPriority[params.data.priority]}
          </Box>
        );
      }
    },
    {
      headerName: 'Task Name',
      field: 'name',
      flex: 1,
      sortable: false
    },
    {
      headerName: 'Task ID',
      field: 'external_id',
      width: '80px',
      sortable: false
    },
    {
      headerName: 'Status',
      field: 'status.name',
      flex: 1,
      sortable: false
    },
    {
      headerName: 'Module',
      field: 'module',
      width: '80px',
      sortable: false
    },
    {
      headerName: 'Created by',
      field: 'creator',
      flex: 1,
      sortable: false,
      cellRenderer: (params: { data: { creator: { first_name: string; last_name: string } | null } }) => {
        const creator = params.data.creator;
        return (
          <Box display="flex" alignItems="center">
            {creator ? (
              <>
                <Avatar sx={avatarStyles} alt={creator.first_name + ' ' + creator.last_name}>
                  {creator.first_name.charAt(0) + creator.last_name.charAt(0)}
                </Avatar>
                <span>
                  {creator.first_name} {creator.last_name}
                </span>
              </>
            ) : (
              <span>Unassigned</span>
            )}
          </Box>
        );
      }
    },
    {
      headerName: 'Due Date',
      field: 'due_date',
      width: '95px',
      sortable: false,
      cellRenderer: (params: { data: { due_date: string | null } }) => {
        const date = params.data.due_date === null ? 'No due date' : dayjs(params.data.due_date).format('MM/DD/YY');
        return (
          <Box display="flex" alignItems="center">
            <Box>{date}</Box>
          </Box>
        );
      }
    }
  ];

  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const columns = getColumns();

  const onRowClicked = React.useCallback(
    (e: RowClickedEvent) => {
      const site = e.data.site;
      const module = e.data.module;

      if (module === 'Asset' && e?.data?.company) {
        navigate(`/project-hub/companies/${e.data.company.id}/tasks/${e.data.id}`);
      } else if (module === 'Asset') {
        navigate(`/project-hub/companies/${site.company_id}/sites/${site.id}/tasks/${e.data.id}`);
      }

      if (module === 'Diligence') {
        const document = e.data.document;
        navigate(
          `/due-diligence/companies/${document.company_id}/sites/${document.site_id}/due-diligence/${document.id}`
        );
      }

      if (module === 'O&M') {
        if (site) {
          navigate(`/operations-and-maintenance/companies/${site.company_id}/sites/${site.id}/tasks/${e.data.id}`);
        }
        navigate(`/operations-and-maintenance/companies/${e.data.company.id}/tasks/${e.data.id}`);
      }
    },
    [navigate]
  );

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: {
        request: { startRow: number; endRow: number; sortModel: { colId: string; sort: string }[] };
        success: (data: { rowData: unknown[]; rowCount: number }) => void;
        fail: () => void;
      }) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.dashboard
          .getDashboardTasks({
            skip,
            limit,
            ...(orderBy && { order_by: orderBy }),
            ...(orderDirection && { order_direction: orderDirection })
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
    }),
    []
  );

  return (
    <Card>
      <CardContent sx={{ p: 0 }}>
        <Box
          sx={{
            borderBottom: theme => `1px solid ${theme.palette.divider}`,
            px: 2,
            py: 1.5
          }}
        >
          <Typography variant="h6">Tasks</Typography>
        </Box>
        <Box sx={{ height: 400 }}>
          <BaseTable
            ref={basicTableRef}
            rowModelType="serverSide"
            columnDefs={columns}
            serverSideDatasource={serverSideDatasource}
            onRowClicked={onRowClicked}
          />
        </Box>
      </CardContent>
    </Card>
  );
};

export default HomeTasks;
