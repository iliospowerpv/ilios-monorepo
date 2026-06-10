import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import InfoIcon from '@mui/icons-material/Info';
import Tooltip, { tooltipClasses, TooltipProps } from '@mui/material/Tooltip';
import Grid from '@mui/material/Grid';
import { styled, useTheme } from '@mui/material/styles';
import RefreshIcon from '@mui/icons-material/Refresh';
import { Doughnut } from 'react-chartjs-2';
import 'chart.js/auto';
import { useQuery } from '@tanstack/react-query';
import CircularProgress from '@mui/material/CircularProgress';

import { WidgetContainer } from '../../Overview.style';
import { formatFloatValue } from '../../../../../../../../utils/formatters/formatFloatValue';
import { ApiClient } from '../../../../../../../../api';
import { useSiteLatestTelemetry } from '../../../../../../../../hooks/telemetryV2';
import WeatherIndicator from '../../../../../../../../components/common/WeatherIndicator/WeatherIndicator';
import ToggleGroup from '../../../../../../../../components/common/ToogleGroup/ToggleGroup';

interface ActualProductionProps {
  siteId: number;
}

// Render an absolute timestamp from the V2 /latest snapshot. Returns '' for a
// missing/invalid value so the caption can be hidden for non-V2 sites.
const formatWhen = (iso: string | null | undefined): string => {
  if (!iso) return '';
  const when = new Date(iso);
  return Number.isNaN(when.getTime()) ? '' : when.toLocaleString();
};

const Loading: React.FC = () => (
  <Box position="absolute" width="100%" border="1px solid transparent" height="calc(100% - 32px)">
    <Box
      width="100%"
      height="100%"
      position="absolute"
      p="16px"
      top="0"
      display="flex"
      justifyContent="center"
      alignItems="center"
      flexDirection="column"
      bgcolor="#FFFFFF"
    >
      <CircularProgress />
    </Box>
  </Box>
);

const MessageOverlay: React.FC<{ msg: string }> = ({ msg }) => (
  <Box position="absolute" width="100%" border="1px solid transparent" height="calc(100% - 32px)">
    <Box
      width="100%"
      height="100%"
      position="absolute"
      p="16px"
      top="0"
      display="flex"
      justifyContent="center"
      alignItems="center"
      flexDirection="column"
      bgcolor="#FFFFFF"
    >
      <Typography variant="body1" textAlign="center" width="70%">
        {msg}
      </Typography>
    </Box>
  </Box>
);

const BootstrapTooltip = styled(({ className, ...props }: TooltipProps) => (
  <Tooltip {...props} arrow classes={{ popper: className }} />
))(({ theme }) => ({
  [`& .${tooltipClasses.arrow}`]: {
    color: theme.palette.common.black
  },
  [`& .${tooltipClasses.tooltip}`]: {
    backgroundColor: theme.palette.common.black
  }
}));

const ActualProduction: React.FC<ActualProductionProps> = ({ siteId }) => {
  const { data, isFetching, error, refetch } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.getSiteDashboardProduction(siteId),
    queryKey: ['sites', 'actual-production-chart', { siteId }],
    refetchInterval: 15 * 60 * 1000,
    staleTime: 15 * 60 * 1000
  });

  // Read-only freshness snapshot; empty (all-null) for non-V2 sites, in which
  // case the caption below is hidden.
  const { data: latestTelemetry } = useSiteLatestTelemetry(siteId);
  const lastRefreshed = formatWhen(latestTelemetry?.latest_reading_at);

  const theme = useTheme();
  const [alignment, setAlignment] = React.useState('current');

  const { system_size_ac = 0, system_size_dc = 0, weather = 'Sunny' } = data || {};
  const actual_kw = alignment === 'current' ? (data?.actual_kw ?? 0) : (data?.cumulative_actual_kw ?? 0);
  const expected_kw = alignment === 'current' ? (data?.expected_kw ?? 0) : (data?.cumulative_expected_kw ?? 0);
  const actual_vs_expected =
    alignment === 'current' ? (data?.actual_vs_expected ?? 0) : (data?.cumulative_actual_vs_expected ?? 0);

  const actualVsExpected = actual_vs_expected > 100 ? 100 : (actual_vs_expected ?? 0);
  const actualVsExpectedRest = 100 - actualVsExpected ?? 0;

  // V2 telemetry sites carry actual-only data (no projected baseline). When the
  // baseline is unavailable, render an honest neutral ring and "N/A" /
  // "Baseline not available" instead of a misleading red 0% / 0 kW.
  const baselineAvailable = data?.expected_baseline_available ?? true;
  const expectedDisplay = baselineAvailable ? formatFloatValue(expected_kw ?? 0) : 'N/A';

  const deriveProductionColorFromValue = (progress: number): string => {
    if (progress < 51) return theme.efficiencyColors.low;
    if (progress < 90) return theme.efficiencyColors.mediocre;
    if (progress < 101) return theme.efficiencyColors.good;
    return theme.efficiencyColors.outstanding;
  };

  const chartData = {
    datasets: [
      {
        // No baseline -> fully neutral ring (0 filled) so it reads as "no data".
        data: baselineAvailable ? [actualVsExpected, actualVsExpectedRest] : [0, 100],
        backgroundColor: [
          baselineAvailable ? deriveProductionColorFromValue(actual_vs_expected) : theme.efficiencyColors.none,
          '#F3F4F8'
        ],
        cutout: '75%'
      }
    ]
  };

  const options = {
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        enabled: false
      }
    },
    circumference: 180,
    rotation: 270
  };

  return (
    <WidgetContainer>
      <Box
        sx={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          flexWrap: 'nowrap',
          marginBottom: '6px',
          alignItems: 'flex-start'
        }}
      >
        <Box>
          <Typography variant="h6" mb="6px">
            Production
          </Typography>
          {lastRefreshed && (
            <Typography variant="caption" color={theme => theme.palette.text.secondary} sx={{ display: 'block' }}>
              Last refreshed {lastRefreshed}
            </Typography>
          )}
        </Box>
        <Box>
          <ToggleGroup alignment={alignment} setAlignment={setAlignment} />
          <IconButton title="Refetch" disabled={!!isFetching} onClick={() => refetch()}>
            <RefreshIcon sx={{ color: 'rgba(0, 0, 0, 0.87);' }} />
          </IconButton>
        </Box>
      </Box>
      <Box flexGrow={1} position="relative">
        {data && !isFetching && !error && (
          <Box sx={{ display: 'flex', flexDirection: 'row', flexGrow: 1, maxHeight: '300px' }}>
            <Grid container spacing={2}>
              <Grid
                item
                xs={6}
                sx={{
                  position: 'relative',
                  '&.MuiGrid-item': { paddingTop: '0', minHeight: '240px' }
                }}
              >
                <Doughnut data={chartData} options={options} />
                <Typography
                  sx={{
                    position: 'absolute',
                    left: '54%',
                    transform: 'translate(-50%, 0)',
                    fontSize: '20px',
                    top: '50%',
                    textAlign: 'center'
                  }}
                >
                  {baselineAvailable ? (
                    <>
                      {actual_vs_expected ?? 0}{' '}
                      <Typography
                        variant="body2"
                        display="inline-block"
                        fontSize={12}
                        color={theme => theme.palette.text.secondary}
                      >
                        %
                      </Typography>
                      <Typography variant="body2" fontSize={12} color={theme => theme.palette.text.secondary}>
                        from Expected
                      </Typography>
                    </>
                  ) : (
                    <>
                      N/A
                      <Typography variant="body2" fontSize={12} color={theme => theme.palette.text.secondary}>
                        Baseline not available
                      </Typography>
                    </>
                  )}
                </Typography>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    position: 'absolute',
                    top: '77%',
                    width: '92%'
                  }}
                >
                  <Typography variant="body2" fontSize={12} color={theme => theme.palette.text.secondary}>
                    0
                  </Typography>
                  <Typography variant="body2" fontSize={12} color={theme => theme.palette.text.secondary}>
                    {expectedDisplay}
                  </Typography>
                </Box>
              </Grid>
              <Grid
                item
                xs={6}
                sx={{
                  '&.MuiGrid-item': { paddingTop: '0', display: 'flex', justifyContent: 'center', alignItems: 'center' }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                  <Grid container spacing={1}>
                    <Grid item xs={12}>
                      <Typography variant="h6" fontWeight={700} fontSize={14} lineHeight="20px">
                        {formatFloatValue(system_size_ac ?? 0)} AC / {formatFloatValue(system_size_dc ?? 0)} DC
                      </Typography>
                      <Typography variant="caption" color={theme => theme.palette.text.secondary}>
                        System Size (kW)
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              </Grid>
              <Grid item xs={12} sx={{ '&.MuiGrid-item': { paddingTop: '0' } }}>
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'row',
                    padding: '8px 16px',
                    backgroundColor: theme => theme.palette.background.default
                  }}
                >
                  <Grid
                    item
                    xs={4}
                    sx={{
                      '&.MuiGrid-item': {
                        borderRight: theme => `1px solid ${theme.palette.divider}`,
                        marginRight: '16px'
                      }
                    }}
                  >
                    <Typography variant="h6" fontWeight={700} fontSize={20} lineHeight="32px">
                      {formatFloatValue(actual_kw ?? 0)}
                    </Typography>
                    <Typography variant="caption" color={theme => theme.palette.text.secondary}>
                      {alignment === 'current' ? `Actual (kW)` : `Actual (kWh)`}
                    </Typography>
                  </Grid>
                  <Grid
                    item
                    xs={4}
                    sx={{
                      '&.MuiGrid-item': {
                        borderRight: theme => `1px solid ${theme.palette.divider}`,
                        marginRight: '16px'
                      }
                    }}
                  >
                    <Typography variant="h6" fontWeight={700} fontSize={20} lineHeight="32px">
                      {expectedDisplay}
                    </Typography>
                    <Typography variant="caption" color={theme => theme.palette.text.secondary}>
                      {alignment === 'current' ? `Expected (kW)` : `Expected (kWh)`}
                      <BootstrapTooltip
                        title={
                          alignment === 'current'
                            ? 'Weather Adjusted Projection (kW)'
                            : 'Weather Adjusted Projection (kWh)'
                        }
                        placement="right"
                      >
                        <IconButton sx={{ padding: 0, margin: '0 0 4px 4px' }}>
                          <InfoIcon sx={{ fontSize: '20px' }} />
                        </IconButton>
                      </BootstrapTooltip>
                    </Typography>
                  </Grid>
                  <Grid item xs={4} sx={{ '&.MuiGrid-item': { textAlign: 'center' } }}>
                    {weather && (
                      <BootstrapTooltip
                        title={
                          weather && typeof weather === 'object' && 'weather_description' in weather
                            ? weather.weather_description
                            : weather
                        }
                      >
                        <Box
                          display="flex"
                          flexDirection="column"
                          width="100%"
                          maxWidth="100%"
                          height="100%"
                          alignItems="center"
                          gap="4px"
                        >
                          <WeatherIndicator
                            imageSrc={
                              weather && typeof weather === 'object' && 'weather_icon_url' in weather
                                ? weather.weather_icon_url
                                : null
                            }
                          />
                          <Typography
                            variant="caption"
                            noWrap
                            width="100%"
                            maxWidth="100%"
                            color={theme => theme.palette.text.secondary}
                          >
                            {weather && typeof weather === 'object' && 'weather_description' in weather
                              ? weather.weather_description
                              : weather}
                          </Typography>
                        </Box>
                      </BootstrapTooltip>
                    )}
                  </Grid>
                </Box>
              </Grid>
            </Grid>
          </Box>
        )}
        {isFetching && <Loading />}
        {!isFetching && error && <MessageOverlay msg="An error occurred when retrieving the actual production data" />}
        {!isFetching && !data && !error && <MessageOverlay msg="No Data" />}
      </Box>
    </WidgetContainer>
  );
};

export default ActualProduction;
