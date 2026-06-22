import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import type { ChipProps } from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';

import { ApiClient } from '../../../../../../api';
import type { WeatherDeviceMapping } from '../../../../../../types/weather';

interface WeatherDeclarationHistoryDialogProps {
  open: boolean;
  onClose: () => void;
  siteId: number;
  deviceId: number;
  deviceName?: string | null;
}

const statusColor = (status: string | null): ChipProps['color'] => {
  switch (status) {
    case 'active':
      return 'success';
    case 'draft':
      return 'info';
    case 'superseded':
      return 'default';
    default:
      return 'default';
  }
};

const formatWhen = (iso: string | null): string => {
  if (!iso) return '—';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
};

const semanticsSummary = (m: WeatherDeviceMapping): string => {
  const parts = [`plane: ${m.irradiance_plane}`, `temp: ${m.temperature_type}`, `cal: ${m.calibration_status}`];
  return parts.join(', ');
};

/**
 * Read-only append-only declaration history (lineage) for one device. Each row
 * is an immutable governed declaration; the chain is never rewritten, and this
 * view performs no writes — it only discloses the draft → active → superseded
 * lineage exactly as recorded.
 */
export const WeatherDeclarationHistoryDialog: React.FC<WeatherDeclarationHistoryDialogProps> = ({
  open,
  onClose,
  siteId,
  deviceId,
  deviceName
}) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['weather-device-history', siteId, deviceId],
    queryFn: () => ApiClient.weather.listDeviceMappingHistory(siteId, deviceId),
    enabled: open && !!siteId && !!deviceId
  });

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Declaration history — {deviceName ?? `Device ${deviceId}`}</DialogTitle>
      <DialogContent dividers>
        {isLoading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 2 }}>
            <CircularProgress size={18} />
            <Typography variant="body2" color="text.secondary">
              Loading declaration history…
            </Typography>
          </Box>
        )}
        {isError && <Alert severity="error">Failed to load declaration history.</Alert>}
        {!isLoading && !isError && (!data || data.length === 0) && (
          <Alert severity="info">No weather-semantics declarations recorded for this device yet.</Alert>
        )}
        {!isLoading && !isError && data && data.length > 0 && (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Basis</TableCell>
                  <TableCell>Semantics</TableCell>
                  <TableCell>Declared</TableCell>
                  <TableCell>Activated</TableCell>
                  <TableCell>Lineage</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.map(m => (
                  <TableRow key={m.id} hover>
                    <TableCell>#{m.id}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={statusColor(m.declaration_status)}
                        variant={m.declaration_status === 'active' ? 'filled' : 'outlined'}
                        label={m.declaration_status ?? 'ungoverned'}
                      />
                      {m.needs_re_review && (
                        <Chip size="small" color="warning" variant="outlined" label="Needs re-review" sx={{ ml: 0.5 }} />
                      )}
                    </TableCell>
                    <TableCell>{m.declaration_basis ?? '—'}</TableCell>
                    <TableCell>
                      <Typography variant="caption">{semanticsSummary(m)}</Typography>
                    </TableCell>
                    <TableCell>{formatWhen(m.declared_at)}</TableCell>
                    <TableCell>{formatWhen(m.activated_at)}</TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {m.supersedes_mapping_id ? `supersedes #${m.supersedes_mapping_id}` : ''}
                        {m.supersedes_mapping_id && m.superseded_by_mapping_id ? ' · ' : ''}
                        {m.superseded_by_mapping_id ? `superseded by #${m.superseded_by_mapping_id}` : ''}
                        {!m.supersedes_mapping_id && !m.superseded_by_mapping_id ? '—' : ''}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default WeatherDeclarationHistoryDialog;
