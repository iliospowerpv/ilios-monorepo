import React, { useRef, useState, useMemo } from 'react';
import BaseTable from '../../../../../components/common/tables/BaseTable/BaseTable';
import { ColDef, GridApi } from 'ag-grid-community';
import { ApiClient } from '../../../../../api';
import formatFloatValue from '../../../../../utils/formatters/formatFloatValue';
import PowerProductionIndicator from '../../../../../components/common/PowerProductionIndicator/PowerProductionIndicator';

const columns = [
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

interface CompaniesProps {
  onCompanySelected?: (args: { id: number; name: string } | null) => void;
  onCompaniesDataRendered?: () => void;
}

interface CompaniesRef {
  refetchData: () => void;
}

const Companies = React.forwardRef<CompaniesRef, CompaniesProps>(
  ({ onCompanySelected, onCompaniesDataRendered }, ref) => {
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

          ApiClient.investorDashboard
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

    React.useImperativeHandle(
      ref,
      () => ({
        refetchData: () => basicTableRef.current?.getApi()?.refreshServerSide()
      }),
      []
    );

    const onSelectionChange = React.useCallback(() => {
      const [selectedCompany] = basicTableRef.current?.getApi()?.getSelectedRows() ?? [];

      if (!selectedCompany) {
        onCompanySelected && onCompanySelected(null);
        const rowIndex = basicTableRef.current?.getApi()?.getFirstDisplayedRowIndex();
        rowIndex !== undefined && basicTableRef.current?.getApi()?.getDisplayedRowAtIndex(rowIndex)?.setSelected(true);
        return;
      }

      const derivedId = selectedCompany['id'];
      const companyId = typeof derivedId === 'number' ? derivedId : null;
      const derivedName = selectedCompany['name'];
      const companyName = typeof derivedName === 'string' ? derivedName : null;
      onCompanySelected && onCompanySelected(companyId && companyName ? { id: companyId, name: companyName } : null);
    }, [onCompanySelected]);

    return (
      <BaseTable
        selectableRows
        onSelectionChanged={onSelectionChange}
        ref={basicTableRef}
        rowModelType="serverSide"
        columnDefs={colDefs}
        serverSideDatasource={serverSideDatasource}
        onInitialDataRendered={onCompaniesDataRendered}
      />
    );
  }
);

Companies.displayName = 'Companies';

export type { CompaniesRef };

export default Companies;
