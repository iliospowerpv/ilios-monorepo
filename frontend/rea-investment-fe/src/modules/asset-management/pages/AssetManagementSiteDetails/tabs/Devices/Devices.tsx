import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ColDef, GridApi, RowClickedEvent } from 'ag-grid-community';
import { cloneDeep } from 'lodash';
import dayjs from 'dayjs';
import CustomParseFormatPlugin from 'dayjs/plugin/customParseFormat';
import Chip from '@mui/material/Chip';
import CastConnectedIcon from '@mui/icons-material/CastConnected';

import { AssetManagementSiteDetailsTabProps } from '../types';
import { ApiClient } from '../../../../../../api';
import SearchAndActions from '../../../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import ColumnsModal from '../../../../../../components/common/tables/components/ColumnsModal/ColumnsModal';
import formatFloatValue from '../../../../../../utils/formatters/formatFloatValue';
import FullPageLoader from '../../../../../../components/common/FullPageLoader/FullPageLoader';
interface ColumnProp extends ColDef {
  isDefault: boolean;
  checked: boolean;
}

dayjs.extend(CustomParseFormatPlugin);

const deviceHealth: any = {
  green: (theme: { efficiencyColors: { good: any } }) => theme.efficiencyColors.good,
  red: '#B02E0C',
  yellow: '#E9D332'
};

const columns: ColumnProp[] = [
  {
    headerName: 'Asset ID',
    field: 'asset_id',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Connection Status',
    field: 'das_connection_status',
    flex: 1,
    cellRenderer: (params: any) => {
      const status: string = params.data.das_connection_status;

      const chipColorMapping: Record<string, string> = {
        ['Not Connected']: 'rgba(233, 211, 50, 0.5)',
        ['Connected']: '#8CD88A',
        default: 'rgba(0, 0, 0, 0.08)'
      };

      return (
        <Chip
          label={status}
          size="small"
          sx={theme => ({
            marginTop: '-2px',
            height: '22px',
            color: theme.palette.primary.main,
            background: chipColorMapping[status] || chipColorMapping['default']
          })}
        />
      );
    },
    editable: false,
    filter: false,
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Device Status',
    field: 'status',
    flex: 1,
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Device Name',
    field: 'name',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Device Health',
    field: 'health',
    flex: 1,
    cellRenderer: (params: any) => (
      <Chip
        icon={<CastConnectedIcon />}
        color="success"
        size="small"
        sx={theme => ({
          color: theme.palette.primary.main,
          background: deviceHealth[params.data.health],
          '.MuiChip-icon': {
            marginLeft: '3px',
            marginRight: '-13px'
          }
        })}
      />
    ),
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Device Category',
    field: 'category',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Manufacturer',
    field: 'manufacturer',
    flex: 1,
    sortable: false,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Capacity',
    field: 'capacity',
    flex: 1,
    sortable: false,
    checked: true,
    isDefault: true,
    cellRenderer: (data: any) => {
      return typeof data?.value === 'number' ? formatFloatValue(data.value) : '';
    }
  },
  {
    headerName: 'Device Type',
    field: 'type',
    flex: 1,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Model',
    field: 'model',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Serial # / Asset Tag',
    field: 'serial_number',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Warranty Effective Date',
    field: 'warranty_effective_date',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false,
    valueFormatter: ({ value }) => {
      if (typeof value === 'string' && dayjs(value, 'YYYY-MM-DD', true).isValid()) {
        return dayjs(value, 'YYYY-MM-DD', true).format('MM/DD/YYYY');
      }

      return value;
    }
  },
  {
    headerName: 'Warranty Term',
    field: 'warranty_term',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Gateway ID',
    field: 'gateway_id',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Function ID',
    field: 'function_id',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Driver',
    field: 'driver',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Link to Warranty Document',
    field: 'link_to_warranty_document',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Last Service Date (Issue)',
    field: 'issue',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false,
    valueFormatter: ({ value }) => {
      if (typeof value === 'string' && dayjs(value, 'YYYY-MM-DD', true).isValid()) {
        return dayjs(value, 'YYYY-MM-DD', true).format('MM/DD/YYYY');
      }

      return value;
    }
  },
  {
    headerName: 'Last Service Date (Maintenance)',
    field: 'maintenance',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false,
    valueFormatter: ({ value }) => {
      if (typeof value === 'string' && dayjs(value, 'YYYY-MM-DD', true).isValid()) {
        return dayjs(value, 'YYYY-MM-DD', true).format('MM/DD/YYYY');
      }

      return value;
    }
  },
  {
    headerName: 'Next Scheduled Service Date',
    field: 'next_scheduled_service_date',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false,
    valueFormatter: ({ value }) => {
      if (typeof value === 'string' && dayjs(value, 'YYYY-MM-DD', true).isValid()) {
        return dayjs(value, 'YYYY-MM-DD', true).format('MM/DD/YYYY');
      }

      return value;
    }
  },
  {
    headerName: 'Install Date',
    field: 'install_date',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false,
    valueFormatter: ({ value }) => {
      if (typeof value === 'string' && dayjs(value, 'YYYY-MM-DD', true).isValid()) {
        return dayjs(value, 'YYYY-MM-DD', true).format('MM/DD/YYYY');
      }

      return value;
    }
  },
  {
    headerName: 'Decommissioned Date',
    field: 'decommissioned_date',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false,
    valueFormatter: ({ value }) => {
      if (typeof value === 'string' && dayjs(value, 'YYYY-MM-DD', true).isValid()) {
        return dayjs(value, 'YYYY-MM-DD', true).format('MM/DD/YYYY');
      }

      return value;
    }
  },
  {
    headerName: 'Last Updated',
    field: 'last_updated_date',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false,
    valueFormatter: ({ value }) => {
      if (typeof value === 'string' && dayjs(value, 'YYYY-MM-DD', true).isValid()) {
        return dayjs(value, 'YYYY-MM-DD', true).format('MM/DD/YYYY');
      }

      return value;
    }
  },
  {
    headerName: 'Uptime Availability',
    field: 'uptime_availability',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false
  },
  {
    headerName: 'Lifetime',
    field: 'lifetime',
    flex: 1,
    sortable: false,
    checked: false,
    isDefault: false
  }
];

const DevicesTab: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const navigate = useNavigate();
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [colModals, setColModals] = useState<ColumnProp[]>(columns);
  const [colDefs, setColDefs] = useState<ColDef[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [columnsOpen, setColumnsOpen] = React.useState(false);
  const [loading, setLoading] = useState<boolean>(false);

  const serverSideDatasource = useMemo(() => {
    return {
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.assetManagement
          .devices(siteDetails.id, {
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

  const handleColumnsOpen = () => {
    setColumnsOpen(true);
  };

  const handleColumnsClose = () => {
    setColumnsOpen(false);
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const handleAddClick = () => {
    navigate(`/asset-management/companies/${siteDetails.company.id}/sites/${siteDetails.id}/devices/add`);
  };

  const handleColumnsApply = (columns: any) => {
    const columnDefs = filterAndCleanColumns(columns);
    setColModals(columns);
    setColDefs(columnDefs);
    setColumnsOpen(false);
  };

  const onRowClicked = useCallback(
    (e: RowClickedEvent) => {
      navigate(`/asset-management/companies/${siteDetails.company.id}/sites/${siteDetails.id}/devices/${e.data.id}`);
      setTimeout(() => setLoading(true), 500);
    },
    [navigate, siteDetails]
  );

  useEffect(() => {
    return () => {
      setLoading(false);
    };
  }, []);

  return (
    <>
      <SearchAndActions
        showSearch={true}
        showFilter={false}
        showColumns={true}
        reversOrder={true}
        showAdd={true}
        btnAddLabel="Add a New Device"
        searchPlaceholder="Search Device"
        onSearch={handleSearch}
        onAdd={handleAddClick}
        onColumns={handleColumnsOpen}
      />
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        columnDefs={colDefs}
        serverSideDatasource={serverSideDatasource}
        onRowClicked={onRowClicked}
      />
      <ColumnsModal open={columnsOpen} columns={colModals} onClose={handleColumnsClose} onApply={handleColumnsApply} />
      <FullPageLoader open={loading} />
    </>
  );
};

export default DevicesTab;
