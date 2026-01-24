import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import { useTheme } from '@mui/material/styles';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BoltIcon from '@mui/icons-material/Bolt';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import BusinessIcon from '@mui/icons-material/Business';
import dayjs from 'dayjs';
import formatFloatValue from '../../../../../../../../utils/formatters/formatFloatValue';

interface ExecutiveSummaryProps {
  siteLevelDetails: {
    name?: string | null;
    project_id?: string | null;
    status?: string | null;
    address?: string | null;
    city?: string | null;
    state?: string | null;
    zip_code?: string | null;
    system_size_dc?: number | null;
    system_size_ac?: number | null;
  } | null;
  keyDates: {
    permission_to_operate?: string | null;
    placed_in_service_date?: string | null;
    financial_close_date?: string | null;
  } | null;
  interconnection: {
    provider?: string | null;
  } | null;
}

const getStatusColor = (status: string | null | undefined): 'success' | 'warning' | 'error' | 'default' => {
  switch (status?.toLowerCase()) {
    case 'placed in service':
      return 'success';
    case 'construction':
      return 'warning';
    case 'decommissioned':
    case 'sold':
      return 'error';
    default:
      return 'default';
  }
};

const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '—';
  const parsed = dayjs(dateStr, 'YYYY-MM-DD', true);
  return parsed.isValid() ? parsed.format('MM/DD/YYYY') : '—';
};

const ExecutiveSummary: React.FC<ExecutiveSummaryProps> = ({ siteLevelDetails, keyDates, interconnection }) => {
  const theme = useTheme();
  const borderColor = theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.12)';

  const name = siteLevelDetails?.name || '—';
  const projectId = siteLevelDetails?.project_id || '—';
  const status = siteLevelDetails?.status;
  const city = siteLevelDetails?.city || '';
  const state = siteLevelDetails?.state || '';
  const address = siteLevelDetails?.address || '';
  const location = [city, state].filter(Boolean).join(', ') || address || '—';
  const sizeDC = siteLevelDetails?.system_size_dc;
  const sizeAC = siteLevelDetails?.system_size_ac;
  const utilityProvider = interconnection?.provider || '—';
  const ptoDate = keyDates?.permission_to_operate;
  const codDate = keyDates?.placed_in_service_date;
  const financialClose = keyDates?.financial_close_date;

  return (
    <Box
      sx={{
        mb: 2,
        p: 2,
        border: `1px solid ${borderColor}`,
        borderRadius: '8px',
        backgroundColor: theme.palette.background.paper
      }}
    >
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={2}
        alignItems={{ xs: 'flex-start', md: 'center' }}
        justifyContent="space-between"
      >
        <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
          <Box>
            <Typography variant="h6" fontWeight={700} sx={{ mb: 0.5 }}>
              {name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Project ID: {projectId}
            </Typography>
          </Box>
          {status && <Chip label={status} color={getStatusColor(status)} size="small" sx={{ fontWeight: 600 }} />}
        </Stack>
      </Stack>

      <Divider sx={{ my: 1.5 }} />

      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={{ xs: 1, sm: 3 }}
        flexWrap="wrap"
        alignItems={{ xs: 'flex-start', sm: 'center' }}
      >
        <Stack direction="row" spacing={0.5} alignItems="center">
          <LocationOnIcon fontSize="small" color="action" />
          <Typography variant="body2">{location}</Typography>
        </Stack>

        <Stack direction="row" spacing={0.5} alignItems="center">
          <BoltIcon fontSize="small" color="action" />
          <Typography variant="body2">
            {sizeDC ? `${formatFloatValue(sizeDC)} kW DC` : '— kW DC'} /{' '}
            {sizeAC ? `${formatFloatValue(sizeAC)} kW AC` : '— kW AC'}
          </Typography>
        </Stack>

        <Stack direction="row" spacing={0.5} alignItems="center">
          <BusinessIcon fontSize="small" color="action" />
          <Typography variant="body2">Utility: {utilityProvider}</Typography>
        </Stack>
      </Stack>

      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={{ xs: 1, sm: 3 }}
        sx={{ mt: 1 }}
        flexWrap="wrap"
        alignItems={{ xs: 'flex-start', sm: 'center' }}
      >
        <Stack direction="row" spacing={0.5} alignItems="center">
          <CalendarTodayIcon fontSize="small" color="action" />
          <Typography variant="body2">PTO: {formatDate(ptoDate)}</Typography>
        </Stack>

        <Typography variant="body2">COD: {formatDate(codDate)}</Typography>

        {financialClose && <Typography variant="body2">Fin Close: {formatDate(financialClose)}</Typography>}
      </Stack>
    </Box>
  );
};

export default ExecutiveSummary;
