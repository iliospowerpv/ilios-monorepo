import React from 'react';
import Box from '@mui/material/Box';
import { styled } from '@mui/material/styles';
import CircularProgress from '@mui/material/CircularProgress';
import BrokenImageIcon from '@mui/icons-material/BrokenImage';

const WeatherIndicatorImage = styled('img')(() => ({
  borderRadius: '8px',
  height: '32px',
  widows: '32px'
}));

export const WeatherIndicator: React.FC<{ imageSrc: string | null }> = ({ imageSrc }) => {
  const shouldLoad = imageSrc && imageSrc !== 'N/A';
  const [isLoaded, setIsLoaded] = React.useState(false);

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
        <Box
          height="32px"
          width="32px"
          borderRadius="8px"
          bgcolor="#96B4E4"
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
        >
          <BrokenImageIcon sx={{ color: '#FFFFFF', fontSize: '18px' }} />
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
