import React from 'react';
import Box from '@mui/material/Box';
import { styled } from '@mui/material/styles';
import CircularProgress from '@mui/material/CircularProgress';
import WbCloudyIcon from '@mui/icons-material/WbCloudy';

const WeatherIndicatorImage = styled('img')(() => ({
  borderRadius: '8px',
  height: '32px',
  widows: '32px'
}));

const DEMO_ICON_PREFIXES = ['DEMO_'];

export const WeatherIndicator: React.FC<{ imageSrc: string | null }> = ({ imageSrc }) => {
  const isDemoIcon = imageSrc && DEMO_ICON_PREFIXES.some(p => imageSrc.startsWith(p));
  const shouldLoad = imageSrc && imageSrc !== 'N/A' && !isDemoIcon;
  const [isLoaded, setIsLoaded] = React.useState(false);

  if (isDemoIcon) {
    return (
      <Box display="flex" borderRadius="8px" flexDirection="column" alignItems="center" justifyContent="center">
        <WbCloudyIcon sx={{ fontSize: '32px', color: '#90A4AE' }} />
      </Box>
    );
  }

  return (
    <Box
      position="relative"
      display="flex"
      borderRadius="8px"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
    >
      {shouldLoad ? (
        <WeatherIndicatorImage
          alt="weather icon"
          src={imageSrc}
          height="32px"
          width="32px"
          onLoad={() => setIsLoaded(true)}
        />
      ) : (
        <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center">
          <WbCloudyIcon sx={{ fontSize: '32px', color: '#90A4AE' }} />
        </Box>
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
    </Box>
  );
};

export default WeatherIndicator;
