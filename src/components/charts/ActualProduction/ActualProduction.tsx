import React from 'react';
import Box, { BoxProps } from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import InfoIcon from '@mui/icons-material/Info';
import IconButton from '@mui/material/IconButton';
import Tooltip, { TooltipProps, tooltipClasses } from '@mui/material/Tooltip';
import Grid from '@mui/material/Grid';
import { styled, useTheme } from '@mui/material/styles';
import RefreshIcon from '@mui/icons-material/Refresh';
import { Doughnut } from 'react-chartjs-2';
import 'chart.js/auto';

import { formatFloatValue } from '../../../utils/formatters/formatFloatValue';
import { CircularProgress } from '@mui/material';
import ToggleGroup from '../../../components/common/ToogleGroup/ToggleGroup';

interface WidgetContainerScoped extends BoxProps {
  scope?: 'O&M' | 'investor-dashboard';
}

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

export const WidgetContainer = styled(Box, {
  shouldForwardProp: prop => prop !== 'scope'
})<WidgetContainerScoped>(({ scope }) => ({
  display: 'flex',
  flexDirection: 'column',
  flexGrow: 1,
  padding: '16px',
  border: '1px solid',
  borderColor: scope !== 'investor-dashboard' ? '#0000003B' : '#0000001F',
  height: '100%',
  minHeight: '360px'
}));

interface ActualProductionCommonProps {
  title: string;
  onClickRefetch?: () => void;
}

interface ActualProductionOMScopeProps extends ActualProductionCommonProps {
  scope?: 'O&M';
  companyName?: undefined | null;
  data?: {
    actual_vs_expected: number;
    total_actual_kw: number;
    total_expected_kw: number;
    total_sites: number;
    total_system_size_ac: number;
    total_system_size_dc: number;
    cumulative_actual_kw: number;
    cumulative_expected_kw: number;
    cumulative_actual_vs_expected: number | null;
  };
  isFetchingCompanyData?: boolean | null;
  errorLoadingCompanyData?: Error | null;
  companiesDataRendered?: boolean | null;
}

interface ActualProductionInvestorDashboardScopeProps extends ActualProductionCommonProps {
  scope: 'investor-dashboard';
  data?: {
    id: number;
    total_sites: number;
    total_actual_kw: number;
    total_expected_kw: number;
    total_system_size_ac: number;
    total_system_size_dc: number;
    actual_vs_expected: number | null;
    cumulative_actual_kw: number;
    cumulative_expected_kw: number;
    cumulative_actual_vs_expected: number | null;
  };
  isFetchingCompanyData?: boolean | null;
  errorLoadingCompanyData?: Error | null;
  companiesDataRendered?: boolean | null;
}

type ActualProductionProps = ActualProductionOMScopeProps | ActualProductionInvestorDashboardScopeProps;

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

const ActualProduction: React.FC<ActualProductionProps> = ({
  title,
  data,
  scope,
  isFetchingCompanyData,
  errorLoadingCompanyData,
  companiesDataRendered,
  onClickRefetch
}) => {
  const theme = useTheme();
  const [alignment, setAlignment] = React.useState('current');

  const { total_sites = 0, total_system_size_ac = 0, total_system_size_dc = 0 } = data || {};
  const total_actual_kw = alignment === 'current' ? data?.total_actual_kw ?? 0 : data?.cumulative_actual_kw ?? 0;
  const total_expected_kw = alignment === 'current' ? data?.total_expected_kw ?? 0 : data?.cumulative_expected_kw ?? 0;
  const actual_vs_expected =
    alignment === 'current' ? data?.actual_vs_expected ?? 0 : data?.cumulative_actual_vs_expected ?? 0;

  const actualVsExpected =
    typeof actual_vs_expected === 'number' ? (actual_vs_expected > 100 ? 100 : actual_vs_expected) : 0;
  const actualVsExpectedRest = 100 - actualVsExpected ?? 0;

  const deriveProductionColorFromValue = (progress: number): string => {
    if (progress < 51) return theme.efficiencyColors.low;
    if (progress < 90) return theme.efficiencyColors.mediocre;
    if (progress < 101) return theme.efficiencyColors.good;
    return theme.efficiencyColors.outstanding;
  };

  const chartData = {
    datasets: [
      {
        data: [actualVsExpected, actualVsExpectedRest],
        backgroundColor: [deriveProductionColorFromValue(actual_vs_expected ?? 0), '#F3F4F8'],
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
    <WidgetContainer scope={scope}>
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
        {scope === 'investor-dashboard' ? (
          <Typography variant="h6" fontSize="24px">
            {title}
          </Typography>
        ) : (
          <Typography variant="h6" mb="6px">
            {title}
          </Typography>
        )}
        <Box>
          <ToggleGroup alignment={alignment} setAlignment={setAlignment} />
          <IconButton title="Refetch" disabled={!!isFetchingCompanyData} onClick={onClickRefetch}>
            <RefreshIcon sx={{ color: 'rgba(0, 0, 0, 0.87);' }} />
          </IconButton>
        </Box>
      </Box>
      <Box flexGrow={1} position="relative">
        {data && !isFetchingCompanyData && !errorLoadingCompanyData && (
          <Box sx={{ display: 'flex', flexDirection: 'row', flexGrow: 1 }}>
            <Grid container spacing={2}>
              <Grid
                item
                xs={6}
                sx={{
                  position: 'relative',
                  '&.MuiGrid-item': { paddingTop: '0' },
                  minHeight: '240px'
                }}
              >
                <Doughnut data={chartData} options={options} />
                <Box
                  sx={{
                    position: 'absolute',
                    left: '54%',
                    transform: 'translate(-50%, 0)',
                    fontSize: '20px',
                    top: '50%',
                    textAlign: 'center'
                  }}
                >
                  {actual_vs_expected}{' '}
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
                </Box>
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
                    {formatFloatValue(total_expected_kw ?? 0)}
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
                        {formatFloatValue(total_system_size_ac ?? 0)} AC / {formatFloatValue(total_system_size_dc ?? 0)}{' '}
                        DC
                      </Typography>
                      <Typography variant="caption" color={theme => theme.palette.text.secondary}>
                        System Size (kW)
                      </Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="h6" fontWeight={700} fontSize={14} lineHeight="20px">
                        {total_sites ?? 0}
                      </Typography>
                      <Typography variant="caption" color={theme => theme.palette.text.secondary}>
                        Sites
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
                    alignItems: 'baseline',
                    padding: '8px 16px',
                    backgroundColor: theme => theme.palette.background.default
                  }}
                >
                  <Grid
                    item
                    xs={4}
                    sx={{ '&.MuiGrid-item': { borderRight: '1px solid #E0E0E0', marginRight: '16px' } }}
                  >
                    <Typography variant="h6" fontWeight={700} fontSize={20} lineHeight="32px">
                      {formatFloatValue(total_actual_kw ?? 0)}
                    </Typography>
                    <Typography variant="caption" color={theme => theme.palette.text.secondary}>
                      {alignment === 'current' ? `Actual (kW)` : `Actual (kWh)`}
                    </Typography>
                  </Grid>
                  <Grid
                    item
                    xs={4}
                    sx={scope !== 'investor-dashboard' ? { '&.MuiGrid-item': { marginRight: '16px' } } : undefined}
                  >
                    <Typography variant="h6" fontWeight={700} fontSize={20} lineHeight="32px">
                      {formatFloatValue(total_expected_kw ?? 0)}
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
                </Box>
              </Grid>
            </Grid>
          </Box>
        )}
        {isFetchingCompanyData && <Loading />}
        {!isFetchingCompanyData && errorLoadingCompanyData && (
          <MessageOverlay msg="An error occurred when retrieving the actual production data" />
        )}
        {!isFetchingCompanyData &&
          !data &&
          !errorLoadingCompanyData &&
          (scope === 'investor-dashboard' ? companiesDataRendered : true) && <MessageOverlay msg="No Data" />}
      </Box>
    </WidgetContainer>
  );
};

export default ActualProduction;
