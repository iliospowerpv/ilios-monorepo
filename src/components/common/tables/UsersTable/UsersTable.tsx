import React, { useCallback, useRef, useState } from 'react';
import BaseTable from '../BaseTable/BaseTable';
import SearchAndActions from '../components/SearchAndActions/SearchAndActions';
import { ColDef, GridApi } from 'ag-grid-community';
import { ApiClient } from '../../../../api';
import { useTheme } from '@mui/material/styles';
import { useNavigate } from 'react-router-dom';
import ActionButtons from '../components/ActionButtons/ActionButtons';
import formatPhoneNumber from '../../../../utils/formatters/formatPhoneNumber';

interface UsersTableProps {
  searchPlaceholder?: string;
  btnAddLabel?: string;
  customActions?: React.ReactElement;
}

const columnDefs: ColDef[] = [
  {
    field: 'first_name',
    headerName: 'First Name',
    flex: 1
  },
  {
    field: 'last_name',
    headerName: 'Last Name',
    flex: 1
  },
  {
    field: 'email',
    flex: 1,
    sortable: false
  },
  {
    headerName: 'Phone Number',
    field: 'phone',
    flex: 1,
    filter: false,
    sortable: false,
    valueFormatter: ({ value }) =>
      typeof value === 'string' || typeof value === 'number' ? formatPhoneNumber(value) : ''
  },
  {
    field: 'role.name',
    colId: 'role',
    flex: 1
  },
  {
    field: 'actions',
    editable: false,
    filter: false,
    sortable: false,
    cellRenderer: (params: any) => (
      <ActionButtons
        data={params.data}
        isRegistered={params.data.is_registered}
        isEdit={true}
        isDelete={false}
        onEdit={`/settings/users/${params?.data?.id}/edit`}
        onDelete={(data: any) => console.log('Delete', data)}
        hideEditActions={typeof params?.data?.parent_company_id !== 'number'}
      />
    )
  }
];

const UsersTable: React.FC<UsersTableProps> = ({ customActions, searchPlaceholder, btnAddLabel }) => {
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const theme = useTheme();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState<string>('');

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleAddClick = () => {
    navigate('/settings/users/add');
  };

  const handleExport = useCallback(() => {
    const api = basicTableRef.current?.getApi();

    api?.exportDataAsCsv();
  }, []);

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.user
          .users({
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
    [searchTerm]
  );

  const getRowStyle = React.useCallback(
    (params: any) => {
      if (!params?.data?.is_registered) {
        return { color: theme.palette.text.disabled };
      }
    },
    [theme]
  );

  return (
    <>
      <SearchAndActions
        showSearch={true}
        showExport={true}
        showAdd={true}
        searchPlaceholder={searchPlaceholder}
        btnAddLabel={btnAddLabel}
        onSearch={handleSearch}
        onExport={handleExport}
        onAdd={handleAddClick}
        customActions={customActions}
      />
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        disableRowHover={true}
        columnDefs={columnDefs}
        getRowStyle={getRowStyle}
        serverSideDatasource={serverSideDatasource}
      />
    </>
  );
};

export default UsersTable;
