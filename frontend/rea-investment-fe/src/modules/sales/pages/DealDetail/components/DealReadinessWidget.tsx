import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import { useTheme } from '@mui/material/styles';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { Deal } from '../../../types';

interface DealReadinessWidgetProps {
  deal: Deal;
}

const HANDOFF_REQUIRED_FIELDS: { field: keyof Deal; label: string }[] = [
  { field: 'address', label: 'Address' },
  { field: 'state', label: 'State' },
  { field: 'system_size_ac', label: 'System Size (AC)' },
  { field: 'system_size_dc', label: 'System Size (DC)' },
  { field: 'utility_rate', label: 'Utility Rate' },
  { field: 'ownership_structure', label: 'Ownership Structure' },
  { field: 'offtaker_name', label: 'Offtaker Name' }
];

export const DealReadinessWidget: React.FC<DealReadinessWidgetProps> = ({ deal }) => {
  const theme = useTheme();

  const missingFields = HANDOFF_REQUIRED_FIELDS.filter(({ field }) => {
    const value = deal[field];
    return value === null || value === undefined || value === '';
  });

  const isReady = missingFields.length === 0;
  const completedCount = HANDOFF_REQUIRED_FIELDS.length - missingFields.length;
  const totalCount = HANDOFF_REQUIRED_FIELDS.length;
  const percentage = Math.round((completedCount / totalCount) * 100);

  const borderColor = isReady ? theme.palette.success.main : theme.palette.warning.main;
  const successBg = theme.palette.mode === 'dark' ? 'rgba(46, 125, 50, 0.1)' : 'rgba(46, 125, 50, 0.05)';
  const warningBg = theme.palette.mode === 'dark' ? 'rgba(237, 108, 2, 0.1)' : 'rgba(237, 108, 2, 0.05)';
  const bgColor = isReady ? successBg : warningBg;

  return (
    <Box
      sx={{
        mb: 2,
        p: 2,
        border: `1px solid ${borderColor}`,
        borderRadius: 2,
        bgcolor: bgColor
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={2}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          {isReady ? (
            <CheckCircleOutlineIcon sx={{ color: 'success.main', fontSize: 28 }} />
          ) : (
            <WarningAmberIcon sx={{ color: 'warning.main', fontSize: 28 }} />
          )}
          <Box>
            <Typography variant="subtitle1" fontWeight={600}>
              Conversion Readiness
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {isReady
                ? 'All required fields complete - ready to convert to project'
                : `${missingFields.length} missing field${missingFields.length > 1 ? 's' : ''} before conversion`}
            </Typography>
          </Box>
        </Stack>

        <Stack direction="row" alignItems="center" spacing={2}>
          <Chip
            label={`${percentage}% Complete`}
            color={isReady ? 'success' : 'warning'}
            variant="outlined"
            size="small"
          />
          <Typography variant="body2" color="text.secondary">
            {completedCount} / {totalCount} fields
          </Typography>
        </Stack>
      </Stack>

      {!isReady && missingFields.length > 0 && (
        <Box sx={{ mt: 1.5, pt: 1.5, borderTop: `1px solid ${borderColor}` }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            Missing fields:
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" gap={0.5}>
            {missingFields.slice(0, 5).map(({ label }) => (
              <Tooltip key={label} title={`Required for conversion`}>
                <Chip label={label} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
              </Tooltip>
            ))}
            {missingFields.length > 5 && (
              <Chip
                label={`+${missingFields.length - 5} more`}
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.7rem' }}
              />
            )}
          </Stack>
        </Box>
      )}
    </Box>
  );
};

export default DealReadinessWidget;
