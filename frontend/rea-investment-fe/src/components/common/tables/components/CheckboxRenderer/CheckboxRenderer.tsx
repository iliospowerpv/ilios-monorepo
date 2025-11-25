import React, { memo } from 'react';
import { Checkbox } from '@mui/material';

import { CheckIcon, CrossIcon, CellContainer } from './CheckboxRenderer.styles';

interface CheckboxRendererProps {
  value: boolean;
  isRowSelected: boolean;
  isRowEditMode: boolean;
  onChange: (checked: boolean) => void;
}

const CheckboxRenderer: React.FC<CheckboxRendererProps> = memo(({ value, onChange, isRowSelected, isRowEditMode }) => {
  return (
    <CellContainer>
      {isRowSelected && isRowEditMode ? (
        <Checkbox checked={value} onChange={event => onChange(event.target.checked)} />
      ) : value ? (
        <CheckIcon />
      ) : (
        <CrossIcon />
      )}
    </CellContainer>
  );
});

CheckboxRenderer.displayName = 'CheckboxRenderer';

export default CheckboxRenderer;
