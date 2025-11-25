import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import { ColDef, GridApi } from 'ag-grid-community';
import { ApiClient } from '../../../../../../api';
import ActionButtons from '../../../../../../components/common/tables/components/ActionButtons/ActionButtons';
import SearchAndActions from '../../../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import formatPhoneNumber from '../../../../../../utils/formatters/formatPhoneNumber';

const columns: ColDef[] = [
  {
    headerName: 'Name',
    field: 'name',
    flex: 1
  },
  {
    headerName: 'Type',
    field: 'company_type',
    flex: 1
  },
  {
    headerName: 'Email',
    field: 'email',
    flex: 1
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
    headerName: 'Address',
    field: 'address',
    flex: 1
  },
  {
    field: 'actions',
    editable: false,
    filter: false,
    sortable: false,
    cellRenderer: (params: any) => (
      <ActionButtons
        isRegistered={true}
        isAdd={true}
        isEdit={true}
        isLink={true}
        isDelete={false}
        data={params.data}
        onAdd={`/settings/company/${params.data.id}/site/add/`}
        onEdit={`/settings/company/${params.data.id}`}
        onLink={`/settings/company/${params.data.id}/connections`}
        onDelete={(data: any) => console.log('Delete', data)}
      />
    )
  }
];

const Companies = () => {
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const navigate = useNavigate();

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.assetManagement
          .contractors({
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
    navigate('/settings/company/add');
  };

  return (
    <>
      <SearchAndActions
        showSearch={true}
        showExport={false}
        showAdd={true}
        searchPlaceholder="Search by Name"
        btnAddLabel="Add a New Company"
        onSearch={handleSearch}
        onAdd={handleAddClick}
      />
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        disableRowHover={true}
        columnDefs={columns}
        serverSideDatasource={serverSideDatasource}
      />
    </>
  );
};

export default Companies;
