import React, { useRef, useState } from 'react';
import { ApiClient, CompanyDetails } from '../../../../../../api';
import { GridApi } from 'ag-grid-community';
import { useNavigate } from 'react-router-dom';
import SearchAndActions from '../../../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import ActionButtons from '../../../../../../components/common/tables/components/ActionButtons/ActionButtons';

export interface CompanyDetailsTabProps {
  companyDetails: CompanyDetails;
}

const getColumns = () => [
  {
    headerName: 'Site Name',
    field: 'name',
    flex: 1
  },
  {
    headerName: 'Address',
    field: 'address',
    flex: 1
  },
  {
    field: 'actions',
    editable: false,
    filter: false,
    sortable: false,
    cellRenderer: (params: any) => (
      <ActionButtons
        isRegistered={true}
        isEdit={true}
        data={params.data}
        onEdit={`/settings/my-company/site/${params.data.id}/edit`}
      />
    )
  }
];

export const SitesTab: React.FC<CompanyDetailsTabProps> = () => {
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const navigate = useNavigate();
  const columns = getColumns();

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.myCompany
          .getMyCompanySites({
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

  const handleAddClick = () => {
    navigate(`/settings/my-company/sites/add`);
  };

  return (
    <>
      <SearchAndActions
        showSearch={true}
        showExport={false}
        showAdd={true}
        searchPlaceholder="Search by Name"
        btnAddLabel="Add a New Site"
        onSearch={handleSearch}
        onAdd={handleAddClick}
      />
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        disableRowHover={true}
        columnDefs={columns}
        serverSideDatasource={serverSideDatasource}
      />
    </>
  );
};

export default SitesTab;
