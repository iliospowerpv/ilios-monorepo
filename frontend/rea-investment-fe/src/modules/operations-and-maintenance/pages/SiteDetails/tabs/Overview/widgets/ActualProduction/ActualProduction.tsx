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
import { useNativeWeatherCondition } from '../../../../../../../../hooks/useNativeWeatherCondition';
import WeatherIndicator from '../../../../../../../../components/common/WeatherIndicator/WeatherIndicator';
import ToggleGroup from '../../../../../../../../components/common/ToogleGroup/ToggleGroup';
import { parseUtc } from '../../../../../../../../utils/time/utcTime';
import { resolveExpectedState } from '../../../../../../../../utils/telemetry/expectedState';

interface ActualProductionProps {
  siteId: number;
}

// Render an absolute timestamp from the V2 /latest snapshot. Returns '' for a
// missing/invalid value so the caption can be hidden for non-V2 sites.
const formatWhen = (iso: string | null | undefined): string => {
  // Backend serializes naive-UTC timestamps; parse as UTC then render in the
  // viewer's browser timezone (matching the rest of the app).
  const when = parseUtc(iso);
  return when ? when.toLocaleString() : '';
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

  // Native observed-weather condition (dual-run alongside the untouched
  // Weatherstack pipeline). Drives the cosmetic chip below; null/unavailable
  // hides it (never a fabricated condition).
  const { data: observedCondition } = useNativeWeatherCondition(siteId);

  const theme = useTheme();
  const [alignment, setAlignment] = React.useState('current');

  const { system_size_ac = 0, system_size_dc = 0 } = data || {};

  // Honest null handling: only null/undefined map to N/A. A genuine measured 0
  // and a negative night-time tare value are finite and preserved untouched.
  const isNum = (v: number | null | undefined): v is number => typeof v === 'number' && Number.isFinite(v);

  // V2 telemetry sites carry actual-only data (no projected baseline). The
  // resolver maps expected_state (or the legacy boolean) to a display mode:
  // available/partial -> show expected; missing_inputs/pre_pto/
  // baseline_not_available -> honest "N/A" + reason, never a fabricated 0.
  const expectedState = resolveExpectedState(data);
  const rawExpected = alignment === 'current' ? data?.expected_kw : data?.cumulative_expected_kw;
  const expectedDisplay = expectedState.showExpected && isNum(rawExpected) ? formatFloatValue(rawExpected) : 'N/A';

  // Actual value for the selected scope. Kept raw (no `?? 0`) so a missing
  // actual renders as N/A instead of a misleading 0.
  const actualRaw = alignment === 'current' ? data?.actual_kw : data?.cumulative_actual_kw;
  const actualAvailable = isNum(actualRaw);

  // Variance/percent is meaningful only when BOTH sides are present: a measured
  // actual AND a usable expected baseline. Otherwise the gauge shows "Variance
  // N/A" rather than a fabricated 0% ring.
  const varianceRaw = alignment === 'current' ? data?.actual_vs_expected : data?.cumulative_actual_vs_expected;
  const varianceAvailable = expectedState.showExpected && actualAvailable && isNum(varianceRaw);
  const varianceValue = isNum(varianceRaw) ? varianceRaw : 0;
  const actualVsExpected = varianceValue > 100 ? 100 : varianceValue;
  const actualVsExpectedRest = 100 - actualVsExpected;

  // Caption for the "Variance N/A" state — actual-side reason first, then the
  // expected-side term from the resolver.
  const varianceReason = !actualAvailable ? 'Actual unavailable' : expectedState.term;

  const deriveProductionColorFromValue = (progress: number): string => {
    if (progress < 51) return theme.efficiencyColors.low;
    if (progress < 90) return theme.efficiencyColors.mediocre;
    if (progress < 101) return theme.efficiencyColors.good;
    return theme.efficiencyColors.outstanding;
  };

  const chartData = {
    datasets: [
      {
        // No usable variance (missing actual or expected) -> fully neutral ring
        // (0 filled) so it reads as "no data", never a fabricated 0%.
        data: varianceAvailable ? [actualVsExpected, actualVsExpectedRest] : [0, 100],
        backgroundColor: [
          varianceAvailable ? deriveProductionColorFromValue(varianceValue) : theme.efficiencyColors.none,
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
                  {varianceAvailable ? (
                    <>
                      {varianceValue}{' '}
                      <Typography
                        variant="body2"
                        display="inline-block"
                        fontSize={12}
                        color={theme => theme.palette.text.secondary}
                      >
                        %
                      </Typography>
                      <Typography variant="body2" fontSize={12} color={theme => theme.palette.text.secondary}>
                        {expectedState.isPartial ? 'from Expected (partial)' : 'from Expected'}
                      </Typography>
                    </>
                  ) : (
                    <>
                      Variance N/A
                      <Typography variant="body2" fontSize={12} color={theme => theme.palette.text.secondary}>
                        {varianceReason}
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
                      {isNum(actualRaw) ? formatFloatValue(actualRaw) : 'N/A'}
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
                    {observedCondition && observedCondition.state !== 'unavailable' && (
                      <BootstrapTooltip title={`Observed (native): ${observedCondition.label}`}>
                        <Box
                          display="flex"
                          flexDirection="column"
                          width="100%"
                          maxWidth="100%"
                          height="100%"
                          alignItems="center"
                          gap="4px"
                        >
                          <Typography
                            variant="caption"
                            color={theme => theme.palette.text.secondary}
                            sx={{ lineHeight: 1 }}
                          >
                            Observed
                          </Typography>
                          <WeatherIndicator condition={observedCondition} />
                          <Typography
                            variant="caption"
                            noWrap
                            width="100%"
                            maxWidth="100%"
                            color={theme => theme.palette.text.secondary}
                          >
                            {observedCondition.label}
                          </Typography>
                        </Box>
                      </BootstrapTooltip>
                    )}
                  </Grid>
                </Box>
              </Grid>
              {!actualAvailable && (
                <Grid item xs={12} sx={{ '&.MuiGrid-item': { paddingTop: '4px' } }}>
                  <Typography variant="caption" color={theme => theme.palette.text.secondary}>
                    Actual production is unavailable for this period (no telemetry reading), shown as N/A.
                  </Typography>
                </Grid>
              )}
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
