import React, { useCallback, useMemo, useRef, useState } from 'react';

import { useNavigate, useParams } from 'react-router-dom';
import SearchAndActions from '../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import BaseTable from '../../../../components/common/tables/BaseTable/BaseTable';
import { ColDef, GridApi, RowClickedEvent } from 'ag-grid-community';
import { ApiClient } from '../../../../api';
import Typography from '@mui/material/Typography';
import { useAccess } from '../../../../hooks/access/access';

const columns = [
  {
    headerName: 'Site Name',
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

const SitesTab: React.FC = () => {
  const { companyId } = useParams();
  const existCompanyID = companyId ? Number.parseInt(companyId) : undefined;
  const navigate = useNavigate();
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [colDefs] = useState<ColDef[]>(columns);
  const { isFullAccess, isUserParentCompany } = useAccess(existCompanyID);
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
  }, [searchTerm, companyId]);

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
        Sites
      </Typography>
      <SearchAndActions
        showSearch={true}
        searchPlaceholder="Search by Site Name"
        onSearch={handleSearch}
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
    </>
  );
};

export default SitesTab;
