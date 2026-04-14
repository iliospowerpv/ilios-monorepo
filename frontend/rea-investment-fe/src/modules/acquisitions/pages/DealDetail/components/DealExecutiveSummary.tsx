import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import { useTheme } from '@mui/material/styles';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BoltIcon from '@mui/icons-material/Bolt';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import BusinessIcon from '@mui/icons-material/Business';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import { Deal, SALES_STAGE_LABELS, SalesStage } from '../../../types';
import type { DealEntityAssignment } from '../../../../../api/entities';

interface DealExecutiveSummaryProps {
  deal: Deal;
  entityAssignments?: DealEntityAssignment[];
}

const formatCurrency = (value?: number): string => {
  if (value === undefined || value === null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const formatSize = (value?: number): string => {
  if (value === undefined || value === null) return '—';
  return `${value.toLocaleString()} kW`;
};

const getStageChipColor = (stage: SalesStage): 'success' | 'warning' | 'error' | 'info' | 'default' => {
  if (['mipa_signed', 'passed'].includes(stage)) return 'success';
  if (['dead'].includes(stage)) return 'error';
  if (['prospect', 'nda_signed'].includes(stage)) return 'info';
  return 'warning';
};

export const DealExecutiveSummary: React.FC<DealExecutiveSummaryProps> = ({ deal, entityAssignments }) => {
  const theme = useTheme();
  const borderColor = theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.12)';

  const location = [deal.city, deal.state].filter(Boolean).join(', ') || deal.address || '—';
  const stageLabel = SALES_STAGE_LABELS[deal.sales_stage] || deal.sales_stage;

  const developerAssignment = entityAssignments?.find(a => a.role === 'developer');
  const developerName = developerAssignment?.entity_name || deal.developer_name;

  return (
    <Box
      sx={{
        mb: 2,
        p: 2,
        border: `1px solid ${borderColor}`,
        borderRadius: 2,
        bgcolor: theme.palette.background.paper
      }}
    >
      <Stack direction="row" alignItems="flex-start" justifyContent="space-between" flexWrap="wrap" gap={2}>
        <Box sx={{ flex: '1 1 auto', minWidth: 200 }}>
          <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 1 }}>
            <Typography variant="h5" fontWeight={600}>
              {deal.name}
            </Typography>
            <Chip
              label={stageLabel}
              color={getStageChipColor(deal.sales_stage)}
              size="small"
              sx={{ fontWeight: 500 }}
            />
            {deal.is_converted && <Chip label="Converted" color="success" size="small" variant="outlined" />}
          </Stack>

          {developerName && (
            <Stack direction="row" alignItems="center" spacing={0.5} sx={{ mb: 0.5 }}>
              <BusinessIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
              <Typography variant="body2" color="text.secondary">
                {developerName}
              </Typography>
            </Stack>
          )}
        </Box>

        <Stack
          direction="row"
          spacing={3}
          divider={<Divider orientation="vertical" flexItem />}
          sx={{ flexWrap: 'wrap', gap: 2 }}
        >
          <Box sx={{ textAlign: 'center', minWidth: 80 }}>
            <Stack direction="row" alignItems="center" justifyContent="center" spacing={0.5}>
              <AttachMoneyIcon sx={{ fontSize: 18, color: 'primary.main' }} />
              <Typography variant="caption" color="text.secondary">
                Pipeline Value
              </Typography>
            </Stack>
            <Typography variant="h6" fontWeight={600}>
              {formatCurrency(deal.pipeline_value)}
            </Typography>
          </Box>

          <Box sx={{ textAlign: 'center', minWidth: 80 }}>
            <Stack direction="row" alignItems="center" justifyContent="center" spacing={0.5}>
              <TrendingUpIcon sx={{ fontSize: 18, color: 'success.main' }} />
              <Typography variant="caption" color="text.secondary">
                Probability
              </Typography>
            </Stack>
            <Typography variant="h6" fontWeight={600}>
              {deal.probability !== undefined && deal.probability !== null ? `${deal.probability}%` : '—'}
            </Typography>
          </Box>

          <Box sx={{ textAlign: 'center', minWidth: 100 }}>
            <Stack direction="row" alignItems="center" justifyContent="center" spacing={0.5}>
              <BoltIcon sx={{ fontSize: 18, color: 'warning.main' }} />
              <Typography variant="caption" color="text.secondary">
                System Size
              </Typography>
            </Stack>
            <Typography variant="h6" fontWeight={600}>
              {formatSize(deal.system_size_ac)} AC
            </Typography>
            {deal.system_size_dc && (
              <Typography variant="caption" color="text.secondary">
                {formatSize(deal.system_size_dc)} DC
              </Typography>
            )}
          </Box>

          <Box sx={{ textAlign: 'center', minWidth: 100 }}>
            <Stack direction="row" alignItems="center" justifyContent="center" spacing={0.5}>
              <LocationOnIcon sx={{ fontSize: 18, color: 'info.main' }} />
              <Typography variant="caption" color="text.secondary">
                Location
              </Typography>
            </Stack>
            <Typography variant="body1" fontWeight={500}>
              {location}
            </Typography>
          </Box>
        </Stack>
      </Stack>
    </Box>
  );
};

export default DealExecutiveSummary;
