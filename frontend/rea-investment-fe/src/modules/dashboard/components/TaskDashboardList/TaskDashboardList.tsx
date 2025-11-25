import React, { useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

import { GridApi, RowClickedEvent } from 'ag-grid-community';
import Box from '@mui/material/Box';
import FlagIcon from '@mui/icons-material/Flag';
import { useTheme } from '@mui/material';
import Avatar from '@mui/material/Avatar';

import BaseTable from '../../../../components/common/tables/BaseTable/BaseTable';
import { ApiClient } from '../../../../api';
import Typography from '@mui/material/Typography';

export const TaskDashboardList: React.FC = () => {
  const navigate = useNavigate();
  const { efficiencyColors, color } = useTheme();
  const taskPriority: any = {
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
      cellRenderer: (params: any) => {
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
      cellRenderer: (params: any) => {
        const creator = params.data.creator;
        return (
          <Box display="flex" alignItems="center">
            {creator ? (
              <>
                <Avatar
                  data-testid="document-new_comment-avatar"
                  sx={avatarStyles}
                  alt={creator.first_name + ' ' + creator.last_name}
                >
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
      cellRenderer: (params: any) => {
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
        navigate(`/asset-management/companies/${e.data.company.id}/tasks/${e.data.id}`);
      } else if (module === 'Asset') {
        navigate(`/asset-management/companies/${site.company_id}/sites/${site.id}/tasks/${e.data.id}`);
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
      getRows: (params: any) => {
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
    <Box sx={{ pt: 1 }}>
      <Box
        sx={{
          borderTop: '1px solid #0000003B',
          borderRight: '1px solid #0000003B',
          borderLeft: '1px solid #0000003B'
        }}
      >
        <Typography variant="h6" fontSize="24px" p="16px">
          Tasks
        </Typography>
      </Box>
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        columnDefs={columns}
        serverSideDatasource={serverSideDatasource}
        onRowClicked={onRowClicked}
      />
    </Box>
  );
};

export default TaskDashboardList;
