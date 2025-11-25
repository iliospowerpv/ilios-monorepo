import React from 'react';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ToggleButton from '@mui/material/ToggleButton';

interface ToggleComponentProps {
  alignment: string;
  setAlignment: (alignment: string) => void;
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
      sx={{ height: '40px' }}
    >
      <ToggleButton value="list" sx={{ width: '104px' }}>
        List
      </ToggleButton>
      <ToggleButton value="board" sx={{ width: '104px' }}>
        Board
      </ToggleButton>
      <ToggleButton value="calendar" sx={{ width: '104px' }}>
        Calendar
      </ToggleButton>
    </ToggleButtonGroup>
  );
};

export default ToggleGroup;
