import React from 'react';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

export type ArchiveFilterValue = 'active' | 'archived' | 'all';

interface ArchiveFilterProps {
  value: ArchiveFilterValue;
  onChange: (value: ArchiveFilterValue) => void;
}

export const ArchiveFilter: React.FC<ArchiveFilterProps> = ({ value, onChange }) => {
  const handleChange = (_: React.MouseEvent<HTMLElement>, newValue: ArchiveFilterValue | null) => {
    if (newValue !== null) {
      onChange(newValue);
    }
  };

  return (
    <ToggleButtonGroup value={value} exclusive onChange={handleChange} size="small" sx={{ mr: 1 }}>
      <ToggleButton value="active">Active</ToggleButton>
      <ToggleButton value="archived">Archived</ToggleButton>
      <ToggleButton value="all">All</ToggleButton>
    </ToggleButtonGroup>
  );
};

export default ArchiveFilter;
