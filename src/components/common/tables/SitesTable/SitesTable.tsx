import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import BaseTable from '../BaseTable/BaseTable';
import SearchAndActions from '../components/SearchAndActions/SearchAndActions';
import { ColDef, GridApi, RowClickedEvent } from 'ag-grid-community';
import { ApiClient } from '../../../../api';
import { cloneDeep } from 'lodash';
import FiltersModal from '../components/FiltersModal/FiltersModal';
import ColumnsModal from '../components/ColumnsModal/ColumnsModal';
import { useAccess } from '../../../../hooks/access/access';

interface ColumnProp extends ColDef {
  isDefault: boolean;
  checked: boolean;
}

interface SitesTableProps {
  columns: ColumnProp[];
  companyId?: number;
}

const SitesTable: React.FC<SitesTableProps> = ({ columns, companyId }) => {
  const navigate = useNavigate();
  const { isFullAccess, isUserParentCompany } = useAccess(companyId);
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [colModals, setColModals] = useState<ColumnProp[]>(columns);
  const [colDefs, setColDefs] = useState<ColDef[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [filterOpen, setFilterOpen] = React.useState(false);
  const [columnsOpen, setColumnsOpen] = React.useState(false);
  const showAddBtn = !!companyId && isFullAccess && isUserParentCompany;

  const serverSideDatasource = useMemo(() => {
    return {
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.assetManagement
          .sites({
            skip,
            limit,
            ...(searchTerm && { search: searchTerm }),
            ...(companyId && { company_id: companyId }),
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
    };
  }, [searchTerm]);

  const filterAndCleanColumns = (columnsArray: any) => {
    const columns = cloneDeep(columnsArray);
    const filteredColumns = columns.filter((column: any) => column.checked !== false);

    return filteredColumns.map((column: any) => {
      delete column.checked;
      delete column.isDefault;

      return column;
    });
  };

  useEffect(() => {
    const columnDefs = filterAndCleanColumns(columns);
    setColDefs(columnDefs);
  }, []);

  const handleFilterOpen = () => {
    setFilterOpen(true);
  };

  const handleFilterClose = () => {
    setFilterOpen(false);
  };

  const handleColumnsOpen = () => {
    setColumnsOpen(true);
  };

  const handleColumnsClose = () => {
    setColumnsOpen(false);
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleColumnsApply = (columns: any) => {
    const columnDefs = filterAndCleanColumns(columns);
    setColModals(columns);
    setColDefs(columnDefs);
    setColumnsOpen(false);
  };

  const onRowClicked = useCallback(
    (e: RowClickedEvent) => {
      navigate(`/asset-management/companies/${e.data.company.id}/sites/${e.data.id}`);
    },
    [navigate]
  );

  const handleAddClick = () => {
    navigate(`/settings/company/${companyId}/site/add`);
  };

  return (
    <>
      <SearchAndActions
        showSearch={true}
        showFilter={false}
        showColumns={true}
        reversOrder={true}
        searchPlaceholder="Search by Site Name"
        onSearch={handleSearch}
        onFilter={handleFilterOpen}
        onColumns={handleColumnsOpen}
        btnAddLabel="Add a New Site"
        onAdd={handleAddClick}
        showAdd={showAddBtn}
      />
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        columnDefs={colDefs}
        serverSideDatasource={serverSideDatasource}
        onRowClicked={onRowClicked}
      />
      <FiltersModal open={filterOpen} handleClose={handleFilterClose} />
      <ColumnsModal open={columnsOpen} columns={colModals} onClose={handleColumnsClose} onApply={handleColumnsApply} />
    </>
  );
};

export default SitesTable;
