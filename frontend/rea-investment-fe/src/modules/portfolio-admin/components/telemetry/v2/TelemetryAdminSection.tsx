import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Snackbar from '@mui/material/Snackbar';
import Typography from '@mui/material/Typography';
import SensorsIcon from '@mui/icons-material/Sensors';

import { useAuth } from '../../../../../contexts/auth/auth';
import { useLicensedProviders, useTelemetryAdminMutations } from '../../../../../hooks/telemetryV2';
import type { ProviderAccount } from '../../../../../types/telemetryV2';
import { AddLicensedProviderDialog } from './AddLicensedProviderDialog';
import { AddProviderAccountDialog } from './AddProviderAccountDialog';
import { LicensedProviderTypesPanel } from './LicensedProviderTypesPanel';
import { ProviderAccountDrawer } from './ProviderAccountDrawer';
import { ProviderAccountsTable } from './ProviderAccountsTable';
import { RotateCredentialsDialog } from './RotateCredentialsDialog';

interface TelemetryAdminSectionProps {
  companyId: number;
}

const useTelemetryAdminPermission = (): boolean => {
  const { user } = useAuth();
  if (!user) return false;
  if (user.is_system_user) return true;
  const perms = user.role?.permissions ?? {};
  // Backend telemetry_admin_required permits the new Telemetry.admin key
  // and falls back to Settings Page.edit. Mirror that gating in the UI so
  // existing settings administrators don't silently lose write access.
  const telemetryAdmin = (perms as Record<string, { admin?: boolean }>)['Telemetry']?.admin;
  if (telemetryAdmin) return true;
  const settingsEdit = (perms as Record<string, { edit?: boolean }>)['Settings Page']?.edit;
  return Boolean(settingsEdit);
};

type Snack = { severity: 'success' | 'error' | 'info' | 'warning'; message: string } | null;

export const TelemetryAdminSection: React.FC<TelemetryAdminSectionProps> = ({ companyId }) => {
  const canEdit = useTelemetryAdminPermission();
  const { data: licensedData } = useLicensedProviders(companyId);
  const hasLicensedProviders = (licensedData?.items ?? []).length > 0;

  const mutations = useTelemetryAdminMutations(companyId);

  const [addLicenseOpen, setAddLicenseOpen] = React.useState(false);
  const [addAccountOpen, setAddAccountOpen] = React.useState(false);
  const [rotateAccount, setRotateAccount] = React.useState<ProviderAccount | null>(null);
  const [drawerAccount, setDrawerAccount] = React.useState<ProviderAccount | null>(null);
  const [pendingTestId, setPendingTestId] = React.useState<number | null>(null);
  const [pendingSyncId, setPendingSyncId] = React.useState<number | null>(null);
  const [pendingArchiveId, setPendingArchiveId] = React.useState<number | null>(null);
  const [snack, setSnack] = React.useState<Snack>(null);

  const showSnack = (severity: 'success' | 'error' | 'info' | 'warning', message: string) =>
    setSnack({ severity, message });

  const errorMessage = (err: unknown, fallback: string): string => {
    const e = err as Error & { response?: { data?: { detail?: string } } };
    return e?.response?.data?.detail || e?.message || fallback;
  };

  const handleTest = (account: ProviderAccount) => {
    setPendingTestId(account.id);
    mutations.testAccount.mutate(account.id, {
      onSuccess: data => {
        setPendingTestId(null);
        if (data.success) {
          showSnack('success', `Credentials verified for ${account.name}.`);
        } else {
          showSnack('warning', data.message || 'Credential test failed.');
        }
      },
      onError: err => {
        setPendingTestId(null);
        showSnack('error', errorMessage(err, 'Credential test failed.'));
      }
    });
  };

  const handleSyncSites = (account: ProviderAccount) => {
    setPendingSyncId(account.id);
    mutations.syncSites.mutate(account.id, {
      onSuccess: data => {
        setPendingSyncId(null);
        showSnack(
          data.error ? 'warning' : 'success',
          data.error
            ? `Sync completed with errors: ${data.error}`
            : `Sync complete — ${data.seen_count} site${data.seen_count === 1 ? '' : 's'} seen, ${data.new_count} new.`
        );
      },
      onError: err => {
        setPendingSyncId(null);
        showSnack('error', errorMessage(err, 'Sync failed.'));
      }
    });
  };

  const handleArchive = (account: ProviderAccount) => {
    setPendingArchiveId(account.id);
    mutations.archiveAccount.mutate(account.id, {
      onSuccess: () => {
        setPendingArchiveId(null);
        showSnack('success', `${account.name} archived. Stored credentials are retained.`);
        if (drawerAccount?.id === account.id) {
          setDrawerAccount(null);
        }
      },
      onError: err => {
        setPendingArchiveId(null);
        showSnack('error', errorMessage(err, 'Archive failed.'));
      }
    });
  };

  return (
    <>
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <SensorsIcon color="primary" />
            <Typography variant="h6">Telemetry Administration</Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            License telemetry provider types for this company, manage provider accounts and their stored credentials,
            and review external site inventory.{' '}
            {!canEdit &&
              'You have read-only access; mutation actions are hidden because you do not have telemetry administrator permissions.'}
          </Typography>

          <LicensedProviderTypesPanel
            companyId={companyId}
            canEdit={canEdit}
            onAddLicense={() => setAddLicenseOpen(true)}
            onError={msg => showSnack('error', msg)}
          />

          <ProviderAccountsTable
            companyId={companyId}
            canEdit={canEdit}
            hasLicensedProviders={hasLicensedProviders}
            onAddAccount={() => setAddAccountOpen(true)}
            onView={setDrawerAccount}
            onTest={handleTest}
            onSyncSites={handleSyncSites}
            onRotate={setRotateAccount}
            onArchive={handleArchive}
            pendingTestId={pendingTestId}
            pendingSyncId={pendingSyncId}
            pendingArchiveId={pendingArchiveId}
          />
        </CardContent>
      </Card>

      <AddLicensedProviderDialog companyId={companyId} open={addLicenseOpen} onClose={() => setAddLicenseOpen(false)} />

      <AddProviderAccountDialog
        companyId={companyId}
        open={addAccountOpen}
        onClose={() => setAddAccountOpen(false)}
        onCreated={() =>
          showSnack('info', 'Provider account saved. Credentials are not yet verified — click Test Credentials.')
        }
      />

      <RotateCredentialsDialog
        companyId={companyId}
        account={rotateAccount}
        open={!!rotateAccount}
        onClose={() => setRotateAccount(null)}
      />

      <ProviderAccountDrawer
        companyId={companyId}
        account={drawerAccount}
        open={!!drawerAccount}
        onClose={() => setDrawerAccount(null)}
        canEdit={canEdit}
        onTest={handleTest}
        onSyncSites={handleSyncSites}
        onRotate={setRotateAccount}
        onArchive={handleArchive}
        pendingTestId={pendingTestId}
        pendingSyncId={pendingSyncId}
        pendingArchiveId={pendingArchiveId}
      />

      <Snackbar
        open={!!snack}
        autoHideDuration={6000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        {snack ? (
          <Alert severity={snack.severity} onClose={() => setSnack(null)}>
            {snack.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </>
  );
};
