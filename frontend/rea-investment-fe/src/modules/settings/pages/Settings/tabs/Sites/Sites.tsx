import React, { useRef, useState } from 'react';

import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import { GridApi } from 'ag-grid-community';
import { ApiClient } from '../../../../../../api';
import ActionButtons from '../../../../../../components/common/tables/components/ActionButtons/ActionButtons';
import SearchAndActions from '../../../../../../components/common/tables/components/SearchAndActions/SearchAndActions';

const columns = [
  {
    headerName: 'Site Name',
    field: 'name',
    flex: 1
  },
  {
    headerName: 'Company Name',
    field: 'company_name',
    flex: 1
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
        isEdit={true}
        data={params.data}
        onEdit={`/settings/company/${params.data.company_id}/site/${params.data.id}/edit`}
      />
    )
  }
];

const Sites = () => {
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.settings
          .sites({
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

  return (
    <>
      <SearchAndActions
        showSearch={true}
        searchPlaceholder="Search by Name"
        btnAddLabel="Add a New Site"
        onSearch={handleSearch}
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

export default Sites;
