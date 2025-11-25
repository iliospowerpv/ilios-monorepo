import React from 'react';
import { ColDef, GridApi } from 'ag-grid-community';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import BaseTable from '../../../../../components/common/tables/BaseTable/BaseTable';
import { ApiClient } from '../../../../../api';
import EfficiencyRateBar from '../../../../../components/common/EfficiencyRateBar/EfficiencyRateBar';
import WeatherIndicator from '../../../../../components/common/WeatherIndicator/WeatherIndicator';
import { formatFloatValue } from '../../../../../utils/formatters/formatFloatValue';
import { BootstrapTooltip } from '../../../../../components/common/BootstrapTooltip/BootstrapTooltip';

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

const SitesTab: React.FC = () => {
  const basicTableRef = React.useRef<{ getApi: () => GridApi | undefined }>(null);

  const serverSideDatasource = React.useMemo(() => {
    return {
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;

        ApiClient.investorDashboard
          .sites({
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
  }, []);

  return (
    <BaseTable
      ref={basicTableRef}
      rowModelType="serverSide"
      columnDefs={columns}
      serverSideDatasource={serverSideDatasource}
      tableRowHeight={52}
      defaultColDefOverrides={defaultColDefOverrides}
      allowMultilineHeader
    />
  );
};

export default SitesTab;
