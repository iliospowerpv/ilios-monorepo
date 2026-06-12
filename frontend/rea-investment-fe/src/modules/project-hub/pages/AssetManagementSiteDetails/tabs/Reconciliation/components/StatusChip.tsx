import React from 'react';
import Chip from '@mui/material/Chip';
import { BootstrapTooltip } from '../../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import { statusMeta } from '../utils';

interface StatusChipProps {
  status: string;
}

export const StatusChip: React.FC<StatusChipProps> = ({ status }) => {
  const meta = statusMeta(status);
  return (
    <BootstrapTooltip title={meta.description} placement="top">
      <Chip
        label={meta.label}
        color={meta.color}
        size="small"
        variant="outlined"
        data-testid="reconciliation-status-chip"
      />
    </BootstrapTooltip>
  );
};

export default StatusChip;
