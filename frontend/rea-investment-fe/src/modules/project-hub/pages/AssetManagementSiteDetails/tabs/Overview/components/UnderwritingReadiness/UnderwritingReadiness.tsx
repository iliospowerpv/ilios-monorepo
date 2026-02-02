import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import { useTheme } from '@mui/material/styles';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

interface MissingFieldInfo {
  cardId: string;
  cardTitle: string;
  fieldName: string;
  fieldLabel: string;
}

interface UnderwritingReadinessProps {
  missingFields: MissingFieldInfo[];
  totalCriticalCards: number;
  completeCards: number;
}

const FIELD_LABELS: Record<string, string> = {
  name: 'Site Name',
  address: 'Address',
  city: 'City',
  state: 'State',
  system_size_ac: 'System Size (AC)',
  system_size_dc: 'System Size (DC)',
  guarantor: 'Guarantor',
  ownership_structure: 'Ownership Structure',
  placed_in_service_date: 'Placed in Service Date',
  permission_to_operate: 'PTO Date',
  provider: 'Provider',
  ppa_effective_date: 'PPA Effective Date',
  insurance_provider: 'Insurance Provider',
  tax_equity_provider: 'Tax Equity Provider',
  agreement_effective_date: 'Agreement Effective Date',
  production_guarantee: 'Production Guarantee',
  offtaker_name: 'Offtaker Name'
};

const UnderwritingReadiness: React.FC<UnderwritingReadinessProps> = ({
  missingFields,
  totalCriticalCards,
  completeCards
}) => {
  const theme = useTheme();
  const isReady = missingFields.length === 0;
  const topMissing = missingFields.slice(0, 3);

  const borderColor = theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.12)';
  const bgColor = isReady
    ? theme.palette.mode === 'dark'
      ? 'rgba(46, 125, 50, 0.1)'
      : 'rgba(46, 125, 50, 0.05)'
    : theme.palette.mode === 'dark'
      ? 'rgba(211, 47, 47, 0.1)'
      : 'rgba(211, 47, 47, 0.05)';

  return (
    <Box
      sx={{
        mb: 2,
        p: 1.5,
        border: `1px solid ${borderColor}`,
        borderRadius: '8px',
        backgroundColor: bgColor
      }}
    >
      <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
        <Stack direction="row" spacing={1} alignItems="center">
          {isReady ? (
            <CheckCircleIcon fontSize="small" sx={{ color: theme.palette.success.main }} />
          ) : (
            <ErrorIcon fontSize="small" sx={{ color: theme.palette.error.main }} />
          )}
          <Typography variant="subtitle2" fontWeight={600}>
            Underwriting Readiness:
          </Typography>
          <Chip
            label={isReady ? 'Ready' : 'Not Ready'}
            color={isReady ? 'success' : 'error'}
            size="small"
            sx={{ fontWeight: 600 }}
          />
        </Stack>

        <Typography variant="body2" color="text.secondary">
          {completeCards}/{totalCriticalCards} critical sections complete
        </Typography>

        {!isReady && topMissing.length > 0 && (
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Typography variant="body2" color="text.secondary">
              Missing:
            </Typography>
            {topMissing.map(field => (
              <Tooltip
                key={`${field.cardId}-${field.fieldName}`}
                title={`${field.cardTitle}: ${FIELD_LABELS[field.fieldName] || field.fieldName}`}
                arrow
              >
                <Chip
                  label={FIELD_LABELS[field.fieldName] || field.fieldName}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: '0.75rem' }}
                />
              </Tooltip>
            ))}
            {missingFields.length > 3 && (
              <Typography variant="body2" color="text.secondary">
                +{missingFields.length - 3} more
              </Typography>
            )}
          </Stack>
        )}
      </Stack>
    </Box>
  );
};

export default UnderwritingReadiness;
