import React, { useMemo, useRef, forwardRef, useImperativeHandle, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { SelectionChangedEvent, RowModelType, RowStyle, GridOptions, RowClickedEvent, ColDef } from 'ag-grid-community';
import { LicenseManager } from 'ag-grid-enterprise';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import '../../../../utils/styles/ag-theme-rea.css';
import NoDataOverlay from '../components/NoDataOverlay/NoDataOverlay';

if (typeof process.env.REACT_APP_AG_GRID_LICENSE_KEY === 'string') {
  LicenseManager.setLicenseKey(process.env.REACT_APP_AG_GRID_LICENSE_KEY);
}

interface BaseTableProps {
  columnDefs: any[];
  rowData?: any[];
  searchable?: boolean;
  rowModelType?: RowModelType;
  serverSideDatasource?: any;
  tableRowHeight?: number;
  defaultColDefOverrides?: ColDef;
  allowMultilineHeader?: boolean;
  getRowStyle?: (params: any) => RowStyle | undefined;
  onSelectionChanged?: (event: SelectionChangedEvent) => void;
  onRowClicked?: (event: RowClickedEvent) => void;
}

const BaseTableNoPagination = forwardRef((props: BaseTableProps, ref) => {
  const agGridRef = useRef<AgGridReact>(null);
  const {
    columnDefs,
    rowData,
    rowModelType,
    getRowStyle,
    serverSideDatasource,
    onSelectionChanged,
    onRowClicked,
    tableRowHeight,
    defaultColDefOverrides,
    allowMultilineHeader
  } = props;

  useImperativeHandle(
    ref,
    () => ({
      getApi: () => agGridRef.current?.api
    }),
    []
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      resizable: false,
      filter: false,
      suppressHeaderMenuButton: true,
      suppressMovable: true,
      ...defaultColDefOverrides,
      ...(allowMultilineHeader && { wrapHeaderText: true, autoHeaderHeight: true })
    }),
    [defaultColDefOverrides, allowMultilineHeader]
  );

  const getRowId = useMemo(() => {
    return (params: any) => (params.data.id ? params.data.id : params.data.uuid);
  }, []);

  const onSortChanged = useCallback(() => {
    agGridRef.current?.api.paginationGoToPage(0);
  }, []);

  const gridOptions = useMemo<GridOptions>(
    () => ({
      ...(typeof tableRowHeight === 'number' && { rowHeight: tableRowHeight }),
      ...(onRowClicked && { onRowClicked })
    }),
    [onRowClicked, tableRowHeight]
  );

  return (
    <div className="ag-theme-quartz full-width-grid no-borders " data-testid="grid__base-table">
      <AgGridReact
        ref={agGridRef}
        domLayout="autoHeight"
        className="ag-fill-both"
        pagination={false}
        animateRows={true}
        suppressContextMenu={true}
        headerHeight={32}
        groupHeaderHeight={32}
        getRowId={getRowId}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        maxBlocksInCache={0}
        rowData={rowData}
        rowModelType={rowModelType}
        getRowStyle={getRowStyle}
        onSortChanged={onSortChanged}
        serverSideDatasource={serverSideDatasource}
        onSelectionChanged={onSelectionChanged}
        gridOptions={gridOptions}
        noRowsOverlayComponent={NoDataOverlay}
      />
    </div>
  );
});

BaseTableNoPagination.displayName = 'BaseTableNoPagination';

export default BaseTableNoPagination;
