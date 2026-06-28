import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Snackbar from '@mui/material/Snackbar';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';
import AddIcon from '@mui/icons-material/Add';
import CloudOutlinedIcon from '@mui/icons-material/CloudOutlined';

import {
  useWeatherProviders,
  useWeatherProviderAccounts,
  useWeatherProviderAccountMutations
} from '../../../../hooks/weatherProvider';
import { useTelemetryAdminPermission } from '../../../../hooks/useTelemetryAdminPermission';
import type { WeatherProviderAccountResponse } from '../../../../types/weather';
import { AddWeatherProviderAccountDialog } from './AddWeatherProviderAccountDialog';

type Snack = { severity: 'success' | 'error' | 'info' | 'warning'; message: string } | null;

const errorMessage = (err: unknown, fallback: string): string => {
  const e = err as Error & { response?: { data?: { detail?: string } } };
  return e?.response?.data?.detail || e?.message || fallback;
};

const fmtInstant = (raw: string | null | undefined): string => {
  if (!raw) return 'Never';
  const hasTz = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(raw);
  const d = new Date(hasTz ? raw : `${raw}Z`);
  return Number.isNaN(d.getTime()) ? 'Unavailable' : d.toLocaleString();
};

const statusColor = (status: string): 'success' | 'warning' | 'default' => {
  if (status === 'active') return 'success';
  if (status === 'paused') return 'warning';
  return 'default';
};

const credentialColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
  if (status === 'verified') return 'success';
  if (status === 'failed' || status === 'invalid') return 'error';
  if (status === 'untested') return 'warning';
  return 'default';
};

interface WeatherProviderAdminSectionProps {
  companyId: number;
}

/**
 * D4 — company-level weather provider administration.
 *
 * Mirrors TelemetryAdminSection but for the context-only weather framework. It
 * shows the read-only provider catalog (including disabled providers, so the
 * operator can see what exists), the company's weather provider accounts, and
 * write actions (add / test / archive) gated to telemetry admins. There is no
 * hard delete — archiving is a status update. External weather is always
 * context only and never drives expected math; that is stated up front.
 */
export const WeatherProviderAdminSection: React.FC<WeatherProviderAdminSectionProps> = ({ companyId }) => {
  const canEdit = useTelemetryAdminPermission();
  const { data: catalog } = useWeatherProviders({ includeDisabled: true });
  const { data: accountData, isLoading: isLoadingAccounts } = useWeatherProviderAccounts(companyId);
  const { testAccount, archiveAccount } = useWeatherProviderAccountMutations(companyId);

  const [addOpen, setAddOpen] = React.useState(false);
  const [pendingTestId, setPendingTestId] = React.useState<number | null>(null);
  const [pendingArchiveId, setPendingArchiveId] = React.useState<number | null>(null);
  const [snack, setSnack] = React.useState<Snack>(null);

  const showSnack = (severity: NonNullable<Snack>['severity'], message: string) => setSnack({ severity, message });

  const providers = catalog?.items ?? [];
  const accounts = accountData?.items ?? [];

  // Admins only — non-admins never see the credential/account surface.
  if (!canEdit) return null;

  const handleTest = (account: WeatherProviderAccountResponse) => {
    setPendingTestId(account.id);
    testAccount.mutate(account.id, {
      onSuccess: data => {
        setPendingTestId(null);
        showSnack(data.success ? 'success' : 'warning', data.message || 'Credential test complete.');
      },
      onError: err => {
        setPendingTestId(null);
        showSnack('error', errorMessage(err, 'Credential test failed.'));
      }
    });
  };

  const handleArchive = (account: WeatherProviderAccountResponse) => {
    setPendingArchiveId(account.id);
    archiveAccount.mutate(account.id, {
      onSuccess: () => {
        setPendingArchiveId(null);
        showSnack('success', `Archived ${account.display_name}.`);
      },
      onError: err => {
        setPendingArchiveId(null);
        showSnack('error', errorMessage(err, 'Failed to archive account.'));
      }
    });
  };

  return (
    <Card sx={{ mt: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CloudOutlinedIcon />
            <Typography variant="h6">Weather Providers</Typography>
          </Box>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setAddOpen(true)}>
            Add Account
          </Button>
        </Box>

        <Alert severity="info" sx={{ mb: 2 }}>
          External weather is imported as <strong>context only</strong>. It is never used for expected-production or
          loss math, and is never converted to plane-of-array irradiance or cell temperature.
        </Alert>

        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Provider catalog
        </Typography>
        {providers.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            No weather providers are registered.
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
            {providers.map(p => (
              <Tooltip
                key={p.provider_key}
                title={`${p.requires_credentials ? 'Requires credentials' : 'Keyless'}${
                  p.licensing_class ? ` · ${p.licensing_class}` : ''
                }`}
              >
                <Chip
                  label={p.display_name}
                  color={p.is_enabled ? 'primary' : 'default'}
                  variant={p.is_enabled ? 'filled' : 'outlined'}
                  size="small"
                />
              </Tooltip>
            ))}
          </Box>
        )}

        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Accounts
        </Typography>
        {isLoadingAccounts ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1 }}>
            <CircularProgress size={18} />
            <Typography variant="body2" color="text.secondary">
              Loading accounts…
            </Typography>
          </Box>
        ) : accounts.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No weather provider accounts yet. Click <strong>Add Account</strong> to create one.
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Account</TableCell>
                  <TableCell>Provider</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Credentials</TableCell>
                  <TableCell>Last success</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {accounts.map(account => (
                  <TableRow key={account.id}>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {account.display_name}
                      </Typography>
                      {account.external_account_label && (
                        <Typography variant="caption" color="text.secondary">
                          {account.external_account_label}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{account.provider_key}</TableCell>
                    <TableCell>
                      <Chip size="small" label={account.status} color={statusColor(account.status)} />
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        variant="outlined"
                        label={account.credential_status}
                        color={credentialColor(account.credential_status)}
                      />
                    </TableCell>
                    <TableCell>{fmtInstant(account.last_success_at)}</TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        onClick={() => handleTest(account)}
                        disabled={
                          !account.has_stored_credentials ||
                          account.status === 'archived' ||
                          pendingTestId === account.id
                        }
                      >
                        {pendingTestId === account.id ? 'Testing…' : 'Test'}
                      </Button>
                      <Button
                        size="small"
                        color="warning"
                        onClick={() => handleArchive(account)}
                        disabled={account.status === 'archived' || pendingArchiveId === account.id}
                      >
                        {pendingArchiveId === account.id ? 'Archiving…' : 'Archive'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>

      <AddWeatherProviderAccountDialog
        companyId={companyId}
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={() => showSnack('success', 'Weather provider account created.')}
      />

      <Snackbar
        open={!!snack}
        autoHideDuration={6000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        {snack ? (
          <Alert severity={snack.severity} onClose={() => setSnack(null)} variant="filled">
            {snack.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Card>
  );
};

export default WeatherProviderAdminSection;
