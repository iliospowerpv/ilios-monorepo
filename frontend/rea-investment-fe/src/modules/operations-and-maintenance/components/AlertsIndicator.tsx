import React from 'react';
import Badge from '@mui/material/Badge';
import Box from '@mui/material/Box';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import BoltIcon from '@mui/icons-material/Bolt';
import { useTheme } from '@mui/material';

interface AlertsIndicatorProps {
  alertsCount: number;
  severity: 'Warning' | 'Informational' | 'Critical';
}

interface IndicatorProperties {
  component: typeof BoltIcon | typeof WarningRoundedIcon;
  iconColor: string;
}

export const AlertsIndicator: React.FC<AlertsIndicatorProps> = ({ alertsCount, severity }) => {
  const { alertSeverity } = useTheme();

  const indicatorPropertiesMapping = React.useMemo<{ [key in AlertsIndicatorProps['severity']]: IndicatorProperties }>(
    () => ({
      Warning: {
        component: WarningRoundedIcon,
        iconColor: alertSeverity.high
      },
      Informational: {
        component: WarningRoundedIcon,
        iconColor: alertSeverity.warning
      },
      Critical: {
        component: BoltIcon,
        iconColor: alertSeverity.severe
      }
    }),
    [alertSeverity]
  );
  const { component: SeverityIcon, iconColor } = indicatorPropertiesMapping[severity];

  return (
    <Box width="100%" height="100%">
      <Badge
        sx={{ '& > .MuiBadge-badge': { transform: 'scale(0.9) translate(70%, -40%)' } }}
        color="primary"
        max={999}
        badgeContent={alertsCount}
      >
        <SeverityIcon sx={{ color: iconColor }} />
      </Badge>
    </Box>
  );
};

export default AlertsIndicator;
