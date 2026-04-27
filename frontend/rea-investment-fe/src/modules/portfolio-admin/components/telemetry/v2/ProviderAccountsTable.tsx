import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import IconButton from '@mui/material/IconButton';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Skeleton from '@mui/material/Skeleton';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import AddIcon from '@mui/icons-material/Add';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

import type { ProviderAccount } from '../../../../../types/telemetryV2';
import { useProviderAccounts } from '../../../../../hooks/telemetryV2';
import { CredentialChip, LifecycleChip, SyncChip } from './StatusChips';

interface ProviderAccountsTableProps {
  companyId: number;
  canEdit: boolean;
  hasLicensedProviders: boolean;
  onAddAccount: () => void;
  onView: (account: ProviderAccount) => void;
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

export const ProviderAccountsTable: React.FC<ProviderAccountsTableProps> = ({
  companyId,
  canEdit,
  hasLicensedProviders,
  onAddAccount,
  onView,
  onTest,
  onSyncSites,
  onRotate,
  onArchive,
  pendingTestId,
  pendingSyncId,
  pendingArchiveId
}) => {
  const { data, isLoading, error } = useProviderAccounts(companyId);
  const [menuAnchor, setMenuAnchor] = React.useState<HTMLElement | null>(null);
  const [menuAccount, setMenuAccount] = React.useState<ProviderAccount | null>(null);

  const accounts = data?.items ?? [];

  const openMenu = (event: React.MouseEvent<HTMLElement>, account: ProviderAccount) => {
    setMenuAnchor(event.currentTarget);
    setMenuAccount(account);
  };

  const closeMenu = () => {
    setMenuAnchor(null);
    setMenuAccount(null);
  };

  const renderActions = (account: ProviderAccount) => {
    const isTesting = pendingTestId === account.id;
    const isSyncing = pendingSyncId === account.id;
    const isArchiving = pendingArchiveId === account.id;
    const syncDisabled = account.credential_status !== 'verified' || account.status !== 'active';
    const syncTooltip = !canEdit
      ? 'Read-only — telemetry admin permission required'
      : account.status !== 'active'
        ? 'Account is not active'
        : account.credential_status !== 'verified'
          ? 'Test credentials successfully before syncing sites'
          : 'Sync sites from the provider';

    return (
      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
        <Tooltip title="View account details">
          <span>
            <IconButton size="small" onClick={() => onView(account)}>
              <OpenInNewIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
        {canEdit && (
          <>
            <Tooltip
              title={
                account.status !== 'active' ? 'Account is not active' : 'Test stored credentials against the provider'
              }
            >
              <span>
                <Button
                  size="small"
                  variant="outlined"
                  disabled={account.status !== 'active' || isTesting}
                  onClick={() => onTest(account)}
                >
                  {isTesting ? 'Testing…' : 'Test'}
                </Button>
              </span>
            </Tooltip>
            <Tooltip title={syncTooltip}>
              <span>
                <Button
                  size="small"
                  variant="outlined"
                  disabled={syncDisabled || isSyncing}
                  onClick={() => onSyncSites(account)}
                >
                  {isSyncing ? 'Syncing…' : 'Sync Sites'}
                </Button>
              </span>
            </Tooltip>
            <IconButton size="small" onClick={event => openMenu(event, account)} disabled={isArchiving}>
              <MoreVertIcon fontSize="small" />
            </IconButton>
          </>
        )}
      </Box>
    );
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={600}>
            Provider Accounts
          </Typography>
          {canEdit && (
            <Tooltip
              title={
                hasLicensedProviders
                  ? 'Create a new provider account'
                  : 'License a provider type first (panel above) before adding accounts.'
              }
            >
              <span>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={onAddAccount}
                  disabled={!hasLicensedProviders}
                >
                  Add Provider Account
                </Button>
              </span>
            </Tooltip>
          )}
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Each provider account represents one set of stored credentials with one telemetry provider. Credentials are
          write-only — saved values are never displayed back in this UI.
        </Typography>

        {isLoading ? (
          <Skeleton variant="rectangular" height={120} />
        ) : error ? (
          <Alert severity="error">Failed to load provider accounts.</Alert>
        ) : accounts.length === 0 ? (
          <Alert severity="info">
            No provider accounts yet.
            {canEdit && hasLicensedProviders
              ? ' Click Add Provider Account above to create one.'
              : !hasLicensedProviders
                ? ' License a provider type first.'
                : ''}
          </Alert>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Provider</TableCell>
                  <TableCell>Account</TableCell>
                  <TableCell>Lifecycle</TableCell>
                  <TableCell>Credentials</TableCell>
                  <TableCell>Sync</TableCell>
                  <TableCell align="right">External sites</TableCell>
                  <TableCell align="right">Active mappings</TableCell>
                  <TableCell>Last test</TableCell>
                  <TableCell>Last success</TableCell>
                  <TableCell>Last error</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {accounts.map(account => (
                  <TableRow
                    key={account.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => onView(account)}
                  >
                    <TableCell>
                      <Typography variant="body2">{account.display_name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {account.provider_key}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{account.name}</Typography>
                      {account.external_account_label && (
                        <Typography variant="caption" color="text.secondary">
                          {account.external_account_label}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <LifecycleChip value={account.status} />
                    </TableCell>
                    <TableCell>
                      <CredentialChip value={account.credential_status} />
                    </TableCell>
                    <TableCell>
                      <SyncChip value={account.last_sync_status} />
                    </TableCell>
                    <TableCell align="right">{account.external_site_count}</TableCell>
                    <TableCell align="right">{account.active_mapping_count}</TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {formatTimestamp(account.last_error_at ?? account.last_success_at)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{formatTimestamp(account.last_success_at)}</Typography>
                    </TableCell>
                    <TableCell sx={{ maxWidth: 220 }}>
                      {account.last_error_message ? (
                        <Tooltip title={account.last_error_message}>
                          <Typography
                            variant="caption"
                            color="error"
                            sx={{
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden'
                            }}
                          >
                            {account.last_error_message}
                          </Typography>
                        </Tooltip>
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell align="right" onClick={e => e.stopPropagation()}>
                      {renderActions(account)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={closeMenu}>
          <MenuItem
            onClick={() => {
              if (menuAccount) onRotate(menuAccount);
              closeMenu();
            }}
          >
            Rotate Credentials
          </MenuItem>
          <MenuItem
            onClick={() => {
              if (menuAccount) onArchive(menuAccount);
              closeMenu();
            }}
          >
            {menuAccount?.is_archived ? 'Already archived' : 'Archive'}
          </MenuItem>
        </Menu>
      </CardContent>
    </Card>
  );
};
