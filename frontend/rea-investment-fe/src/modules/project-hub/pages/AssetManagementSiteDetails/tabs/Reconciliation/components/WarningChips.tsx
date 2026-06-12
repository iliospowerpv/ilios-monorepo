import React from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { BootstrapTooltip } from '../../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import { warningMeta, PLACEHOLDER } from '../utils';

interface WarningChipsProps {
  warnings: string[];
}

export const WarningChips: React.FC<WarningChipsProps> = ({ warnings }) => {
  if (!warnings || warnings.length === 0) {
    return (
      <Typography variant="body2" color="text.disabled">
        {PLACEHOLDER}
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }} data-testid="reconciliation-warning-chips">
      {warnings.map(warning => {
        const meta = warningMeta(warning);
        return (
          <BootstrapTooltip key={warning} title={meta.description} placement="top">
            <Chip icon={<WarningAmberIcon />} label={meta.label} color="warning" size="small" variant="outlined" />
          </BootstrapTooltip>
        );
      })}
    </Box>
  );
};

export default WarningChips;
