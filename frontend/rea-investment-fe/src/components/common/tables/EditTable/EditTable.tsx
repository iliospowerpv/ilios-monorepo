import React, { useCallback, useMemo, useState, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { LicenseManager } from 'ag-grid-enterprise';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import '../../../../utils/styles/ag-theme-rea.css';

import Box from '@mui/material/Box';
import { Button, Typography } from '@mui/material';

import CheckboxRenderer from '../components/CheckboxRenderer/CheckboxRenderer';
import { HeaderActionsContainer, FooterActionsContainer } from './EditTable.style';

if (typeof process.env.REACT_APP_AG_GRID_LICENSE_KEY === 'string') {
  LicenseManager.setLicenseKey(process.env.REACT_APP_AG_GRID_LICENSE_KEY);
}

interface EditTableProps {
  rowData: any[];
  customActions?: React.ReactElement;
}

const EditTable: React.FC<EditTableProps> = ({ rowData, customActions }) => {
  const gridRef = useRef<AgGridReact>(null);
  const [selectedRowId, setSelectedRowId] = useState<number | null>(null);
  const [isRowEditMode, setIsRowEditMode] = useState<boolean>(false);
  const [rolesRowData, setRolesRowData] = useState<any[]>(rowData);

  const defaultColDef = useMemo(
    () => ({
      sortable: false,
      resizable: false,
      flex: 1,
      suppressMenu: true,
      suppressMovable: true
    }),
    []
  );

  const additionalColumn = {
    field: 'name',
    headerName: 'Name',
    flex: 1,
    pinned: true,
    cellRenderer: (params: any) => (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <Typography variant="body2" gutterBottom>
          {params.data.name}
        </Typography>
        <Typography variant="caption" gutterBottom sx={{ color: '#4F4F4F' }}>
          {params.data.company_type}
        </Typography>
      </Box>
    )
  };

  const excludedPermissions = ['Role-based Homepage/Tab', 'Investor Dashboard'];

  const dynamicColumns = Object.keys(rowData[0].permissions)
    .filter(key => !excludedPermissions.includes(key))
    .map(key => ({
      headerName: key,
      children: Object.keys(rowData[0].permissions[key]).map(y => ({
        field: y,
        headerName: y.charAt(0).toUpperCase() + y.slice(1),
        cellRenderer: (params: any) => (
          <CheckboxRenderer
            isRowSelected={params.data.id === selectedRowId}
            isRowEditMode={isRowEditMode}
            value={params?.data?.permissions[key][y]}
            onChange={checked => handleCheckboxChange(params.data.id, `${key}.${y}`, checked)}
          />
        )
      }))
    }));

  const columnDefs = useMemo(() => [additionalColumn, ...dynamicColumns], [selectedRowId, isRowEditMode]);

  const onSelectionChanged = useCallback(() => {
    const selectedNodes = gridRef.current?.api.getSelectedNodes();
    const selectedId = selectedNodes?.map(node => node.data.id)[0] || null;

    if (isRowEditMode && selectedId !== selectedRowId) {
      gridRef.current?.api.deselectAll();
    } else {
      setSelectedRowId(selectedId);
    }
  }, [isRowEditMode, selectedRowId]);

  const handleCheckboxChange = useCallback(
    (rowId: number, field: string, checked: boolean) => {
      if (rowId !== selectedRowId) return;
      setRolesRowData(prevRowData => prevRowData.map(row => (row.id === rowId ? { ...row, [field]: checked } : row)));
    },
    [selectedRowId]
  );

  const saveChanges = () => {
    if (!selectedRowId) return;

    setIsRowEditMode(false);
    setSelectedRowId(null);
  };

  // const toggleEditMode = useCallback(() => {
  //   if (selectedRowId) {
  //     setIsRowEditMode(prev => !prev);
  //   }
  // }, [selectedRowId]);

  const cancelEdit = () => {
    setIsRowEditMode(false);
    setSelectedRowId(null);
  };

  const getRowId = useMemo(() => {
    return (params: any) => params.data.id;
  }, []);

  return (
    <>
      <HeaderActionsContainer>
        {customActions}
        {/*<Button variant="outlined" disabled={!selectedRowId} onClick={toggleEditMode}>*/}
        {/*  Edit Permissions*/}
        {/*</Button>*/}
      </HeaderActionsContainer>
      <div className="ag-theme-quartz full-width-grid">
        <AgGridReact
          ref={gridRef}
          domLayout="autoHeight"
          className="ag-fill-both"
          rowSelection="single"
          headerHeight={32}
          groupHeaderHeight={32}
          rowHeight={74}
          animateRows={true}
          getRowId={getRowId}
          onSelectionChanged={onSelectionChanged}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          rowData={rolesRowData}
        />
      </div>
      {isRowEditMode && selectedRowId && (
        <FooterActionsContainer>
          <Button variant="contained" color="primary" onClick={saveChanges}>
            Save
          </Button>
          <Button variant="outlined" color="primary" onClick={cancelEdit}>
            Cancel
          </Button>
        </FooterActionsContainer>
      )}
    </>
  );
};

export default EditTable;
