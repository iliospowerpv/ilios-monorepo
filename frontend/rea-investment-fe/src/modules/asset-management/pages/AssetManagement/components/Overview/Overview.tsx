import React, { useRef, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import { ColDef, GridApi, RowClickedEvent } from 'ag-grid-community';
import { ApiClient } from '../../../../../../api';
import { formatFloatValue } from '../../../../../../utils/formatters/formatFloatValue';

const columns = [
  {
    headerName: 'Company Name',
    field: 'name',
    flex: 1,
    editable: false,
    filter: false,
    sortable: true
  },
  {
    headerName: 'Number of Sites',
    field: 'total_sites',
    flex: 1,
    editable: false,
    filter: false,
    sortable: true
  },
  {
    headerName: 'System Size (kW)',
    field: 'total_capacity',
    flex: 1,
    editable: false,
    filter: false,
    sortable: true,
    cellRenderer: (data: any) => {
      return typeof data?.value === 'number' ? formatFloatValue(data.value) : '';
    }
  }
];

const Overview = () => {
  const navigate = useNavigate();
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [colDefs] = useState<ColDef[]>(columns);

  const serverSideDatasource = useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.assetManagement
          .companies({
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

  const onRowClicked = useCallback(
    (e: RowClickedEvent) => {
      navigate(`/asset-management/companies/${e.data.id}`);
    },
    [navigate]
  );

  return (
    <>
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        columnDefs={colDefs}
        serverSideDatasource={serverSideDatasource}
        onRowClicked={onRowClicked}
      />
    </>
  );
};

export default Overview;
