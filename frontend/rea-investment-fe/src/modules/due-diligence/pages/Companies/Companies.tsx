import React, { useRef, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import BaseTable from '../../../../components/common/tables/BaseTable/BaseTable';
import { ColDef, GridApi, RowClickedEvent } from 'ag-grid-community';
import { ApiClient } from '../../../../api';
import SearchAndActions from '../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import RestoreIcon from '@mui/icons-material/Restore';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import { useAccess } from '../../../../hooks/access/access';
import ArchiveFilter, { ArchiveFilterValue } from '../../../../components/common/ArchiveFilter/ArchiveFilter';

const Companies = () => {
  const navigate = useNavigate();
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [searchTerm, setSearchTerm] = React.useState<string>('');
  const { isSystemUser } = useAccess();
  const [archiveFilter, setArchiveFilter] = useState<ArchiveFilterValue>('active');
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const restoreMutation = useMutation({
    mutationFn: (companyId: number) => ApiClient.assetManagement.restoreCompany(companyId),
    onSuccess: data => {
      setToast({ open: true, message: data.message, severity: 'success' });
      queryClient.invalidateQueries({ queryKey: ['company'] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      basicTableRef.current?.getApi()?.refreshServerSide({ purge: true });
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || 'Failed to restore company';
      setToast({ open: true, message: detail, severity: 'error' });
    }
  });

  const columns: ColDef[] = useMemo(() => {
    const baseCols: ColDef[] = [
      {
        headerName: 'Company Name',
        field: 'name',
        flex: 1,
        editable: false,
        filter: false,
        sortable: true
      },
      {
        headerName: 'Number of Projects',
        field: 'total_sites',
        flex: 1,
        editable: false,
        filter: false,
        sortable: true
      }
    ];

    if (isSystemUser && archiveFilter !== 'active') {
      baseCols.push({
        headerName: 'Actions',
        field: 'actions',
        flex: 0.5,
        sortable: false,
        cellRenderer: (params: any) => {
          if (!params.data?.is_archived) return null;
          return (
            <Button
              size="small"
              startIcon={<RestoreIcon />}
              onClick={e => {
                e.stopPropagation();
                restoreMutation.mutate(params.data.id);
              }}
            >
              Restore
            </Button>
          );
        }
      });
    }

    return baseCols;
  }, [isSystemUser, archiveFilter, restoreMutation]);

  const serverSideDatasource = useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        const requestParams: Record<string, any> = {
          skip,
          limit,
          ...(searchTerm && { search: searchTerm }),
          ...(orderBy && { order_by: orderBy }),
          ...(orderDirection && { order_direction: orderDirection })
        };

        if (archiveFilter === 'archived') {
          requestParams.is_archived = true;
        } else if (archiveFilter === 'all') {
          requestParams.include_all = true;
        }

        ApiClient.assetManagement
          .companies(requestParams)
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
    [searchTerm, archiveFilter]
  );

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const onRowClicked = useCallback(
    (e: RowClickedEvent) => {
      navigate(`/due-diligence/companies/${e.data.id}/sites`);
    },
    [navigate]
  );

  return (
    <>
      <Box sx={{ paddingTop: '24px' }}>
        <SearchAndActions
          showSearch={true}
          showExport={false}
          searchPlaceholder="Search by Name"
          onSearch={handleSearch}
          customActions={isSystemUser ? <ArchiveFilter value={archiveFilter} onChange={setArchiveFilter} /> : undefined}
        />
        <BaseTable
          ref={basicTableRef}
          rowModelType="serverSide"
          columnDefs={columns}
          serverSideDatasource={serverSideDatasource}
          onRowClicked={onRowClicked}
        />
      </Box>

      <Snackbar
        open={toast.open}
        autoHideDuration={4000}
        onClose={() => setToast(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={toast.severity} onClose={() => setToast(prev => ({ ...prev, open: false }))}>
          {toast.message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default Companies;
