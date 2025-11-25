import React, { useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

import { GridApi, RowClickedEvent } from 'ag-grid-community';
import Box from '@mui/material/Box';
import FlagIcon from '@mui/icons-material/Flag';
import { useTheme } from '@mui/material';
import Avatar from '@mui/material/Avatar';

import BaseTable from '../../../../common/tables/BaseTable/BaseTable';
import { ApiClient } from '../../../../../api';
import { TasksViewProps } from '../../types';

export const TaskList: React.FC<TasksViewProps> = ({ boardId, searchTerm, scope, companyId, siteId, module }) => {
  const navigate = useNavigate();
  const { efficiencyColors, color } = useTheme();
  const taskPriority: any = {
    High: <FlagIcon sx={{ color: efficiencyColors.low }} />,
    Low: <FlagIcon sx={{ color: efficiencyColors.good }} />,
    Medium: <FlagIcon sx={{ color: efficiencyColors.mediocre }} />
  };

  const avatarStyles = {
    width: 28,
    height: 28,
    marginRight: '4px !important',
    backgroundColor: color.blueGray,
    fontSize: '12px',
    fontWeight: '600'
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
      flex: 1
    },
    {
      headerName: 'Task ID',
      field: 'external_id',
      flex: 1
    },
    {
      headerName: 'Status',
      field: 'status.name',
      flex: 1,
      sortable: false
    },
    {
      headerName: 'Due Date',
      field: 'due_date',
      flex: 1,
      cellRenderer: (params: any) => {
        const date = params.data.due_date === null ? 'No due date' : dayjs(params.data.due_date).format('MM/DD/YY');
        return (
          <Box display="flex" alignItems="center">
            <Box>{date}</Box>
          </Box>
        );
      }
    },
    {
      headerName: 'Assigned to',
      field: 'assignee',
      flex: 1,
      sortable: false,
      cellRenderer: (params: any) => {
        const assignee = params.data.assignee;
        return (
          <Box display="flex" alignItems="center">
            {assignee ? (
              <>
                <Avatar
                  data-testid="document-new_comment-avatar"
                  sx={avatarStyles}
                  alt={assignee.first_name + ' ' + assignee.last_name}
                >
                  {assignee.first_name.charAt(0) + assignee.last_name.charAt(0)}
                </Avatar>
                <span>
                  {assignee.first_name} {assignee.last_name}
                </span>
              </>
            ) : (
              <span>Unassigned</span>
            )}
          </Box>
        );
      }
    }
  ];

  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const columns = getColumns();

  const onRowClicked = React.useCallback(
    (e: RowClickedEvent) => {
      if (module === 'O&M') {
        if (scope === 'site') {
          navigate(`/operations-and-maintenance/companies/${companyId}/sites/${siteId}/tasks/${e.data.id}`);
          return;
        }
        navigate(`/operations-and-maintenance/companies/${companyId}/tasks/${e.data.id}`);
        return;
      }
      if (scope === 'site') {
        navigate(`/asset-management/companies/${companyId}/sites/${siteId}/tasks/${e.data.id}`);
        return;
      }
      navigate(`/asset-management/companies/${companyId}/tasks/${e.data.id}`);
    },
    [navigate, companyId, siteId, scope, module]
  );

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.taskManagement
          .getTasks(boardId, {
            skip,
            limit,
            ...(searchTerm && { search: searchTerm }),
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
    [searchTerm, boardId]
  );

  return (
    <Box sx={{ pt: 1 }}>
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

export default TaskList;
