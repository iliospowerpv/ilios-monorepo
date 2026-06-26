import React from 'react';
import Box from '@mui/material/Box';
import { styled } from '@mui/material/styles';
import CircularProgress from '@mui/material/CircularProgress';
import WbSunnyIcon from '@mui/icons-material/WbSunny';
import WbCloudyIcon from '@mui/icons-material/WbCloudy';
import CloudIcon from '@mui/icons-material/Cloud';
import GrainIcon from '@mui/icons-material/Grain';
import WbTwilightIcon from '@mui/icons-material/WbTwilight';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import CloudOffIcon from '@mui/icons-material/CloudOff';
import type { SvgIconComponent } from '@mui/icons-material';

import type { ObservedCondition, ObservedConditionState } from '../../../types/telemetryV2';

const WeatherIndicatorImage = styled('img')(() => ({
  borderRadius: '8px',
  height: '32px',
  width: '32px'
}));

// Native observed-condition state -> MUI icon + color. Honest, never "rainy":
// `overcast_unknown` uses a neutral precipitation-undetermined glyph and
// `unavailable` shows a struck-through cloud (never a fabricated "sunny"/0).
const STATE_ICON: Record<ObservedConditionState, { Icon: SvgIconComponent; color: string }> = {
  sunny: { Icon: WbSunnyIcon, color: '#F9A825' },
  partly_cloudy: { Icon: WbCloudyIcon, color: '#90A4AE' },
  cloudy: { Icon: CloudIcon, color: '#78909C' },
  overcast_unknown: { Icon: GrainIcon, color: '#607D8B' },
  low_light: { Icon: WbTwilightIcon, color: '#8D6E63' },
  nighttime: { Icon: DarkModeIcon, color: '#5C6BC0' },
  unavailable: { Icon: CloudOffIcon, color: '#B0BEC5' }
};

interface WeatherIndicatorProps {
  /**
   * Native observed condition (preferred). When this prop is provided (even as
   * `null`), the indicator renders a state-driven MUI icon; `null`/`unavailable`
   * shows the honest "unavailable" glyph rather than a fabricated condition.
   */
  condition?: ObservedCondition | null;
  /**
   * Legacy Weatherstack image URL (dual-run fallback). Used ONLY when no
   * `condition` prop is supplied, so existing callers keep working unchanged.
   */
  imageSrc?: string | null;
}

const IndicatorBox: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Box
    data-testid="weather-indicator__component"
    position="relative"
    display="flex"
    borderRadius="8px"
    flexDirection="column"
    alignItems="center"
    justifyContent="center"
  >
    {children}
  </Box>
);

export const WeatherIndicator: React.FC<WeatherIndicatorProps> = ({ condition, imageSrc }) => {
  const [isLoaded, setIsLoaded] = React.useState(false);
  const [hasError, setHasError] = React.useState(false);

  // Native path: a `condition` prop (present, possibly null) wins over imageSrc.
  if (condition !== undefined) {
    const state = condition?.state ?? 'unavailable';
    const { Icon, color } = STATE_ICON[state] ?? STATE_ICON.unavailable;
    const label = condition?.label ?? 'Observed weather unavailable';
    return (
      <IndicatorBox>
        <Icon role="img" aria-label={label} sx={{ fontSize: '32px', color }} />
      </IndicatorBox>
    );
  }

  // Legacy Weatherstack image path (kept for dual-run). A non-loading/broken
  // src falls back to a neutral cloud rather than spinning forever.
  const shouldLoad = !!imageSrc && imageSrc !== 'N/A' && !hasError;
  return (
    <IndicatorBox>
      {shouldLoad ? (
        <WeatherIndicatorImage
          alt="weather icon"
          src={imageSrc as string}
          height="32px"
          width="32px"
          onLoad={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
        />
      ) : (
        <WbCloudyIcon sx={{ fontSize: '32px', color: '#90A4AE' }} />
      )}
      {shouldLoad && !isLoaded && (
        <Box
          position="absolute"
          height="32px"
          width="32px"
          borderRadius="8px"
          bgcolor="#96B4E4"
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
        >
          <CircularProgress sx={{ color: '#FFFFFF' }} size="16px" />
        </Box>
      )}
    </IndicatorBox>
  );
};

export default WeatherIndicator;
