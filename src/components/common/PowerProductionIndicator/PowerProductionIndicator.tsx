import React from 'react';
import { useTheme } from '@mui/material';
import Box from '@mui/material/Box';

interface PowerProductionIndicatorProps {
  actualPerformance: number;
  actualVsExpected: number;
  formatter?: (value: number) => string;
}

export const PowerProductionIndicator: React.FC<PowerProductionIndicatorProps> = ({
  actualPerformance,
  actualVsExpected,
  formatter
}) => {
  const { efficiencyColors } = useTheme();

  /*
    ! this function can be re-used in case if we decide to drop this approach (illustrating efficiency
      using colored circles) in favour of just having plain colored text in cells, where text-color illustrates
      efficiency;
      then this code should be used in cellStyle func which can be passed via cell-defs to add dynamic styling
      to table cells
   */
  const deriveMarkerColorFromEfficiency = React.useCallback(
    (efficiency: number): string => {
      if (efficiency < 51) return efficiencyColors.low;
      if (efficiency < 90) return efficiencyColors.mediocre;
      if (efficiency < 101) return efficiencyColors.good;
      return efficiencyColors.outstanding;
    },
    [efficiencyColors]
  );

  const markerColor = deriveMarkerColorFromEfficiency(actualVsExpected);

  return (
    <Box
      sx={{
        display: 'inline-flex',
        flexWrap: 'nowrap',
        alignItems: 'center',
        '& .performance-efficiency-marker': {
          display: 'inline-block',
          height: '20px',
          width: '20px',
          borderRadius: '20px',
          mr: 1,
          bgcolor: markerColor
        }
      }}
    >
      {/*
          ! span-element efficiency marker can be replaced with any suitable icon from material icons
            some of suitable icons which can be potentially used are following:
              - TungstenRoundedIcon
              - OfflineBoltRoundedIcon
              - ElectricMeterRoundedIcon
              - WbIncandescentRoundedIcon
              - EmojiObjectsRoundedIcon
      */}
      <span className="performance-efficiency-marker" />
      <span>{formatter ? formatter(actualPerformance) : actualPerformance}</span>
    </Box>
  );
};

export default PowerProductionIndicator;
