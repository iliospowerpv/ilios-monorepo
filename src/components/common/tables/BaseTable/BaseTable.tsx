import React, { useMemo, useRef, forwardRef, useImperativeHandle, useCallback, useState, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import {
  SelectionChangedEvent,
  RowModelType,
  RowStyle,
  GridOptions,
  RowClickedEvent,
  ColDef,
  GridReadyEvent
} from 'ag-grid-community';
import { LicenseManager } from 'ag-grid-enterprise';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import '../../../../utils/styles/ag-theme-rea.css';
import NoDataOverlay from '../components/NoDataOverlay/NoDataOverlay';

if (typeof process.env.REACT_APP_AG_GRID_LICENSE_KEY === 'string') {
  LicenseManager.setLicenseKey(process.env.REACT_APP_AG_GRID_LICENSE_KEY);
}

interface BaseTableProps {
  rowIdKey?: string;
  columnDefs: any[];
  rowData?: any[];
  searchable?: boolean;
  disableRowHover?: boolean;
  rowModelType?: RowModelType;
  serverSideDatasource?: any;
  tableRowHeight?: number;
  defaultColDefOverrides?: ColDef;
  allowMultilineHeader?: boolean;
  selectableRows?: boolean;
  getRowStyle?: (params: any) => RowStyle | undefined;
  onSelectionChanged?: (event: SelectionChangedEvent) => void;
  onRowClicked?: (event: RowClickedEvent) => void;
  onInitialDataRendered?: () => void;
}

const BaseTable = forwardRef((props: BaseTableProps, ref) => {
  const agGridRef = useRef<AgGridReact>(null);
  const {
    rowIdKey,
    columnDefs,
    rowData,
    rowModelType,
    getRowStyle,
    serverSideDatasource,
    disableRowHover,
    onSelectionChanged,
    onRowClicked,
    tableRowHeight,
    defaultColDefOverrides,
    allowMultilineHeader,
    selectableRows,
    onInitialDataRendered
  } = props;
  const [pageSize, setPageSize] = useState<number>(10);
  const [isServerSide, setIsServerSide] = useState<boolean>(false);

  useImperativeHandle(
    ref,
    () => ({
      getApi: () => agGridRef.current?.api
    }),
    []
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      resizable: true,
      filter: false,
      suppressHeaderMenuButton: true,
      suppressMovable: true,
      ...defaultColDefOverrides,
      ...(allowMultilineHeader && { wrapHeaderText: true, autoHeaderHeight: true })
    }),
    [defaultColDefOverrides, allowMultilineHeader]
  );

  const paginationPageSizeSelector = useMemo(() => {
    return [10, 50, 100];
  }, []);

  const getRowId = useMemo(() => {
    return (params: any) => params.data[rowIdKey || 'id'];
  }, [rowIdKey]);

  const onSortChanged = useCallback(() => {
    agGridRef.current?.api.paginationGoToPage(0);
  }, []);

  const gridOptions = useMemo<GridOptions>(
    () => ({
      ...(typeof tableRowHeight === 'number' && { rowHeight: tableRowHeight }),
      ...(onRowClicked && { onRowClicked }),
      ...(selectableRows && { rowSelection: 'single' })
    }),
    [onRowClicked, tableRowHeight, selectableRows]
  );

  const onPaginationChanged = useCallback(() => {
    if (!agGridRef.current) return;

    const api = agGridRef.current?.api;
    const currentPageSize = api?.paginationGetPageSize() || 10;
    if (currentPageSize !== pageSize) {
      setPageSize(currentPageSize);
    }
  }, [pageSize]);

  const handleLoadingOverlay = useCallback(
    (params: any, rowData: any) => {
      if (isServerSide) {
        params.api.showLoadingOverlay();
      } else if (!rowData || rowData.length === 0) {
        params.api.showLoadingOverlay();
      } else {
        params.api.hideOverlay();
      }
    },
    [isServerSide, rowData]
  );

  const onGridReady = useCallback(
    (evt: GridReadyEvent) => {
      handleLoadingOverlay(evt, rowData);
    },
    [handleLoadingOverlay, rowData]
  );

  const onFirstDataRendered = React.useCallback(() => {
    if (selectableRows) {
      agGridRef.current?.api?.deselectAll();
    }
    onInitialDataRendered && onInitialDataRendered();
  }, [selectableRows, onInitialDataRendered]);

  const onStoreRefreshed = React.useCallback(() => {
    if (selectableRows) {
      setTimeout(() => agGridRef.current?.api?.deselectAll());
    }
  }, [selectableRows]);

  useEffect(() => {
    setIsServerSide(rowModelType === 'serverSide');
  }, [rowModelType]);

  return (
    <div
      className={`ag-theme-quartz full-width-grid no-borders ${disableRowHover ? 'no-hover' : ''}`}
      data-testid="grid__base-table"
    >
      <AgGridReact
        ref={agGridRef}
        domLayout="autoHeight"
        className="ag-fill-both"
        pagination={true}
        animateRows={true}
        suppressContextMenu={true}
        headerHeight={32}
        groupHeaderHeight={32}
        getRowId={getRowId}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        paginationPageSize={pageSize}
        cacheBlockSize={pageSize}
        maxBlocksInCache={0}
        rowData={!isServerSide ? rowData : null}
        rowModelType={rowModelType}
        getRowStyle={getRowStyle}
        onSortChanged={onSortChanged}
        onPaginationChanged={onPaginationChanged}
        paginationPageSizeSelector={paginationPageSizeSelector}
        serverSideDatasource={isServerSide ? serverSideDatasource : null}
        onSelectionChanged={onSelectionChanged}
        gridOptions={gridOptions}
        noRowsOverlayComponent={NoDataOverlay}
        onGridReady={onGridReady}
        onFirstDataRendered={onFirstDataRendered}
        onStoreRefreshed={onStoreRefreshed}
      />
    </div>
  );
});

BaseTable.displayName = 'BaseTable';

export default BaseTable;
