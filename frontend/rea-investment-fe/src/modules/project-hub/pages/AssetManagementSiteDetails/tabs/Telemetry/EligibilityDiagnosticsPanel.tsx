import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import type { ChipProps } from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import Collapse from '@mui/material/Collapse';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import FactCheckIcon from '@mui/icons-material/FactCheck';

import { ApiClient } from '../../../../../../api';
import type { DeviceEligibilityDiagnosticsResponse } from '../../../../../../types/telemetryV2';
import {
  blockingMeta,
  IndicatorChip,
  roleLabel,
  weatherSemanticsLabel
} from '../../../../../../utils/telemetry/deviceDiagnostics';

interface SummaryStripProps {
  data: DeviceEligibilityDiagnosticsResponse;
}

const SummaryStrip: React.FC<SummaryStripProps> = ({ data }) => {
  const chips: Array<{ label: string; color?: ChipProps['color'] }> = [
    { label: `${data.mapped_count}/${data.mappable_count} mapped`, color: 'success' },
    { label: `${data.expected_driving_count} expected driver(s)`, color: 'primary' }
  ];
  if (data.weather_source_count) chips.push({ label: `${data.weather_source_count} weather source(s)`, color: 'info' });
  if (data.meter_count) chips.push({ label: `${data.meter_count} meter(s)` });
  if (data.gateway_count) chips.push({ label: `${data.gateway_count} gateway/logger(s)` });
  if (data.virtual_count) chips.push({ label: `${data.virtual_count} virtual` });
  if (data.ineligible_count) chips.push({ label: `${data.ineligible_count} not eligible` });

  return (
    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
      {chips.map(c => (
        <Chip key={c.label} size="small" label={c.label} color={c.color ?? 'default'} variant="outlined" />
      ))}
    </Box>
  );
};

interface EligibilityDiagnosticsPanelProps {
  siteId: number;
}

export const EligibilityDiagnosticsPanel: React.FC<EligibilityDiagnosticsPanelProps> = ({ siteId }) => {
  const [expanded, setExpanded] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['telemetry-eligibility-diagnostics', siteId],
    queryFn: () => ApiClient.telemetryV2.getSiteEligibilityDiagnostics(siteId),
    enabled: !!siteId
  });

  if (isLoading) {
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={18} />
          <Typography variant="body2" color="text.secondary">
            Loading device eligibility diagnostics…
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (isError || !data) {
    return null;
  }

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6">
          <FactCheckIcon sx={{ mr: 1, verticalAlign: 'middle' }} fontSize="small" />
          Device Eligibility &amp; Diagnostics
        </Typography>
        <Button
          size="small"
          onClick={() => setExpanded(prev => !prev)}
          endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        >
          {expanded ? 'Hide devices' : `Show devices (${data.total_devices})`}
        </Button>
      </Box>

      <SummaryStrip data={data} />

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
        Read-only. Meters, loggers, gateways and weather sensors are mappable for inspection but never drive expected
        performance. Weather semantics are disclosed verbatim and never guessed or converted.
      </Typography>

      {data.indicators.length > 0 && (
        <Box sx={{ mb: 1 }}>
          {data.indicators.map(ind => {
            const meta = blockingMeta[ind.blocking_level] ?? blockingMeta.informational;
            return (
              <Alert key={ind.key} severity={meta.severity} sx={{ mb: 0.5, py: 0 }}>
                <Typography variant="body2" fontWeight="bold" component="span">
                  {ind.label}:
                </Typography>{' '}
                <Typography variant="body2" component="span">
                  {ind.explanation}
                </Typography>
                {ind.recommended_action && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                    Next: {ind.recommended_action}
                  </Typography>
                )}
              </Alert>
            );
          })}
        </Box>
      )}

      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <TableContainer sx={{ mt: 1 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Device</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Mapping</TableCell>
                <TableCell>Weather semantics</TableCell>
                <TableCell>Diagnostics</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.devices.map(device => {
                const semantics = weatherSemanticsLabel(device);
                return (
                  <TableRow key={device.device_id} hover>
                    <TableCell>{device.name ?? `Device ${device.device_id}`}</TableCell>
                    <TableCell>{device.category ?? '—'}</TableCell>
                    <TableCell>{roleLabel(device)}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        variant={device.is_mapped ? 'filled' : 'outlined'}
                        color={device.is_mapped ? 'success' : device.mappable ? 'default' : 'default'}
                        label={device.is_mapped ? 'Mapped' : device.mappable ? 'Unmapped' : 'Not eligible'}
                      />
                    </TableCell>
                    <TableCell>{semantics ?? '—'}</TableCell>
                    <TableCell>
                      {device.indicators.length === 0 ? (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      ) : (
                        device.indicators.map(ind => <IndicatorChip key={ind.key} indicator={ind} />)
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Collapse>
    </Paper>
  );
};

export default EligibilityDiagnosticsPanel;
