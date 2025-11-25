import React, { useRef, useState } from 'react';
import { ColDef, GridApi } from 'ag-grid-community';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '@mui/material/styles';

import { ApiClient, CompanyDetails } from '../../../../../../api';
import SearchAndActions from '../../../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import ActionButtons from '../../../../../../components/common/tables/components/ActionButtons/ActionButtons';
import formatPhoneNumber from '../../../../../../utils/formatters/formatPhoneNumber';

export interface CompanyDetailsTabProps {
  companyDetails: CompanyDetails;
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
        onEdit={`/settings/my-company/users/${params?.data?.id}/edit`}
        onDelete={(data: any) => console.log('Delete', data)}
        hideEditActions={typeof params?.data?.parent_company_id !== 'number'}
      />
    )
  }
];

export const UsersTab: React.FC<CompanyDetailsTabProps> = () => {
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const navigate = useNavigate();
  const theme = useTheme();

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.myCompany
          .getMyCompanyUsers({
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

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleAddClick = () => {
    navigate(`/settings/my-company/users/add`);
  };

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
        showExport={false}
        showAdd={true}
        searchPlaceholder="Search by Name or Email"
        btnAddLabel="Add a New User"
        onSearch={handleSearch}
        onAdd={handleAddClick}
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

export default UsersTab;
