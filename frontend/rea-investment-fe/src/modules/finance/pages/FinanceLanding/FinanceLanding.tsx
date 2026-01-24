import React, { useRef, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { ColDef, GridApi, RowClickedEvent } from 'ag-grid-community';
import BaseTable from '../../../../components/common/tables/BaseTable/BaseTable';
import SearchAndActions from '../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import { ApiClient } from '../../../../api';

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
  }
];

export const FinanceLanding: React.FC = () => {
  const navigate = useNavigate();
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [colDefs] = useState<ColDef[]>(columns);
  const [searchTerm, setSearchTerm] = useState<string>('');

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

  const onRowClicked = useCallback(
    (e: RowClickedEvent) => {
      navigate(`/finance/companies/${e.data.id}`);
    },
    [navigate]
  );

  return (
    <Box p={3}>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        Finance - Companies
      </Typography>
      <Box sx={{ paddingTop: '24px' }}>
        <SearchAndActions
          showSearch={true}
          showExport={false}
          searchPlaceholder="Search by Name"
          onSearch={handleSearch}
        />
        <BaseTable
          ref={basicTableRef}
          rowModelType="serverSide"
          columnDefs={colDefs}
          serverSideDatasource={serverSideDatasource}
          onRowClicked={onRowClicked}
        />
      </Box>
    </Box>
  );
};

export default FinanceLanding;
