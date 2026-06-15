import React from 'react';
import Chip from '@mui/material/Chip';
import { BootstrapTooltip } from '../../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import { statusMeta } from '../utils';

interface StatusChipProps {
  status: string;
  /** Backend-supplied label override (`status_label`); falls back to STATUS_META. */
  label?: string | null;
  /** Backend-supplied explanation override (`status_explanation`); falls back to STATUS_META. */
  description?: string | null;
}

export const StatusChip: React.FC<StatusChipProps> = ({ status, label, description }) => {
  const meta = statusMeta(status);
  return (
    <BootstrapTooltip title={description || meta.description} placement="top">
      <Chip
        label={label || meta.label}
        color={meta.color}
        size="small"
        variant="outlined"
        data-testid="reconciliation-status-chip"
      />
    </BootstrapTooltip>
  );
};

export default StatusChip;
