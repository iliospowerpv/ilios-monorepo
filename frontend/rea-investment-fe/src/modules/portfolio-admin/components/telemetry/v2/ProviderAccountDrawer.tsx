import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import Skeleton from '@mui/material/Skeleton';
import Stack from '@mui/material/Stack';
import Tab from '@mui/material/Tab';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tabs from '@mui/material/Tabs';
import Typography from '@mui/material/Typography';
import CloseIcon from '@mui/icons-material/Close';

import type { ProviderAccount } from '../../../../../types/telemetryV2';
import { useExternalSites, useProviderAccountDetail } from '../../../../../hooks/telemetryV2';
import { CredentialChip, LifecycleChip, SyncChip } from './StatusChips';

interface ProviderAccountDrawerProps {
  companyId: number;
  account: ProviderAccount | null;
  open: boolean;
  onClose: () => void;
  canEdit: boolean;
  onTest: (account: ProviderAccount) => void;
  onSyncSites: (account: ProviderAccount) => void;
  onRotate: (account: ProviderAccount) => void;
  onArchive: (account: ProviderAccount) => void;
  pendingTestId?: number | null;
  pendingSyncId?: number | null;
  pendingArchiveId?: number | null;
}

const formatTimestamp = (value: string | null): string => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};

export const ProviderAccountDrawer: React.FC<ProviderAccountDrawerProps> = ({
  companyId,
  account,
  open,
  onClose,
  canEdit,
  onTest,
  onSyncSites,
  onRotate,
  onArchive,
  pendingTestId,
  pendingSyncId,
  pendingArchiveId
}) => {
  const accountId = account?.id ?? null;
  const { data: detail, isLoading: detailLoading } = useProviderAccountDetail(companyId, accountId, {
    enabled: open && !!accountId
  });
  const current = detail ?? account;
  const [tab, setTab] = React.useState(0);

  React.useEffect(() => {
    if (open) setTab(0);
  }, [open, accountId]);

  const { data: externalSites, isLoading: externalSitesLoading } = useExternalSites(accountId, {
    enabled: open && tab === 1 && !!accountId
  });

  const isTesting = !!current && pendingTestId === current.id;
  const isSyncing = !!current && pendingSyncId === current.id;
  const isArchiving = !!current && pendingArchiveId === current.id;
  const syncDisabled = !current || current.credential_status !== 'verified' || current.status !== 'active';

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: { xs: '100%', sm: 560 },
          backgroundColor: 'background.paper',
          color: 'text.primary'
        }
      }}
    >
      {!current ? (
        <Box sx={{ p: 2 }}>
          <Skeleton variant="rectangular" height={240} />
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <Box
            sx={{
              p: 2,
              display: 'flex',
              alignItems: 'flex-start',
              gap: 1,
              borderBottom: theme => `1px solid ${theme.palette.divider}`
            }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="subtitle1" fontWeight={600}>
                {current.display_name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {current.name}
                {current.external_account_label ? ` • ${current.external_account_label}` : ''}
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <LifecycleChip value={current.status} />
                <CredentialChip value={current.credential_status} />
                <SyncChip value={current.last_sync_status} />
              </Stack>
            </Box>
            <IconButton size="small" onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Box>

          <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ px: 2 }}>
            <Tab label="Configuration" />
            <Tab label={`External Sites (${current.external_site_count})`} />
            <Tab label={`Project / Site Mappings (${current.active_mapping_count})`} />
          </Tabs>

          <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
            {detailLoading && <Skeleton variant="rectangular" height={120} />}

            {tab === 0 && (
              <Stack spacing={2}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Provider
                  </Typography>
                  <Typography variant="body2">
                    {current.display_name} ({current.provider_key})
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Credentials fingerprint
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {current.credentials_fingerprint || '—'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Saved values are write-only and are never displayed.
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Last successful test
                  </Typography>
                  <Typography variant="body2">{formatTimestamp(current.last_success_at)}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Last error
                  </Typography>
                  <Typography variant="body2" color={current.last_error_message ? 'error' : 'inherit'}>
                    {current.last_error_message || '—'}
                  </Typography>
                  {current.last_error_at && (
                    <Typography variant="caption" color="text.secondary">
                      at {formatTimestamp(current.last_error_at)}
                    </Typography>
                  )}
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Created / updated
                  </Typography>
                  <Typography variant="body2">
                    {formatTimestamp(current.created_at)} / {formatTimestamp(current.updated_at)}
                  </Typography>
                </Box>
                {canEdit && (
                  <>
                    <Divider />
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      <Button
                        variant="outlined"
                        onClick={() => onTest(current)}
                        disabled={current.status !== 'active' || isTesting}
                      >
                        {isTesting ? 'Testing…' : 'Test Credentials'}
                      </Button>
                      <Button
                        variant="outlined"
                        onClick={() => onSyncSites(current)}
                        disabled={syncDisabled || isSyncing}
                      >
                        {isSyncing ? 'Syncing…' : 'Sync Sites'}
                      </Button>
                      <Button variant="outlined" onClick={() => onRotate(current)}>
                        Rotate Credentials
                      </Button>
                      <Button
                        variant="outlined"
                        color="error"
                        onClick={() => onArchive(current)}
                        disabled={current.is_archived || isArchiving}
                      >
                        {current.is_archived ? 'Archived' : isArchiving ? 'Archiving…' : 'Archive'}
                      </Button>
                    </Stack>
                    {current.credential_status !== 'verified' && current.status === 'active' && (
                      <Alert severity="warning">
                        Credentials have not been verified. <strong>Click Test Credentials</strong> to verify before
                        syncing sites.
                      </Alert>
                    )}
                  </>
                )}
              </Stack>
            )}

            {tab === 1 && (
              <Stack spacing={1}>
                <Typography variant="body2" color="text.secondary">
                  External sites synced from the provider. Counts are computed server-side and are scoped to this
                  account only.
                </Typography>
                {externalSitesLoading ? (
                  <Skeleton variant="rectangular" height={120} />
                ) : !externalSites || externalSites.items.length === 0 ? (
                  <Alert severity="info">
                    No external sites yet. Run <strong>Sync Sites</strong> after the credential test succeeds.
                  </Alert>
                ) : (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>External ID</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Last seen</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {externalSites.items.map(site => (
                        <TableRow key={site.id}>
                          <TableCell sx={{ fontFamily: 'monospace' }}>{site.external_site_id}</TableCell>
                          <TableCell>{site.external_site_name || '—'}</TableCell>
                          <TableCell>{site.sync_status}</TableCell>
                          <TableCell>{formatTimestamp(site.last_seen_at)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </Stack>
            )}

            {tab === 2 && (
              <Stack spacing={2}>
                <Alert severity="info">
                  Project/Site mappings are managed in the project Telemetry tab on each project page.{' '}
                  {current.active_mapping_count} active mapping
                  {current.active_mapping_count === 1 ? '' : 's'} currently use this account.
                </Alert>
                <Typography variant="body2" color="text.secondary">
                  This view is read-only in this release. Use the project Telemetry wizard to add, edit, or remove site
                  mappings.
                </Typography>
              </Stack>
            )}
          </Box>
        </Box>
      )}
    </Drawer>
  );
};
