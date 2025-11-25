import React, { useCallback } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { ApiClient } from '../../../../api';
import { GridApi, ColDef, RowClickedEvent } from 'ag-grid-community';
import SearchAndActions from '../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import BaseTable from '../../../../components/common/tables/BaseTable/BaseTable';
import AlertsIndicator from '../../components/AlertsIndicator';
import PowerProductionIndicator from '../../../../components/common/PowerProductionIndicator/PowerProductionIndicator';
import { useNavigate } from 'react-router-dom';
import { formatFloatValue } from '../../../../utils/formatters/formatFloatValue';

const columns: ColDef[] = [
  {
    headerName: undefined,
    width: 60,
    editable: false,
    filter: false,
    sortable: false,
    cellStyle: { paddingLeft: 10, paddingRight: 10 },
    cellRenderer: (params: any) => {
      const { data } = params;
      const count = data?.alerts_overview?.total;

      if (typeof count !== 'number' || count < 1) return null;

      const severity = ['Critical', 'Warning', 'Informational'].includes(data?.alerts_overview?.severity)
        ? data?.alerts_overview?.severity
        : 'Warning';

      return <AlertsIndicator alertsCount={count} severity={severity} />;
    }
  },
  {
    headerName: 'Company Name',
    field: 'name',
    flex: 1
  },
  {
    headerName: 'Number of Sites',
    field: 'total_sites',
    flex: 1
  },
  {
    headerName: 'System Size (kW)',
    field: 'total_capacity',
    flex: 1,
    cellRenderer: (data: any) => {
      return typeof data?.value === 'number' ? formatFloatValue(data.value) : '';
    }
  },
  {
    headerName: 'Actual Production (kW)',
    field: 'actual_production',
    flex: 1,
    sortable: false,
    cellRenderer: (params: any) => {
      const { data } = params;
      const actualProduction = data?.total_actual_kw;
      const actualVsExpected = data?.actual_vs_expected;

      if (typeof actualProduction !== 'number' || typeof actualVsExpected !== 'number') return null;

      return (
        <PowerProductionIndicator
          actualPerformance={actualProduction}
          actualVsExpected={actualVsExpected}
          formatter={formatFloatValue}
        />
      );
    }
  }
];

export const AllCompaniesPage: React.FC = () => {
  const navigate = useNavigate();
  const basicTableRef = React.useRef<{ getApi: () => GridApi | undefined }>(null);
  const [searchTerm, setSearchTerm] = React.useState<string>('');

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.operationsAndMaintenance
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
      navigate(`/operations-and-maintenance/companies/${e.data.id}`);
    },
    [navigate]
  );

  return (
    <Box>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        Companies
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
          columnDefs={columns}
          onRowClicked={onRowClicked}
          serverSideDatasource={serverSideDatasource}
        />
      </Box>
    </Box>
  );
};

export default AllCompaniesPage;
