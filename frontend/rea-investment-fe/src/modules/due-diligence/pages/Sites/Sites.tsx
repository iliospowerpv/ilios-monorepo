import React, { useCallback, useMemo, useRef, useState } from 'react';

import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import SearchAndActions from '../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import BaseTable from '../../../../components/common/tables/BaseTable/BaseTable';
import { ColDef, GridApi, RowClickedEvent } from 'ag-grid-community';
import { ApiClient } from '../../../../api';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import RestoreIcon from '@mui/icons-material/Restore';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import { useAccess } from '../../../../hooks/access/access';
import ArchiveFilter, { ArchiveFilterValue } from '../../../../components/common/ArchiveFilter/ArchiveFilter';

const SitesTab: React.FC = () => {
  const { companyId } = useParams();
  const existCompanyID = companyId ? Number.parseInt(companyId) : undefined;
  const navigate = useNavigate();
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const { isFullAccess, isUserParentCompany, isSystemUser } = useAccess(existCompanyID);
  const showAddBtn = !!companyId && isFullAccess && isUserParentCompany;
  const [archiveFilter, setArchiveFilter] = useState<ArchiveFilterValue>('active');
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const restoreMutation = useMutation({
    mutationFn: (siteId: number) => ApiClient.assetManagement.restoreSite(siteId),
    onSuccess: data => {
      setToast({ open: true, message: data.message, severity: 'success' });
      queryClient.invalidateQueries({ queryKey: ['site'] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      basicTableRef.current?.getApi()?.refreshServerSide({ purge: true });
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail || 'Failed to restore project';
      setToast({ open: true, message: detail, severity: 'error' });
    }
  });

  const columns: ColDef[] = useMemo(() => {
    const baseCols: ColDef[] = [
      {
        headerName: 'Project Name',
        field: 'name',
        flex: 1
      },
      {
        headerName: 'Company Name',
        field: 'company.name',
        flex: 1,
        sortable: false
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

  const serverSideDatasource = useMemo(() => {
    return {
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
          ...(companyId && { company_id: companyId }),
          ...(orderBy && { order_by: orderBy }),
          ...(orderDirection && { order_direction: orderDirection })
        };

        if (archiveFilter === 'archived') {
          requestParams.is_archived = true;
        } else if (archiveFilter === 'all') {
          requestParams.include_all = true;
        }

        ApiClient.assetManagement
          .sites(requestParams)
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
  }, [searchTerm, companyId, archiveFilter]);

  const onRowClicked = useCallback(
    (e: RowClickedEvent) => {
      navigate(`/due-diligence/companies/${e.data.company.id}/sites/${e.data.id}`);
    },
    [navigate]
  );

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleAddClick = () => {
    navigate(`/settings/company/${companyId}/site/add`);
  };

  return (
    <>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        Projects
      </Typography>
      <SearchAndActions
        showSearch={true}
        searchPlaceholder="Search by Project Name"
        onSearch={handleSearch}
        btnAddLabel="Add a New Project"
        onAdd={handleAddClick}
        showAdd={showAddBtn}
        customActions={isSystemUser ? <ArchiveFilter value={archiveFilter} onChange={setArchiveFilter} /> : undefined}
      />
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        columnDefs={columns}
        serverSideDatasource={serverSideDatasource}
        onRowClicked={onRowClicked}
      />

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

export default SitesTab;
