import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ColDef, GridApi, RowClickedEvent } from 'ag-grid-community';
import Box from '@mui/material/Box';
import BaseTable from '../../../../../../components/common/tables/BaseTable/BaseTable';
import { ApiClient } from '../../../../../../api';
import { CompanyDetailsTabProps } from '../types';
import AlertsIndicator from '../../../../components/AlertsIndicator';
import EfficiencyRateBar from '../../../../../../components/common/EfficiencyRateBar/EfficiencyRateBar';
import { formatFloatValue } from '../../../../../../utils/formatters/formatFloatValue';
import { Button } from '@mui/material';
import { useAccess } from '../../../../../../hooks/access/access';
import Chip from '@mui/material/Chip';
import { BootstrapTooltip } from '../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import WeatherIndicator from '../../../../../../components/common/WeatherIndicator/WeatherIndicator';

const efficiencyBarCellRenderer = (params: any) => {
  const value = typeof params?.value === 'number' ? params?.value : 0;
  return <EfficiencyRateBar percentage={value} />;
};

const statusCellRenderer = (params: any) => {
  const statusColor =
    params?.value === 'Connected'
      ? (theme: { efficiencyColors: { good: any } }) => theme.efficiencyColors.good
      : '#E9D33280';

  return (
    <Chip
      label={params?.value}
      color="success"
      size="small"
      sx={theme => ({
        color: theme.palette.primary.main,
        background: statusColor
      })}
    />
  );
};

const weatherIndicatorCellRenderer = (params: any) => {
  const value = params?.value;

  if (!value) return null;

  if (typeof value === 'string') {
    return (
      <BootstrapTooltip placement="right" title={value}>
        <WeatherIndicator imageSrc={null} />
      </BootstrapTooltip>
    );
  }

  return (
    <BootstrapTooltip placement="right" title={value?.weather_description}>
      <WeatherIndicator imageSrc={value?.weather_icon_url} />
    </BootstrapTooltip>
  );
};

const alertsIndicatorCellRenderer = (params: any) => {
  const { data } = params;
  const count = data?.alerts_overview?.total;

  if (typeof count !== 'number' || count < 1) return null;

  const severity = ['Critical', 'Warning', 'Informational'].includes(data?.alerts_overview?.severity)
    ? data?.alerts_overview?.severity
    : 'Warning';

  return <AlertsIndicator alertsCount={count} severity={severity} />;
};

const defaultColDefOverrides: ColDef = {
  cellStyle: () => ({
    display: 'flex',
    alignItems: 'center'
  }),
  cellRenderer: (params: any) => (
    <Box
      component="span"
      sx={{
        width: '100%',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }}
    >
      {typeof params?.data === 'object' ? params.data[params?.colDef?.field] : null}
    </Box>
  )
};

const columns: ColDef[] = [
  {
    headerName: undefined,
    width: 60,
    pinned: 'left',
    editable: false,
    filter: false,
    sortable: false,
    cellStyle: { paddingLeft: 10, paddingRight: 10 },
    cellRenderer: alertsIndicatorCellRenderer
  },
  {
    headerName: 'Site Name',
    field: 'name',
    flex: 1,
    sortable: false,
    pinned: 'left'
  },
  {
    headerName: 'Status',
    field: 'das_connection_status',
    sortable: false,
    width: 140,
    cellRenderer: statusCellRenderer
  },
  {
    headerName: 'Weather',
    field: 'weather',
    sortable: false,
    width: 90,
    cellRenderer: weatherIndicatorCellRenderer
  },
  {
    headerName: 'Actual (kW)',
    field: 'actual_kw',
    sortable: false,
    width: 150,
    cellRenderer: (data: any) => {
      return typeof data?.value === 'number' ? formatFloatValue(data.value) : '';
    }
  },
  {
    headerName: 'Expected (kW)',
    field: 'expected_kw',
    sortable: false,
    width: 150,
    cellRenderer: (data: any) => {
      return typeof data?.value === 'number' ? formatFloatValue(data.value) : '';
    }
  },
  {
    headerName: 'Actual vs Expected (kW)',
    field: 'actual_vs_expected',
    sortable: false,
    width: 240,
    cellRenderer: efficiencyBarCellRenderer
  },
  {
    headerName: 'Actual vs Expected (kWh) – Today',
    field: 'cumulative_vs_expected',
    sortable: false,
    width: 240,
    cellRenderer: efficiencyBarCellRenderer
  },
  {
    headerName: 'Actual vs Expected (kWh) – Last 7 Days',
    field: 'cumulative_7_days_vs_expected',
    sortable: false,
    width: 237,
    cellRenderer: efficiencyBarCellRenderer
  },
  {
    headerName: 'Actual vs Expected (kWh) – Last 30 Days',
    field: 'cumulative_30_days_vs_expected',
    sortable: false,
    width: 237,
    cellRenderer: efficiencyBarCellRenderer
  }
];

const SitesTab: React.FC<CompanyDetailsTabProps> = ({ companyDetails }) => {
  const companyId = companyDetails.id;
  const basicTableRef = React.useRef<{ getApi: () => GridApi | undefined }>(null);
  const navigate = useNavigate();
  const { isFullAccess, isUserParentCompany } = useAccess(companyId);
  const showAddBtn = isFullAccess && isUserParentCompany;

  const handleAddClick = () => {
    navigate(`/settings/company/${companyId}/site/add`);
  };

  const serverSideDatasource = React.useMemo(() => {
    return {
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;

        ApiClient.operationsAndMaintenance
          .companySites(companyId, {
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
    };
  }, [companyId]);

  const onRowClicked = React.useCallback<{ (event: RowClickedEvent): void }>(
    e => {
      navigate(`/operations-and-maintenance/companies/${companyDetails.id}/sites/${e?.data?.id}`);
    },
    [companyDetails, navigate]
  );

  return (
    <>
      {showAddBtn && (
        <Box display="flex" flexDirection="row" justifyContent="flex-end" marginBottom="16px">
          <Button variant="contained" color="primary" data-testid="actions__add-btn" onClick={handleAddClick}>
            Add a New Site
          </Button>
        </Box>
      )}
      <BaseTable
        ref={basicTableRef}
        rowModelType="serverSide"
        columnDefs={columns}
        serverSideDatasource={serverSideDatasource}
        onRowClicked={onRowClicked}
        tableRowHeight={52}
        defaultColDefOverrides={defaultColDefOverrides}
        allowMultilineHeader
      />
    </>
  );
};

export default SitesTab;
