import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@mui/material';
import FileUploadIcon from '@mui/icons-material/FileUpload';
import BaseTable from '../BaseTable/BaseTable';
import SearchAndActions from '../components/SearchAndActions/SearchAndActions';
import { ColDef, GridApi, ICellRendererParams, RowClickedEvent } from 'ag-grid-community';
import { ApiClient } from '../../../../api';
import { cloneDeep } from 'lodash';
import FiltersModal from '../components/FiltersModal/FiltersModal';
import ColumnsModal from '../components/ColumnsModal/ColumnsModal';
import { useAccess } from '../../../../hooks/access/access';
import ProjectImportWizard from '../../ProjectImport/ProjectImportWizard';
import InventoryReconciliationChip from '../../InventoryReconciliationChip/InventoryReconciliationChip';
import type { InventoryReconciliationSummary } from '../../../../types/telemetryV2';

interface ReconciliationGridContext {
  reconMap: Map<number, InventoryReconciliationSummary>;
  reconLoading: boolean;
  reconError: boolean;
}

const RECONCILIATION_COL_ID = 'inventory_reconciliation';

interface ColumnProp extends ColDef {
  isDefault: boolean;
  checked: boolean;
}

interface SitesTableProps {
  columns: ColumnProp[];
  companyId?: number;
  companyName?: string;
}

const SitesTable: React.FC<SitesTableProps> = ({ columns, companyId, companyName }) => {
  const navigate = useNavigate();
  const { isFullAccess, isUserParentCompany } = useAccess(companyId);
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [colModals, setColModals] = useState<ColumnProp[]>(columns);
  const [colDefs, setColDefs] = useState<ColDef[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [filterOpen, setFilterOpen] = React.useState(false);
  const [columnsOpen, setColumnsOpen] = React.useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [visibleSiteIds, setVisibleSiteIds] = useState<number[]>([]);
  const showAddBtn = !!companyId && isFullAccess && isUserParentCompany;

  // One reconciliation-summary request per rendered page: the visible page's site
  // ids are collected in getRows, then fetched in a single batch call. Cached so
  // re-visiting a page/sort/search with an overlapping id-set reuses the result.
  const sortedSiteIds = useMemo(() => [...visibleSiteIds].sort((a, b) => a - b), [visibleSiteIds]);
  const {
    data: reconData,
    isFetching: reconFetching,
    isError: reconIsError
  } = useQuery({
    queryKey: ['inventory-reconciliation-summaries', sortedSiteIds],
    queryFn: () => ApiClient.telemetryV2.getInventoryReconciliationSummaries(sortedSiteIds),
    enabled: sortedSiteIds.length > 0,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 1
  });

  const reconMap = useMemo(() => {
    const map = new Map<number, InventoryReconciliationSummary>();
    (reconData?.summaries ?? []).forEach(item => map.set(item.site_id, item.summary));
    return map;
  }, [reconData]);

  const gridContext = useMemo<ReconciliationGridContext>(
    () => ({
      reconMap,
      reconLoading: sortedSiteIds.length > 0 && reconFetching,
      reconError: reconIsError
    }),
    [reconMap, reconFetching, reconIsError, sortedSiteIds.length]
  );

  // The chip column reads from grid context (no per-cell network); refresh just
  // that column when the summaries resolve so the rest of the grid never re-renders.
  useEffect(() => {
    basicTableRef.current?.getApi()?.refreshCells({ force: true, columns: [RECONCILIATION_COL_ID] });
  }, [gridContext]);

  const refreshGrid = useCallback(() => {
    const api = basicTableRef.current?.getApi();
    if (api) {
      api.refreshServerSide({ purge: true });
    }
  }, []);

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

            const ids = data.items
              .map((item: { id?: number }) => item.id)
              .filter((id: number | undefined): id is number => typeof id === 'number');
            setVisibleSiteIds(prev =>
              prev.length === ids.length && prev.every((id, idx) => id === ids[idx]) ? prev : ids
            );

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

  const reconciliationColumn = useMemo<ColDef>(
    () => ({
      headerName: 'Reconciliation',
      colId: RECONCILIATION_COL_ID,
      field: RECONCILIATION_COL_ID,
      flex: 1,
      minWidth: 180,
      sortable: false,
      cellRenderer: (params: ICellRendererParams) => {
        const siteId = params.data?.id as number | undefined;
        const ctx = params.context as ReconciliationGridContext | undefined;
        if (typeof siteId !== 'number' || !ctx) {
          return null;
        }
        const summary = ctx.reconMap.get(siteId);
        // No fabricated "Matched": an absent summary while not loading => unavailable.
        return (
          <InventoryReconciliationChip
            summary={summary}
            loading={ctx.reconLoading && !summary}
            error={ctx.reconError && !summary}
            to={`/project-hub/projects/${siteId}/reconciliation`}
          />
        );
      }
    }),
    []
  );

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
    // Inject the read-only reconciliation chip column right after Project Name so
    // it is always present (it is intentionally not part of the toggleable set).
    const insertAt = columnDefs.length > 0 ? 1 : 0;
    columnDefs.splice(insertAt, 0, reconciliationColumn);
    setColDefs(columnDefs);
  }, [reconciliationColumn]);

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
    const insertAt = columnDefs.length > 0 ? 1 : 0;
    columnDefs.splice(insertAt, 0, reconciliationColumn);
    setColModals(columns);
    setColDefs(columnDefs);
    setColumnsOpen(false);
  };

  const onRowClicked = useCallback(
    (e: RowClickedEvent) => {
      navigate(`/project-hub/companies/${e.data.company.id}/sites/${e.data.id}`);
    },
    [navigate]
  );

  const handleAddClick = () => {
    navigate(`/onboarding?companyId=${companyId}`);
  };

  return (
    <>
      <SearchAndActions
        showSearch={true}
        showFilter={false}
        showColumns={true}
        reversOrder={true}
        searchPlaceholder="Search by Project Name"
        onSearch={handleSearch}
        onFilter={handleFilterOpen}
        onColumns={handleColumnsOpen}
        btnAddLabel="Add a New Project"
        onAdd={handleAddClick}
        showAdd={showAddBtn}
        customActions={
          showAddBtn ? (
            <Button
              variant="outlined"
              color="primary"
              startIcon={<FileUploadIcon />}
              onClick={() => setImportOpen(true)}
              size="small"
              sx={{ mr: 1 }}
            >
              Import Projects
            </Button>
          ) : undefined
        }
      />
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        columnDefs={colDefs}
        serverSideDatasource={serverSideDatasource}
        gridContext={gridContext}
        onRowClicked={onRowClicked}
      />
      <FiltersModal open={filterOpen} handleClose={handleFilterClose} />
      <ColumnsModal open={columnsOpen} columns={colModals} onClose={handleColumnsClose} onApply={handleColumnsApply} />
      {companyId && (
        <ProjectImportWizard
          open={importOpen}
          onClose={() => setImportOpen(false)}
          companyId={companyId}
          companyName={companyName || `Company #${companyId}`}
          onImportComplete={refreshGrid}
        />
      )}
    </>
  );
};

export default SitesTable;
