import React from 'react';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ToggleButton from '@mui/material/ToggleButton';

interface ToggleComponentProps {
  alignment: string;
  setAlignment: (view: string) => void;
}
const ToggleGroup: React.FC<ToggleComponentProps> = ({ alignment, setAlignment }) => {
  const handleToggleButtonChange = (event: React.MouseEvent<HTMLElement>, newAlignment: string) => {
    if (newAlignment !== null) {
      setAlignment(newAlignment);
    }
  };

  return (
    <ToggleButtonGroup
      size="small"
      data-testid="toggle__group"
      value={alignment}
      exclusive
      onChange={handleToggleButtonChange}
      sx={{ height: '32px' }}
    >
      <ToggleButton value="current" sx={{ width: '150px', fontSize: '12px' }}>
        Current Production (kW)
      </ToggleButton>
      <ToggleButton value="today" sx={{ width: '130px', fontSize: '12px' }}>
        24-hour Trend (kWh)
      </ToggleButton>
    </ToggleButtonGroup>
  );
};

export default ToggleGroup;
