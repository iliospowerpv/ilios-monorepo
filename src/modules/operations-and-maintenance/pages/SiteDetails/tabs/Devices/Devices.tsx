import React, { useEffect, useState } from 'react';

import { GridApi, ColDef, RowClickedEvent } from 'ag-grid-community';
import { useNavigate } from 'react-router-dom';

import Chip from '@mui/material/Chip';

import { ApiClient } from '../../../../../../api';
import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import AlertsIndicator from '../../../../components/AlertsIndicator';
import { SiteDetailsTabProps } from '../types';
import FullPageLoader from '../../../../../../components/common/FullPageLoader/FullPageLoader';

const columns: ColDef[] = [
  {
    headerName: undefined,
    width: 60,
    editable: false,
    filter: false,
    sortable: false,
    cellStyle: { paddingLeft: 10, paddingRight: 10 },
    cellRenderer: (params: any) => {
      const { data } = params;
      const count = data?.alerts_overview?.total;

      if (typeof count !== 'number' || count < 1) return null;

      const severity = ['Critical', 'Warning', 'Informational'].includes(data?.alerts_overview?.severity)
        ? data?.alerts_overview?.severity
        : 'Warning';

      return <AlertsIndicator alertsCount={count} severity={severity} />;
    }
  },
  {
    headerName: 'Device ID',
    field: 'asset_id',
    flex: 1,
    editable: false,
    filter: false,
    sortable: false
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
    sortable: false
  },
  {
    headerName: 'Device Name',
    field: 'name',
    flex: 1,
    editable: false,
    filter: false,
    sortable: false
  },
  {
    headerName: 'Device Type',
    field: 'type',
    flex: 1,
    editable: false,
    filter: false,
    sortable: false
  },
  {
    headerName: 'Device Status',
    field: 'status',
    flex: 1,
    editable: false,
    filter: false,
    sortable: false
  },
  {
    headerName: 'Last Reported',
    field: 'last_reported',
    flex: 1,
    editable: false,
    filter: false,
    sortable: false
  },
  {
    headerName: 'Lifetime',
    field: 'lifetime',
    flex: 1,
    editable: false,
    filter: false,
    sortable: false
  },
  {
    headerName: 'Warranty Period',
    field: 'warranty_period',
    flex: 1,
    editable: false,
    filter: false,
    sortable: false
  }
];

export const DevicesTab: React.FC<SiteDetailsTabProps> = ({ siteDetails, companyDetails }) => {
  const { id: siteId } = siteDetails;
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(false);
  const basicTableRef = React.useRef<{ getApi: () => GridApi | undefined }>(null);

  const serverSideDatasource = React.useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;

        ApiClient.operationsAndMaintenance
          .devicesBySite(siteId, {
            skip,
            limit
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
    [siteId]
  );

  const onRowClicked = React.useCallback(
    (e: RowClickedEvent) => {
      navigate(`/asset-management/companies/${companyDetails.id}/sites/${siteDetails.id}/devices/${e?.data?.id}`);
      setTimeout(() => setLoading(true), 500);
    },
    [navigate, companyDetails, siteDetails]
  );

  useEffect(() => {
    return () => {
      setLoading(false);
    };
  }, []);

  return (
    <>
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        columnDefs={columns}
        serverSideDatasource={serverSideDatasource}
        onRowClicked={onRowClicked}
      />
      <FullPageLoader open={loading} />
    </>
  );
};

export default DevicesTab;
